"""Callable boundary options preserve exact inputs and fail closed on old servers."""

from __future__ import annotations

import asyncio
from unittest.mock import Mock

import grpc
import pytest

from clang_toolkit import AsyncClient, CallGraph, Client, ParsedTree
from clang_toolkit.analysis_error import AnalysisError
from clang_toolkit._value_lifecycle import CursorOwner
from clang_toolkit.call_graph import call_graph_request
from clang_toolkit.cli.runtime import EvaluationError
from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
from clang_toolkit.client import _call_graph_value_request
from clang_toolkit.match_values import BindingSelection
from clang_toolkit._generated.analysis.v1.call_graph_response_pb2 import CallGraphResponse


FILTER = 'functionDecl(unless(matchesName("(^|::)vendor::")))'


@pytest.mark.parametrize("strict", [False, True])
@pytest.mark.parametrize("kind", ["filename", "tree", "binding"])
def test_boundaries_preserve_retained_identity_and_shallow_defaults(kind, strict):
    client = Client()
    owner = CursorOwner(client, "pinned", 7, lambda _: None)
    target = {
        "filename": "source.cc",
        "tree": ParsedTree("source.cc", owner),
        "binding": BindingSelection("fn", owner, 0),
    }[kind]
    request = _call_graph_value_request(
        client, target, exclude_system_headers=True, node_filter=FILTER,
        strict_node_filter=strict
    )
    assert request.exclude_system_headers
    assert request.node_filter == FILTER
    assert request.strict_node_filter is strict
    assert request.WhichOneof("target") == {
        "filename": "file", "tree": "session", "binding": "binding"
    }[kind]
    assert not request.main_file_only
    assert not request.HasField("max_depth")
    if kind == "binding":
        assert request.binding.session_id == "pinned"
        assert request.binding.expected_result_revision == 7
    client.close()


@pytest.mark.parametrize("value", [1, "true", None])
def test_system_header_exclusion_requires_boolean(value):
    with pytest.raises(ValueError, match="exclude_system_headers"):
        call_graph_request("source.cc", exclude_system_headers=value)


@pytest.mark.parametrize("value", [1, True, [], "", "  "])
def test_custom_filter_requires_nonempty_matcher_text(value):
    with pytest.raises(ValueError, match="node_filter"):
        call_graph_request("source.cc", node_filter=value)


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_console_boundary_options_compose_and_reject_duplicates(tmp_path, engine):
    client = Mock(spec=Client)
    client.callgraph.return_value = CallGraphResponse(is_complete=True)
    runtime = PrototypeRuntime(client, cwd=tmp_path, script_engine=engine)
    runtime.execute(
        'let g = callgraph "source.cc" exclude-system true '
        "node-filter 'functionDecl(unless(matchesName(\"(^|::)vendor::\")))' strict-node-filter true nodes all"
    )
    assert client.callgraph.call_args.kwargs["exclude_system_headers"] is True
    assert client.callgraph.call_args.kwargs["node_filter"] == FILTER
    assert client.callgraph.call_args.kwargs["max_nodes"] == "all"
    assert client.callgraph.call_args.kwargs["strict_node_filter"] is True
    for repeated in (
        "exclude-system true exclude-system false",
        "strict-node-filter true strict-node-filter false",
        "node-filter 'decl()' node-filter 'functionDecl()'",
    ):
        with pytest.raises(EvaluationError, match="duplicate"):
            runtime.execute(f'let g = callgraph "source.cc" {repeated}')
    runtime.close()


@pytest.mark.parametrize("confirmed", [True, False])
def test_streams_require_server_confirmation_of_boundaries(monkeypatch, confirmed):
    from test_call_graph_client import graph_events, setup_stream

    events = graph_events()
    if confirmed:
        events[0].graph_started.graph.exclude_system_headers = True
        events[0].graph_started.graph.node_filter = FILTER
    stream, stub = setup_stream(monkeypatch, events)

    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            if confirmed:
                response = await client.callgraph(
                    "source.cc", exclude_system_headers=True, node_filter=FILTER
                )
                assert response.exclude_system_headers
                assert response.node_filter == FILTER
                assert stub.request.node_filter == FILTER
            else:
                with pytest.raises(AnalysisError) as error:
                    await client.callgraph(
                        "source.cc", exclude_system_headers=True, node_filter=FILTER
                    )
                assert error.value.code == grpc.StatusCode.FAILED_PRECONDITION
                assert stream.cancelled

    asyncio.run(run())


