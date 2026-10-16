"""Call-graph request targets, validation and event-stream contracts."""

from __future__ import annotations

import asyncio

import grpc
import pytest

from clang_toolkit import AsyncClient, Client, InputDescriptor, ParsedTree
from clang_toolkit import client as client_module
from clang_toolkit.analysis_error import AnalysisError
from clang_toolkit._generated.analysis.v1 import call_graph_stream_pb2 as stream_pb
from clang_toolkit._generated.match.v1 import match_result_pb2
from clang_toolkit._value_lifecycle import CursorOwner
from clang_toolkit.match_values import BindingSelection
from clang_toolkit.resources import FileHandle
from test_match_stream import Channel, Stream


def graph_events():
    started = stream_pb.CallGraphStreamEvent()
    started.graph_started.graph.root_node = 0
    started.graph_started.graph.is_complete = False
    node = stream_pb.CallGraphStreamEvent()
    node.node.node.node_index = 0
    node.node.node.function.qualified_name = "pkg::f"
    edge = stream_pb.CallGraphStreamEvent()
    edge.edge.edge.caller_node = 0
    edge.edge.edge.callee_node = 0
    site = stream_pb.CallGraphStreamEvent()
    site.call_site.call_site.caller_node = 0
    done = stream_pb.CallGraphStreamEvent()
    done.completed.graph_count = 1
    done.completed.node_count = 1
    done.completed.edge_count = 1
    done.completed.call_site_count = 1
    done.completed.is_complete = True
    return [started, node, edge, site, done]


def setup_stream(monkeypatch, events, *, status=grpc.StatusCode.OK):
    stream = Stream(events, status=status)

    class Stub:
        def StreamCallGraph(self, request, *, timeout=None):
            self.request = request
            return stream

    stub = Stub()
    monkeypatch.setattr(
        client_module.grpc.aio, "insecure_channel", lambda *a, **k: Channel()
    )
    monkeypatch.setattr(
        client_module.query_pb2_grpc, "QueryServiceStub", lambda c: object()
    )
    monkeypatch.setattr(
        client_module.match_service_pb2_grpc, "MatchServiceStub", lambda c: object()
    )
    monkeypatch.setattr(
        client_module.analysis_service_pb2_grpc, "AnalysisServiceStub", lambda c: stub
    )
    return stream, stub


def test_retained_binding_and_tree_keep_exact_target_and_shallow_defaults():
    client = Client()
    owner = CursorOwner(client, "session-1", 7, lambda _: None)
    selected = BindingSelection("fn", owner, 3)
    request = client_module._call_graph_value_request(client, selected)
    assert request.WhichOneof("target") == "binding"
    assert request.binding.session_id == "session-1"
    assert request.binding.bind == "fn"
    assert request.binding.match_index == 3
    assert request.binding.expected_result_revision == 7
    assert (
        request.direction
        == client_module.call_graph_request_pb2.CALL_GRAPH_DIRECTION_UNSPECIFIED
    )
    assert not request.HasField("max_depth")

    tree = ParsedTree("a.cc", CursorOwner(client, "tree-session", 2, lambda _: None))
    tree_request = client_module._call_graph_value_request(client, tree)
    assert tree_request.WhichOneof("target") == "session"
    assert tree_request.session.session_id == "tree-session"
    with pytest.raises(ValueError, match="omit function"):
        client_module._call_graph_value_request(client, selected, "f")
    client.close()


def test_file_handle_and_descriptor_keep_profile_details():
    client = Client()
    descriptor = InputDescriptor(
        "/src/a.cc",
        profile_id="locked",
        working_directory="/src",
        compile_arguments=("-DVALUE=1",),
        frozen_profile=True,
    )
    handle = FileHandle("lease-1", descriptor, client)
    request = client_module._call_graph_value_request(client, handle)
    assert request.WhichOneof("target") == "file_handle"
    assert request.file_handle.lease_id == "lease-1"

    request = client_module._call_graph_value_request(client, descriptor)
    assert request.WhichOneof("target") == "file"
    assert request.file.expected_profile_id == "locked"
    assert request.file.working_directory == "/src"
    assert list(request.file.compile_arguments) == ["-DVALUE=1"]
    assert request.file.frozen_profile
    client.close()


def test_named_function_uses_exact_function_selector_and_shallow_default():
    client = Client()
    request = client_module._call_graph_value_request(client, "src/a.cc", "pkg::f")
    assert request.WhichOneof("target") == "file"
    assert request.function == "pkg::f"
    assert (
        request.direction
        == client_module.call_graph_request_pb2.CALL_GRAPH_DIRECTION_OUT
    )
    assert request.max_depth == 1
    client.close()


