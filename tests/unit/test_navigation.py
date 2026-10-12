"""Navigation selection, lifetime, streaming and formal console syntax."""
from __future__ import annotations
import asyncio
import grpc
import pytest
from clang_toolkit import AsyncClient, Client, CursorError, MatchValue, MatchValueError
from clang_toolkit._generated.match.v1 import match_service_pb2 as pb
from clang_toolkit._generated.match.v1 import match_stream_pb2 as stream_pb
from clang_toolkit._generated.match.v1 import match_result_pb2 as result_pb
from clang_toolkit._row_store import RowStore
from clang_toolkit._value_lifecycle import CursorOwner
from clang_toolkit.match_values import BindingSelection
from clang_toolkit.cli.runtime import Runtime, EvaluationError
from test_match_stream import Stream, completed, patch_stream, row


@pytest.fixture
def selected_client(monkeypatch):
    client = Client()
    source = BindingSelection("f", CursorOwner(client, "source", 3, lambda _: None), 0)
    requests = []
    count = [1]
    def call(method, *args, **kwargs):
        if method != "_stream_cursor_match":
            return None
        requests.append(args[0])
        store = RowStore()
        for _ in range(count[0]):
            value = result_pb.MatchResult()
            value.bindings["target"].node.compound_stmt.SetInParent()
            store.append(value.SerializeToString(), binding_names=value.bindings)
            if kwargs.get("on_row"):
                asyncio.run(kwargs["on_row"](value))
        done = stream_pb.MatchStreamCompleted(
            session_id=f"result-{len(requests)}", result_revision=1, row_count=count[0])
        done.expires_at.GetCurrentTime()
        return done, store
    monkeypatch.setattr(client, "_cursor_call", call)
    yield client, source, requests, count
    client.close()


def test_peek_and_step_preserve_source_and_return_live_target(selected_client):
    client, source, requests, _ = selected_client
    rows = client.peek(source, query="compoundStmt()")
    body = client.step(source, query="compoundStmt()")
    assert isinstance(rows, MatchValue) and isinstance(body, BindingSelection)
    assert body.name == "target" and body._owner is not source._owner
    assert not source._owner.closed and source._owner.revision == 3
    assert requests[0].navigation_axis == pb.NAVIGATION_AXIS_CHILDREN
    assert requests[0].binding.expected_result_revision == 3
    assert requests[0].binding.HasField("match_index")
    assert requests[0].preserve_source and requests[0].query == "compoundStmt()"
    client.peek(body, axis="parents")
    assert requests[-1].query == ""
    assert requests[-1].navigation_axis == pb.NAVIGATION_AXIS_PARENTS


@pytest.mark.parametrize("count,at,message", [
    (0, None, "no candidates"), (2, None, "ambiguous"),
    (1, 2, "outside"), (1, -1, "zero-based"), (1, True, "zero-based")])
def test_selection_failures_preserve_source_and_close_only_results(
        selected_client, count, at, message):
    client, source, _, emitted = selected_client
    emitted[0] = count
    with pytest.raises(MatchValueError, match=message):
        client.step(source, at=at)
    assert not source._owner.closed and source._owner.revision == 3


def test_indexed_selection_and_binding_ownership_validation(selected_client):
    client, source, requests, count = selected_client
    count[0] = 2
    assert client.step(source, at=1)._index == 1
    with pytest.raises(MatchValueError, match="another client"):
        Client().peek(source)
    for options in [{"axis": "ancestors"}, {"max_nodes": 0}, {"max_nodes": True}]:
        with pytest.raises(ValueError):
            client.peek(source, **options)
    assert len(requests) == 1


def test_console_navigation_assignment_filter_index_and_stream(selected_client, tmp_path, capsys):
    client, source, requests, _ = selected_client
    runtime = Runtime(client, cwd=tmp_path)
    runtime.bindings["node"] = source
    assert runtime.execute("let body = step children compoundStmt() in $node") == ""
    assert runtime.execute("let items = peek children in $node nodes 4") == ""
    assert capsys.readouterr().out == ""
    assert runtime.execute("peek children in $node") == "1 neighbours"
    assert "compound_stmt" in capsys.readouterr().out
    runtime.execute("let up = step parents at 0 in $body")
    assert requests[-1].navigation_axis == pb.NAVIGATION_AXIS_PARENTS
    assert runtime.bindings["node"] is source
    for source_text in ["peek ancestors in $node", "peek children in $node nodes 0",
                        "peek children in $node nodes 2 nodes 3",
                        "step children at 1.5 in $node"]:
        with pytest.raises(EvaluationError):
            runtime.execute(source_text)
    runtime.close()


def test_navigation_rejects_rows_without_a_retained_target(monkeypatch):
    events = Stream([stream_pb.MatchStreamEvent(row=row("wrong")),
                     completed("next", 1)])
    stub = patch_stream(monkeypatch, events)
    stub.StreamNavigate = stub.StreamMatch

    async def run():
        async with AsyncClient() as client:
            owner = CursorOwner(client, "source", 1, lambda _: None)
            source = BindingSelection("f", owner, 0)
            with pytest.raises(CursorError) as error:
                await client.peek(source)
            assert error.value.code == grpc.StatusCode.DATA_LOSS
            assert not owner.closed and client._value_operation_count == 0

    asyncio.run(run())
    assert events.cancelled


def test_async_navigation_uses_stream_rpc_and_waits_for_completion(monkeypatch):
    value = row("target")
    observed = []
    events = Stream([stream_pb.MatchStreamEvent(row=value), completed("next", 1)],
                    before_terminal=lambda: observed.append("completion"))
    stub = patch_stream(monkeypatch, events)
    stub.StreamNavigate = stub.StreamMatch
    async def run():
        async with AsyncClient() as client:
            owner = CursorOwner(client, "source", 1, lambda _: None)
            selected = BindingSelection("f", owner, 0)
            rows = await client.peek(selected, on_row=lambda _: observed.append("row"))
            assert len(rows) == 1
            assert rows[0].binding("target")._owner.session_id == "next"
            assert not owner.closed and stub.request.preserve_source
            assert stub.request.navigation_axis == pb.NAVIGATION_AXIS_CHILDREN
    asyncio.run(run())
    assert observed == ["row", "completion"]