def test_unary_fallback_requires_server_confirmation(monkeypatch):
    from test_call_graph_client import setup_stream

    _, stub = setup_stream(monkeypatch, [], status=grpc.StatusCode.UNIMPLEMENTED)

    async def unary(request, *, timeout=None):
        return CallGraphResponse(is_complete=True)

    stub.CallGraph = unary

    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            with pytest.raises(AnalysisError) as error:
                await client.callgraph("source.cc", exclude_system_headers=True)
            assert error.value.code == grpc.StatusCode.FAILED_PRECONDITION

    asyncio.run(run())


def test_live_neighborhood_queries_keep_the_graph_boundary():
    client = Client()
    target = BindingSelection("fn", CursorOwner(client, "pinned", 7, lambda _: None), 0)
    response = CallGraphResponse(
        is_complete=True, exclude_system_headers=True, node_filter=FILTER,
        strict_node_filter=True
    )
    selector = Mock(return_value=response)
    graph = CallGraph(response, selector=selector)
    graph.callees(target, depth="all")
    selector.assert_called_once_with(
        target, direction="out", max_depth="all",
        exclude_system_headers=True, node_filter=FILTER, strict_node_filter=True,
    )
    client.close()


def test_sync_callback_preserves_boundary_request(monkeypatch):
    from test_call_graph_client import graph_events, setup_stream

    events = graph_events()
    events[0].graph_started.graph.exclude_system_headers = True
    events[0].graph_started.graph.node_filter = FILTER
    _, stub = setup_stream(monkeypatch, events)
    seen = []
    with Client(address="unix:///tmp/test.sock") as client:
        completed = client.stream_callgraph(
            "source.cc", on_event=seen.append,
            exclude_system_headers=True, node_filter=FILTER,
        )
    assert completed.is_complete and seen[-1].HasField("completed")
    assert stub.request.exclude_system_headers and stub.request.node_filter == FILTER


def test_async_iterator_preserves_boundary_request(monkeypatch):
    from test_call_graph_client import graph_events, setup_stream

    events = graph_events()
    events[0].graph_started.graph.exclude_system_headers = True
    events[0].graph_started.graph.node_filter = FILTER
    _, stub = setup_stream(monkeypatch, events)

    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            seen = [event async for event in client.callgraph_stream(
                "source.cc", exclude_system_headers=True, node_filter=FILTER
            )]
            assert seen[-1].completed.is_complete
            assert stub.request.exclude_system_headers and stub.request.node_filter == FILTER

    asyncio.run(run())


@pytest.mark.parametrize("value", [1, "true", None])
def test_strict_filter_requires_boolean(value):
    with pytest.raises(ValueError, match="strict_node_filter"):
        call_graph_request("source.cc", node_filter=FILTER, strict_node_filter=value)


def test_strict_filter_is_optional_and_requires_a_matcher():
    assert not call_graph_request("source.cc", node_filter=FILTER).strict_node_filter
    with pytest.raises(ValueError, match="requires node_filter"):
        call_graph_request("source.cc", strict_node_filter=True)


@pytest.mark.parametrize("fallback", [False, True])
@pytest.mark.parametrize("confirmed", [False, True])
def test_strict_filter_requires_server_confirmation(monkeypatch, fallback, confirmed):
    from test_call_graph_client import graph_events, setup_stream

    events = graph_events()
    events[0].graph_started.graph.node_filter = FILTER
    events[0].graph_started.graph.strict_node_filter = confirmed
    stream, stub = setup_stream(
        monkeypatch, [] if fallback else events,
        status=grpc.StatusCode.UNIMPLEMENTED if fallback else grpc.StatusCode.OK,
    )

    async def unary(request, *, timeout=None):
        return CallGraphResponse(
            is_complete=True, node_filter=FILTER, strict_node_filter=confirmed
        )

    stub.CallGraph = unary

    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            if confirmed:
                graph = await client.callgraph(
                    "source.cc", node_filter=FILTER, strict_node_filter=True
                )
                assert graph.strict_node_filter and stub.request.strict_node_filter
            else:
                with pytest.raises(AnalysisError) as error:
                    await client.callgraph(
                        "source.cc", node_filter=FILTER, strict_node_filter=True
                    )
                assert error.value.code == grpc.StatusCode.FAILED_PRECONDITION
                if not fallback:
                    assert stream.cancelled

    asyncio.run(run())