def test_unlimited_depth_is_explicit_and_mutually_exclusive_with_numeric_depth():
    client = Client()
    selected = BindingSelection(
        "fn", CursorOwner(client, "session-all", 4, lambda _: None), 0
    )
    request = client_module._call_graph_value_request(
        client, selected, direction="both", max_depth="all"
    )
    assert request.unlimited_depth
    assert not request.HasField("max_depth")
    assert request.direction == client_module.call_graph_request_pb2.CALL_GRAPH_DIRECTION_BOTH
    numeric = client_module._call_graph_value_request(
        client, selected, direction="in", max_depth=3
    )
    assert numeric.max_depth == 3
    assert not numeric.unlimited_depth
    client.close()


def test_call_expression_binding_is_exact_site_without_neighborhood_defaults():
    client = Client()
    owner = CursorOwner(client, "session", 1, lambda _: None)
    payload = match_result_pb2.MatchBinding(
        call_site={"static_callee_symbol_identity": "usr:f"}
    )
    selected = BindingSelection(
        "site", owner, 0, _binding_data=payload.SerializeToString()
    )

    request = client_module._call_graph_value_request(client, selected)
    assert request.WhichOneof("target") == "binding"
    assert (
        request.direction
        == client_module.call_graph_request_pb2.CALL_GRAPH_DIRECTION_UNSPECIFIED
    )
    assert not request.HasField("max_depth")
    for option in ({"direction": "in"}, {"max_depth": 0}):
        with pytest.raises(ValueError, match="call expressions"):
            client_module._call_graph_value_request(client, selected, **option)
    client.close()


@pytest.mark.parametrize(
    "options",
    [
        {"max_depth": True},
        {"max_depth": 33},
        {"max_call_sites": 0},
        {"direction": "sideways"},
    ],
)
def test_invalid_options_are_rejected_before_rpc(options):
    client = Client()
    called = []
    client._cursor_call = lambda *args, **kwargs: called.append((args, kwargs))
    with pytest.raises(ValueError):
        client.callgraph("a.cc", **options)
    assert not called
    client.close()


def test_async_iterator_and_collector_verify_counts_and_preserve_request(monkeypatch):
    stream, stub = setup_stream(monkeypatch, graph_events())

    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            events = [
                event
                async for event in client.callgraph_stream(
                    "fixture.cc", direction="both", max_depth=2
                )
            ]
            assert [event.WhichOneof("event") for event in events] == [
                "graph_started",
                "node",
                "edge",
                "call_site",
                "completed",
            ]
            assert (
                stub.request.direction
                == client_module.call_graph_request_pb2.CALL_GRAPH_DIRECTION_BOTH
            )
            assert stub.request.max_depth == 2
            assert client._value_operation_count == 0

        stream2, _ = setup_stream(monkeypatch, graph_events())
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            response = await client.callgraph("fixture.cc")
            assert (
                len(response.nodes)
                == len(response.edges)
                == len(response.call_sites)
                == 1
            )
            assert response.is_complete
            assert client._value_operation_count == 0
        assert not stream2.cancelled

    asyncio.run(run())
    assert not stream.cancelled


def test_unlimited_depth_stream_requires_server_confirmation(monkeypatch):
    events = graph_events()
    events[0].graph_started.graph.selection_unlimited_depth = True
    stream, stub = setup_stream(monkeypatch, events)

    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            events_seen = [
                event
                async for event in client.callgraph_stream(
                    "fixture.cc", "pkg::f", max_depth="all"
                )
            ]
            assert events_seen[-1].HasField("completed")
            assert stub.request.unlimited_depth
            assert not stub.request.HasField("max_depth")

        missing, _ = setup_stream(monkeypatch, graph_events())
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            with pytest.raises(AnalysisError) as error:
                async for _ in client.callgraph_stream(
                    "fixture.cc", "pkg::f", max_depth="all"
                ):
                    pass
            assert error.value.code == grpc.StatusCode.FAILED_PRECONDITION
        assert missing.cancelled

    asyncio.run(run())
    assert not stream.cancelled


def test_stream_collector_aggregates_per_record_availability_in_event_order(
    monkeypatch,
):
    events = graph_events()
    events[0].graph_started.graph.availability.add(field_path="header-only")
    events[1].node.node.availability.add(field_path="node.fact")
    events[2].edge.edge.availability.add(field_path="edge.fact")
    events[3].call_site.call_site.availability.add(field_path="site.fact")
    stream, _ = setup_stream(monkeypatch, events)

    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            response = await client.callgraph("fixture.cc")
            assert [entry.field_path for entry in response.availability] == [
                "node.fact",
                "edge.fact",
                "site.fact",
            ]

    asyncio.run(run())
    assert not stream.cancelled


def test_sync_callback_consumes_stream_and_returns_terminal_counts(monkeypatch):
    stream, _ = setup_stream(monkeypatch, graph_events())
    seen = []
    with Client(address="unix:///tmp/test.sock") as client:
        completed = client.stream_callgraph("fixture.cc", on_event=seen.append)
    assert completed.node_count == 1 and completed.call_site_count == 1
    assert [event.WhichOneof("event") for event in seen][-1] == "completed"
    assert not stream.cancelled


def test_legacy_unary_fallback_only_for_file_target_before_stream_events(monkeypatch):
    stream, stub = setup_stream(monkeypatch, [], status=grpc.StatusCode.UNIMPLEMENTED)
    from clang_toolkit._generated.analysis.v1 import call_graph_response_pb2

    response = call_graph_response_pb2.CallGraphResponse(is_complete=True)
    response.nodes.add(node_index=0, is_virtual_root=True)

    async def unary(request, *, timeout=None):
        return response

    stub.CallGraph = unary

    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            collected = await client.callgraph("fixture.cc")
            assert collected == response
            selected = BindingSelection(
                "fn", CursorOwner(client, "retained", 1, lambda _: None), 0
            )
            with pytest.raises(client_module.AnalysisError) as error:
                await client.callgraph(selected)
            assert error.value.code == grpc.StatusCode.UNIMPLEMENTED

    asyncio.run(run())
    assert not stream.cancelled


def test_stream_callback_runs_before_completion_and_early_close_cancels(monkeypatch):
    stream, _ = setup_stream(monkeypatch, graph_events())

    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            seen = []
            complete = await client.stream_callgraph(
                "fixture.cc",
                on_event=lambda event: seen.append(event.WhichOneof("event")),
            )
            assert seen[-1] == "completed"
            assert complete.node_count == 1 and complete.call_site_count == 1

        early, _ = setup_stream(monkeypatch, graph_events())
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            iterator = client.callgraph_stream("fixture.cc")
            await iterator.__anext__()
            await iterator.aclose()
            assert client._value_operation_count == 0
        assert early.cancelled

    asyncio.run(run())
    assert not stream.cancelled


@pytest.mark.parametrize(
    "mutate",
    [
        lambda events: events[:1] + [events[2], *events[3:]],
        lambda events: events[:2] + [events[1], *events[2:]],
        lambda events: [
            events[0],
            stream_pb.CallGraphStreamEvent(
                node=stream_pb.CallGraphNodeEvent(graph_index=0, node={"node_index": 1})
            ),
            *events[2:],
        ],
        lambda events: [
            events[0],
            events[1],
            stream_pb.CallGraphStreamEvent(
                edge=stream_pb.CallGraphEdgeEvent(
                    graph_index=0, edge={"caller_node": 0, "callee_node": 99}
                )
            ),
            *events[3:],
        ],
        lambda events: [
            events[0],
            stream_pb.CallGraphStreamEvent(
                graph_started=stream_pb.CallGraphStarted(
                    graph_index=1, graph=events[0].graph_started.graph
                )
            ),
            *events[1:],
        ],
        lambda events: [
            stream_pb.CallGraphStreamEvent(
                graph_started=stream_pb.CallGraphStarted(
                    graph_index=0, graph={"root_node": 0, "focus_node": 99}
                )
            ),
            *events[1:],
        ],
        lambda events: [
            *events[:-1],
            stream_pb.CallGraphStreamEvent(
                completed=stream_pb.CallGraphCompleted(
                    graph_count=1,
                    node_count=2,
                    edge_count=1,
                    call_site_count=1,
                    is_complete=True,
                )
            ),
        ],
        lambda events: [
            *events[:-1],
            stream_pb.CallGraphStreamEvent(
                completed=stream_pb.CallGraphCompleted(
                    graph_count=1,
                    node_count=1,
                    edge_count=2,
                    call_site_count=1,
                    is_complete=True,
                )
            ),
        ],
    ],
)
def test_invalid_stream_references_duplicates_and_counts_fail_closed(
    monkeypatch, mutate
):
    events = mutate(graph_events())
    stream, _ = setup_stream(monkeypatch, events)

    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            with pytest.raises(client_module.AnalysisError) as error:
                await client.callgraph("fixture.cc")
            assert error.value.code == grpc.StatusCode.DATA_LOSS
            assert client._value_operation_count == 0

    asyncio.run(run())
    assert stream.cancelled


def test_non_ok_stream_status_is_preserved(monkeypatch):
    setup_stream(monkeypatch, graph_events(), status=grpc.StatusCode.CANCELLED)

    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            with pytest.raises(client_module.AnalysisError) as error:
                await client.callgraph("fixture.cc")
            assert error.value.code == grpc.StatusCode.CANCELLED

    asyncio.run(run())
