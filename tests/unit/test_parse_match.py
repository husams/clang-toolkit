"""Immutable match ownership, Lark scoping and semantic snapshot regressions."""

from __future__ import annotations

import asyncio
import gc
import inspect
from threading import Thread
from dataclasses import FrozenInstanceError

import pytest
import grpc
from lark.exceptions import UnexpectedInput

from clang_toolkit import AsyncClient, Client, MatchValue, MatchValueError, ParsedTree
from clang_toolkit import client as client_module
from clang_toolkit.cursors import CursorError
from clang_toolkit._generated.match.v1 import match_result_pb2 as results
from clang_toolkit._generated.match.v1 import match_service_pb2 as pb
from clang_toolkit._generated.match.v1 import parse_response_pb2
from clang_toolkit._generated.match.v1 import match_stream_pb2
from clang_toolkit._row_store import RowStore
from clang_toolkit._generated.match.v1 import match_stream_pb2
from clang_toolkit._row_store import RowStore
from clang_toolkit.cli.app import dispatch
from clang_toolkit.cli.input_state import input_state
from clang_toolkit.cli.runtime import EvaluationError, Runtime
from clang_toolkit.cli.runtime.persistence import PersistenceError, load, save


def response(identifier: str, query: str = "functionDecl()") -> pb.MatchResponse:
    value = pb.MatchResponse(session_id=identifier, result_revision=1)
    if query == "none()":
        return value
    names = {"f": "FunctionDecl", "call": "CallExpr", "n": "IntegerLiteral"}
    for _ in range(2 if query.startswith("functionDecl") else 1):
        row = value.results.add()
        for name, kind in names.items():
            binding = row.bindings[name]
            binding.unsupported.clang_kind = kind
            binding.unsupported.detail = "test payload"
            binding.is_complete = False
            binding.supported_scopes.append(results.BINDING_MATCH_SCOPE_SUBTREE)
    return value


async def streamed_response(value, on_row=None):
    store = RowStore()
    for row in value.results:
        encoded = row.SerializeToString()
        store.append(encoded)
        if on_row is not None:
            on_row(row)
    completion = match_stream_pb2.MatchStreamCompleted(
        session_id=value.session_id, result_revision=value.result_revision,
        row_count=len(value.results),
    )
    completion.expires_at.GetCurrentTime()
    return completion, store


@pytest.fixture
def owned_client(monkeypatch):
    client = Client()
    requests = []
    closed = []
    counter = 0

    def call(method, *args, **kwargs):
        nonlocal counter
        if method == "close_match":
            closed.append(args[0])
            return None
        if method == "_stream_cursor_match":
            request = args[0]
            counter += 1
            identifier = f"cursor-{counter}"
            requests.append(("_stream_cursor_match", (request,), kwargs))
            result = response(identifier, request.query)
            store = RowStore()
            callback = kwargs.get("on_row")
            for row in result.results:
                encoded = row.SerializeToString()
                store.append(encoded)
                if callback is not None:
                    detached = results.MatchResult.FromString(encoded)
                    outcome = callback(detached)
                    if inspect.isawaitable(outcome):
                        asyncio.run(outcome)
            completion = match_stream_pb2.MatchStreamCompleted(
                session_id=identifier, result_revision=1, row_count=len(result.results)
            )
            completion.expires_at.GetCurrentTime()
            return completion, store
        counter += 1
        identifier = f"cursor-{counter}"
        requests.append((method, args, kwargs))
        if method == "_parse_response":
            return parse_response_pb2.ParseResponse(session_id=identifier, result_revision=1)
        return response(identifier, args[0].query)

    monkeypatch.setattr(client, "_cursor_call", call)
    yield client, requests, closed
    client.close()


def test_parse_and_independent_matches_preserve_tree_and_compilation_context(owned_client, tmp_path):
    client, requests, closed = owned_client
    tree = client.parse("example.cc", working_directory=tmp_path,
                        compile_arguments=["-std=c++23"])
    assert isinstance(tree, ParsedTree)
    method, args, options = requests[0]
    assert method == "_parse_response" and args == ("example.cc",)
    assert options["compile_arguments"] == ["-std=c++23"]
    functions = client.match_in('functionDecl().bind("f")', tree)
    functions2 = client.match_in('functionDecl().bind("f")', tree)
    assert len(functions) == len(functions2) == 2
    assert functions._owner is not functions2._owner
    for _, args, _ in requests[1:]:
        request = args[0]
        assert request.preserve_source
        assert request.session.session_id == "cursor-1"
        assert request.session.expected_result_revision == 1
    assert not closed
    with pytest.raises(FrozenInstanceError):
        tree.path = "other.cc"


def test_all_rows_and_explicit_zero_use_original_result_revision(owned_client):
    client, requests, _ = owned_client
    functions = client.match_in('functionDecl().bind("f")', "example.cc")
    original = tuple(row.to_dict() for row in functions.rows)
    client.match_in('callExpr().bind("call")', functions.binding("f"))
    client.match_in('callExpr().bind("call")', functions[0].binding("f"))
    all_rows, one_row = requests[1][1][0], requests[2][1][0]
    assert not all_rows.binding.HasField("match_index")
    assert one_row.binding.HasField("match_index") and one_row.binding.match_index == 0
    assert all_rows.binding.expected_result_revision == one_row.binding.expected_result_revision == 1
    assert all_rows.preserve_source and one_row.preserve_source
    assert tuple(row.to_dict() for row in functions.rows) == original
    copied = functions[0].bindings["f"]
    copied.unsupported.clang_kind = "changed"
    assert functions[0].bindings["f"].unsupported.clang_kind == "FunctionDecl"


def test_sync_on_row_callback_is_incremental_and_cannot_mutate_stored_rows(owned_client):
    client, _, _ = owned_client
    seen = []

    def on_row(value):
        seen.append(value.bindings["f"].unsupported.clang_kind)
        value.bindings["f"].unsupported.clang_kind = "mutated"

    functions = client.match_in('functionDecl().bind("f")', "example.cc", on_row=on_row)
    assert seen == ["FunctionDecl", "FunctionDecl"]
    assert functions[0].bindings["f"].unsupported.clang_kind == "FunctionDecl"


def test_match_value_equality_and_hash_use_serialized_rows(owned_client):
    client, _, _ = owned_client
    empty = client.match_in("none()", "example.cc")
    populated = client.match_in("functionDecl()", "example.cc")
    same_rows = client.match_in("functionDecl()", "example.cc")

    assert empty != populated
    assert populated == same_rows
    assert hash(populated) == hash(same_rows)


def test_cli_completion_uses_binding_names_without_eager_rows(owned_client, tmp_path, monkeypatch):
    client, _, _ = owned_client
    functions = client.match_in("functionDecl()", "example.cc")
    monkeypatch.setattr(MatchValue, "rows", property(lambda _self: (_ for _ in ()).throw(
        AssertionError("eager row snapshot requested"))))
    runtime = Runtime(client, cwd=tmp_path)
    runtime.bindings["functions"] = functions
    assert runtime.completion_references()["functions"] == (
        "call", "f", "isEmpty", "length", "n"
    )


@pytest.mark.parametrize("index", [-1, 2, 1.5, True])
def test_indices_do_not_silently_select_other_rows(owned_client, index):
    client, _, _ = owned_client
    functions = client.match_in("functionDecl()", "example.cc")
    with pytest.raises(MatchValueError, match="zero-based"):
        functions[index]


def test_empty_collection_can_be_used_without_implicit_root(owned_client):
    client, requests, _ = owned_client
    empty = client.match_in("none()", "example.cc")
    assert len(empty) == 0
    client.match_in("callExpr()", empty.binding("f"))
    request = requests[-1][1][0]
    assert request.binding.bind == "f" and request.preserve_source
    assert not request.binding.HasField("match_index")
    with pytest.raises(MatchValueError):
        empty[0]


def test_aliases_and_retained_selections_delay_native_close(owned_client):
    client, _, closed = owned_client
    functions = client.match_in("functionDecl()", "example.cc")
    alias = functions
    selection = functions[0].binding("f")
    del functions
    gc.collect()
    assert not closed
    del alias
    gc.collect()
    assert not closed
    del selection
    gc.collect()
    assert closed == ["cursor-1"]


def test_close_invalidates_retained_values_and_rejects_cross_client_use(owned_client):
    client, _, closed = owned_client
    tree = client.parse("example.cc")
    with pytest.raises(MatchValueError, match="another client"):
        Client().match_in("decl()", tree)
    client.close()
    assert closed == ["cursor-1"]
    with pytest.raises(MatchValueError, match="closed"):
        client.match_in("decl()", tree)
    client.close()
    assert closed == ["cursor-1"]


def test_console_path_tree_all_and_indexed_targets(owned_client, tmp_path):
    client, requests, _ = owned_client
    runtime = Runtime(client, cwd=tmp_path)
    assert runtime.execute('let tree = parse "example.cc";') == ""
    runtime.execute('let functions = match functionDecl().bind("f") in $tree;')
    runtime.execute('let calls = match callExpr().bind("call") in $functions.f;')
    runtime.execute('let first = match callExpr() in $functions[0].f;')
    runtime.execute('let n = match integerLiteral().bind("n") in "example.cc";')
    assert isinstance(runtime.bindings["n"], MatchValue)
    assert requests[2][1][0].binding.bind == "f"
    assert requests[3][1][0].binding.match_index == 0
    assert requests[4][1][0].WhichOneof("target") == "file"
    assert "FunctionDecl" in runtime.execute("$functions")
    assert runtime.completion_references()["functions"] == ("call", "f", "isEmpty", "length", "n")
    assert dispatch(client, "match decl() in $functions[2].f", runtime).startswith("error:")
    runtime.close()


def test_block_shadowing_cleanup_and_reusable_yield(owned_client, tmp_path):
    client, requests, closed = owned_client
    runtime = Runtime(client, cwd=tmp_path)
    runtime.execute('let functions = "outer"')
    source = '''let analysis = in parse "example.cc" {
        let functions = match functionDecl(isDefinition()).bind("f");
        let calls = match callExpr().bind("call") in $functions.f;
        yield calls;
    };'''
    assert runtime.execute(source) == ""
    assert set(runtime.bindings) == {"functions", "analysis"}
    assert runtime.bindings["functions"] == "outer"
    assert set(closed) == {"cursor-1", "cursor-2"}
    assert requests[1][1][0].session.session_id == "cursor-1"
    runtime.execute('let again = match integerLiteral().bind("n") in $analysis.call')
    assert requests[-1][1][0].binding.session_id == "cursor-3"
    runtime.close()
    assert set(closed) == {"cursor-1", "cursor-2", "cursor-3", "cursor-4"}


def test_block_exception_releases_values_and_preserves_assignment(owned_client, tmp_path):
    client, _, closed = owned_client
    runtime = Runtime(client, cwd=tmp_path)
    runtime.execute('let analysis = "old"')
    with pytest.raises(EvaluationError, match="unknown variable") as failure:
        runtime.execute('''let analysis = in parse "example.cc" {
            let functions = match functionDecl().bind("f");
            let calls = match callExpr() in $missing;
            yield functions;
        };''')
    assert runtime.bindings == {"analysis": "old"}
    assert not runtime._scopes and not runtime._default_targets
    assert failure.value.__traceback__ is not None
    assert set(closed) == {"cursor-1", "cursor-2"}


def test_nested_block_yielded_selection_keeps_only_selected_owner(owned_client, tmp_path):
    client, requests, closed = owned_client
    selected = client.execute('''in parse "example.cc" {
        let nested = in parse "other.cc" {
            let functions = match functionDecl().bind("f");
            yield $functions[0].f;
        };
        yield nested;
    }''', working_directory=tmp_path)
    assert set(closed) == {"cursor-1", "cursor-2"}
    client.match_in("callExpr()", selected)
    assert requests[-1][1][0].binding.session_id == "cursor-3"
    assert requests[-1][1][0].binding.match_index == 0


def test_stale_native_revision_is_reported_without_mutating_value(owned_client, monkeypatch):
    client, _, _ = owned_client
    tree = client.parse("example.cc")
    original = client._cursor_call

    def call(method, *args, **kwargs):
        if method == "_stream_cursor_match":
            assert args[0].session.session_id == tree._owner.session_id
            raise CursorError(grpc.StatusCode.ABORTED, "stale result revision")
        return original(method, *args, **kwargs)

    monkeypatch.setattr(client, "_cursor_call", call)
    with pytest.raises(CursorError, match="stale") as failure:
        client.match_in("decl()", tree)
    assert failure.value.code == grpc.StatusCode.ABORTED
    assert not tree._owner.closed and tree._owner.revision == 1


@pytest.mark.parametrize("body", [
    'let x = 1;', 'yield 1; yield 2;', 'yield 1; let x = 2;',
])
def test_yield_is_exactly_one_terminal_statement(owned_client, tmp_path, body):
    client, requests, _ = owned_client
    with pytest.raises(UnexpectedInput):
        Runtime(client, cwd=tmp_path).execute('in parse "example.cc" { ' + body + ' }')
    assert not requests


def test_multiline_block_completion_and_detached_export(owned_client, tmp_path):
    client, _, _ = owned_client
    assert input_state('let x = in parse "example.cc" {').needs_more
    assert not input_state('let x = in parse "example.cc" { yield 1; };').needs_more
    functions = client.match_in("functionDecl()", "example.cc")
    saved = save(functions, tmp_path / "functions.json")
    snapshot = load(saved)
    assert isinstance(snapshot, list)
    text = saved.read_text()
    assert "cursor-" not in text and "session_id" not in text and "revision" not in text
    assert snapshot[0]["bindings"]["f"]["clang_kind"] == "FunctionDecl"
    selection = functions[0].binding("f")
    binding_path = save(selection, tmp_path / "binding.json")
    binding_snapshot = load(binding_path)
    assert binding_snapshot["clang_kind"] == "FunctionDecl"
    assert not {"is_complete", "availability", "supported_scopes", "node"} & binding_snapshot.keys()
    assert "name" not in binding_snapshot and "value" not in binding_snapshot
    binding_text = binding_path.read_text()
    assert "cursor-" not in binding_text and "session_id" not in binding_text
    with pytest.raises(PersistenceError, match="explicit row index"):
        save(functions.binding("f"), tmp_path / "unindexed-binding.json")


def test_python_execute_returns_live_typed_values(owned_client, tmp_path):
    client, requests, closed = owned_client
    value = client.execute('''let analysis = in parse "example.cc" {
        let functions = match functionDecl().bind("f");
        yield functions;
    };''', working_directory=tmp_path, compile_arguments=["-std=c++23"])
    assert isinstance(value, MatchValue) and len(value) == 2
    again = client.execute('match callExpr().bind("call") in $analysis[0].f')
    assert isinstance(again, MatchValue)
    assert requests[0][2]["compile_arguments"] == ["-std=c++23"]
    with pytest.raises(EvaluationError, match="expression or assignment"):
        client.execute("quit")
    client.close()
    assert set(closed) == {"cursor-1", "cursor-2", "cursor-3"}


def test_async_values_cleanup_revision_guard_and_execute(monkeypatch, tmp_path):
    async def run():
        client = AsyncClient()
        client._loop = asyncio.get_running_loop()
        requests, closed = [], []
        count = 0

        def ensure():
            return None

        async def parse(path, **kwargs):
            nonlocal count
            count += 1
            return parse_response_pb2.ParseResponse(session_id=f"async-{count}", result_revision=1)

        async def match(request, *, on_row=None, source_session_id=None):
            nonlocal count
            requests.append(request)
            count += 1
            return await streamed_response(response(f"async-{count}", request.query), on_row)

        async def close(identifier):
            closed.append(identifier)

        monkeypatch.setattr(client, "_ensure_stub", ensure)
        monkeypatch.setattr(client, "_parse_response", parse)
        monkeypatch.setattr(client, "_stream_cursor_match", match)
        monkeypatch.setattr(client, "close_match", close)
        tree = await client.parse("example.cc")
        functions = await client.match_in("functionDecl()", tree)
        await client.match_in("callExpr()", functions[0].binding("f"))
        assert requests[0].session.expected_result_revision == 1
        assert requests[1].binding.match_index == 0 and requests[1].preserve_source
        value = await client.execute('in parse "example.cc" { let f = match functionDecl(); yield f; }', working_directory=tmp_path)
        assert isinstance(value, MatchValue)
        await client.aclose()
        assert set(closed) == {f"async-{index}" for index in range(1, 6)}
        assert not client._values and not client._value_cleanup
        with pytest.raises(MatchValueError, match="closed"):
            await client.match_in("decl()", tree)

    asyncio.run(run())


def test_async_cancelled_block_unwinds_before_execution_returns(monkeypatch, tmp_path):
    async def run():
        client = AsyncClient()
        client._loop = asyncio.get_running_loop()
        entered = asyncio.Event()
        cancelled = asyncio.Event()
        closed = []

        async def parse(*args, **kwargs):
            return parse_response_pb2.ParseResponse(session_id="cancel-tree", result_revision=1)

        async def match(request, *, on_row=None, source_session_id=None):
            entered.set()
            try:
                await asyncio.Future()
            finally:
                cancelled.set()

        async def close(identifier):
            closed.append(identifier)

        monkeypatch.setattr(client, "_ensure_stub", lambda: None)
        monkeypatch.setattr(client, "_parse_response", parse)
        monkeypatch.setattr(client, "_stream_cursor_match", match)
        monkeypatch.setattr(client, "close_match", close)
        operation = asyncio.create_task(client.execute('''let value = in parse "example.cc" {
            let functions = match functionDecl(); yield functions;
        }''', working_directory=tmp_path))
        await asyncio.wait_for(entered.wait(), timeout=2)
        operation.cancel()
        with pytest.raises(asyncio.CancelledError):
            await operation
        assert cancelled.is_set()
        assert closed == ["cancel-tree"]
        assert not client._expression_runtime._scopes
        assert "value" not in client._expression_runtime.bindings
        await client.aclose()

    asyncio.run(run())


@pytest.mark.parametrize("operation", ["parse", "match", "execute"])
def test_async_shutdown_drains_accepted_requests_and_rejects_new_ones(monkeypatch, tmp_path, operation):
    async def run():
        client = AsyncClient()
        client._loop = asyncio.get_running_loop()
        started, release = asyncio.Event(), asyncio.Event()
        closed = []

        async def parse(path, **kwargs):
            if operation == "parse":
                started.set()
                await release.wait()
            return parse_response_pb2.ParseResponse(session_id="shutdown-tree", result_revision=1)

        async def match(request, *, on_row=None, source_session_id=None):
            started.set()
            await release.wait()
            return await streamed_response(response("shutdown-results", request.query), on_row)

        async def close(identifier):
            closed.append(identifier)

        monkeypatch.setattr(client, "_ensure_stub", lambda: None)
        monkeypatch.setattr(client, "_parse_response", parse)
        monkeypatch.setattr(client, "_stream_cursor_match", match)
        monkeypatch.setattr(client, "close_match", close)
        if operation == "parse":
            accepted = asyncio.create_task(client.parse("example.cc"))
        elif operation == "match":
            tree = await client.parse("example.cc")
            accepted = asyncio.create_task(client.match_in("functionDecl()", tree))
        else:
            accepted = asyncio.create_task(client.execute('''in parse "example.cc" {
                let functions = match functionDecl(); yield functions;
            }''', working_directory=tmp_path))
        await asyncio.wait_for(started.wait(), timeout=2)
        closing = asyncio.create_task(client.aclose())
        await asyncio.sleep(0)
        assert client._value_closing and not closing.done() and not closed
        with pytest.raises(MatchValueError, match="closing or closed"):
            await client.parse("late.cc")
        with pytest.raises(MatchValueError, match="closing or closed"):
            await client.match_in("decl()", "late.cc")
        with pytest.raises(MatchValueError, match="closing or closed"):
            await client.execute('parse "late.cc"')
        release.set()
        value = await asyncio.wait_for(accepted, timeout=2)
        await asyncio.wait_for(closing, timeout=2)
        expected = {"shutdown-tree"} if operation == "parse" else {"shutdown-tree", "shutdown-results"}
        assert set(closed) == expected and len(closed) == len(expected)
        assert value._owner.closed and not client._values
        assert client._value_operation_count == 0
        with pytest.raises(MatchValueError, match="closing or closed"):
            await client.parse("after-close.cc")

    asyncio.run(run())


def test_async_requests_are_rejected_during_paused_close_rpc(monkeypatch):
    async def run():
        client = AsyncClient()
        client._loop = asyncio.get_running_loop()
        started, release = asyncio.Event(), asyncio.Event()
        closed = []

        async def parse(path, **kwargs):
            return parse_response_pb2.ParseResponse(session_id=path, result_revision=1)

        async def close(identifier):
            started.set()
            await release.wait()
            closed.append(identifier)

        monkeypatch.setattr(client, "_ensure_stub", lambda: None)
        monkeypatch.setattr(client, "_parse_response", parse)
        monkeypatch.setattr(client, "close_match", close)
        tree = await client.parse("one.cc")
        closing = asyncio.create_task(client.aclose())
        await started.wait()
        assert tree._owner.closed
        with pytest.raises(MatchValueError, match="closing or closed"):
            await client.parse("two.cc")
        repeated_close = asyncio.create_task(client.aclose())
        release.set()
        await asyncio.gather(closing, repeated_close)
        assert closed == ["one.cc"] and not client._values

    asyncio.run(run())


def test_async_close_attempts_every_owner_and_transport_after_rpc_failure(monkeypatch):
    async def run():
        client = AsyncClient()
        client._loop = asyncio.get_running_loop()
        attempted = []

        class Channel:
            closed = False

            async def close(self):
                self.closed = True

        channel = Channel()
        client._channel = channel

        async def parse(path, **kwargs):
            return parse_response_pb2.ParseResponse(session_id=path, result_revision=1)

        async def close(identifier):
            attempted.append(identifier)
            if identifier == "one.cc":
                raise CursorError(grpc.StatusCode.UNAVAILABLE, "close failed")

        monkeypatch.setattr(client, "_ensure_stub", lambda: None)
        monkeypatch.setattr(client, "_parse_response", parse)
        monkeypatch.setattr(client, "close_match", close)
        first, second = await client.parse("one.cc"), await client.parse("two.cc")
        with pytest.raises(CursorError, match="close failed"):
            await client.aclose()
        assert first._owner.closed and second._owner.closed
        assert set(attempted) == {"one.cc", "two.cc"}
        assert channel.closed and client._channel is None
        assert client._value_closed and client._pending_value_cleanup == {"one.cc"}

        async def retry(identifier):
            attempted.append(identifier)

        monkeypatch.setattr(client, "close_match", retry)
        await client.aclose()
        assert attempted.count("one.cc") == 2
        assert not client._values and not client._pending_value_cleanup

    asyncio.run(run())


def test_async_close_aggregates_rpc_failures(monkeypatch):
    async def run():
        client = AsyncClient()
        client._loop = asyncio.get_running_loop()
        attempted = []

        async def parse(path, **kwargs):
            return parse_response_pb2.ParseResponse(session_id=path, result_revision=1)

        async def close(identifier):
            attempted.append(identifier)
            raise CursorError(grpc.StatusCode.UNAVAILABLE, identifier)

        monkeypatch.setattr(client, "_ensure_stub", lambda: None)
        monkeypatch.setattr(client, "_parse_response", parse)
        monkeypatch.setattr(client, "close_match", close)
        first, second = await client.parse("one.cc"), await client.parse("two.cc")
        with pytest.raises(ExceptionGroup) as failure:
            await client.aclose()
        assert len(failure.value.exceptions) == 2
        assert set(attempted) == {"one.cc", "two.cc"}
        assert first._owner.closed and second._owner.closed

        async def retry(identifier):
            return None

        monkeypatch.setattr(client, "close_match", retry)
        await client.aclose()

    asyncio.run(run())


def test_off_loop_finalizer_queued_before_shutdown_does_not_reopen_channel(monkeypatch):
    async def run():
        client = AsyncClient()
        client._loop = asyncio.get_running_loop()
        closed = []

        class Channel:
            async def close(self):
                return None

        client._channel = Channel()

        def ensure():
            if client._channel is None:
                client._channel = Channel()

        async def parse(path, **kwargs):
            return parse_response_pb2.ParseResponse(session_id=path, result_revision=1)

        async def close(identifier):
            ensure()
            closed.append(identifier)

        monkeypatch.setattr(client, "_ensure_stub", ensure)
        monkeypatch.setattr(client, "_parse_response", parse)
        monkeypatch.setattr(client, "close_match", close)
        tree = await client.parse("thread-cursor")
        thread = Thread(target=tree._owner.close)
        thread.start()
        thread.join()
        await client.aclose()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        assert closed == ["thread-cursor"]
        assert client._channel is None and not client._value_cleanup
        assert not client._pending_value_cleanup

    asyncio.run(run())


def test_async_value_cleanup_is_cancellation_safe_and_owner_scoped(monkeypatch):
    async def run():
        client = AsyncClient()
        client._loop = asyncio.get_running_loop()
        entered, release = asyncio.Event(), asyncio.Event()

        async def parse(path, **kwargs):
            return parse_response_pb2.ParseResponse(session_id=str(path), result_revision=1)

        async def close(identifier):
            if identifier == "old":
                entered.set()
                await release.wait()

        monkeypatch.setattr(client, "_ensure_stub", lambda: None)
        monkeypatch.setattr(client, "_parse_response", parse)
        monkeypatch.setattr(client, "close_match", close)
        old = await client.parse("old")
        closing = asyncio.create_task(old.aclose())
        await asyncio.wait_for(entered.wait(), 2)
        closing.cancel()
        with pytest.raises(asyncio.CancelledError):
            await closing
        cleanup = client._value_cleanup_by_id["old"]
        assert not cleanup.cancelled()
        unrelated = await asyncio.wait_for(client.parse("unrelated"), 1)
        assert unrelated.path == "unrelated"
        release.set()
        await client._close_value_cleanup("old")
        await client.aclose()

    asyncio.run(run())


@pytest.mark.parametrize("persistent", [False, True])
def test_async_failed_background_cleanup_is_consumed_retried_and_reported(monkeypatch, persistent):
    async def run():
        client = AsyncClient()
        client._loop = asyncio.get_running_loop()
        loop = asyncio.get_running_loop()
        previous_handler = loop.get_exception_handler()
        unhandled = []
        loop.set_exception_handler(lambda _loop, context: unhandled.append(context))
        attempts = []

        async def parse(path, **kwargs):
            return parse_response_pb2.ParseResponse(session_id=str(path), result_revision=1)

        async def close(identifier):
            attempts.append(identifier)
            if identifier == "old" and (persistent or attempts.count("old") == 1):
                raise CursorError(grpc.StatusCode.UNAVAILABLE, "cleanup unavailable")

        monkeypatch.setattr(client, "_ensure_stub", lambda: None)
        monkeypatch.setattr(client, "_parse_response", parse)
        monkeypatch.setattr(client, "close_match", close)
        try:
            old = await client.parse("old")
            old.close()
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            assert client._pending_value_cleanup == {"old"}
            assert not client._value_cleanup
            assert not unhandled

            await client.parse("next")
            await asyncio.sleep(0)
            await asyncio.sleep(0)
            assert attempts.count("old") == 2
            assert not unhandled
            if persistent:
                assert client._pending_value_cleanup == {"old"}
                with pytest.raises(CursorError, match="cleanup unavailable"):
                    await client.aclose()
                monkeypatch.setattr(client, "close_match", lambda _identifier: asyncio.sleep(0))
                await client.aclose()
            else:
                assert not client._pending_value_cleanup
                await client.aclose()
        finally:
            loop.set_exception_handler(previous_handler)

    asyncio.run(run())


def test_async_value_close_does_not_wait_for_sibling_cleanup(monkeypatch):
    async def run():
        client = AsyncClient()
        client._loop = asyncio.get_running_loop()
        sibling_entered, release_sibling = asyncio.Event(), asyncio.Event()

        async def parse(path, **kwargs):
            return parse_response_pb2.ParseResponse(session_id=str(path), result_revision=1)

        async def close(identifier):
            if identifier == "sibling":
                sibling_entered.set()
                await release_sibling.wait()

        monkeypatch.setattr(client, "_ensure_stub", lambda: None)
        monkeypatch.setattr(client, "_parse_response", parse)
        monkeypatch.setattr(client, "close_match", close)
        sibling, selected = await client.parse("sibling"), await client.parse("selected")
        sibling.close()
        await asyncio.wait_for(sibling_entered.wait(), 2)
        await asyncio.wait_for(selected.aclose(), 1)
        assert selected._owner.closed
        release_sibling.set()
        await client._close_value_cleanup("sibling")
        await client.aclose()

    asyncio.run(run())


def test_async_retained_context_rejects_foreign_loop_before_mutation(monkeypatch):
    async def run():
        client = AsyncClient()
        client._loop = asyncio.get_running_loop()

        async def parse(path, **kwargs):
            return parse_response_pb2.ParseResponse(session_id=str(path), result_revision=1)

        monkeypatch.setattr(client, "_ensure_stub", lambda: None)
        monkeypatch.setattr(client, "_parse_response", parse)
        monkeypatch.setattr(client, "close_match", lambda identifier: asyncio.sleep(0))
        tree = await client.parse("foreign-loop")

        async def foreign_use():
            with pytest.raises(RuntimeError, match="owning event loop"):
                async with tree:
                    pass
            with pytest.raises(RuntimeError, match="owning event loop"):
                await tree.__aexit__(None, None, None)
            assert not tree._owner.closed

        await asyncio.to_thread(lambda: asyncio.run(foreign_use()))
        await client.aclose()

    asyncio.run(run())


def test_sync_close_attempts_all_owners_and_retains_failed_cleanup_ids(owned_client, monkeypatch):
    client, _, closed = owned_client
    first, second = client.parse("one.cc"), client.parse("two.cc")
    original = client._cursor_call
    attempted = []

    def call(method, *args, **kwargs):
        if method == "close_match":
            attempted.append(args[0])
            if args[0] == "cursor-1":
                raise CursorError(grpc.StatusCode.UNAVAILABLE, "close failed")
        return original(method, *args, **kwargs)

    monkeypatch.setattr(client, "_cursor_call", call)
    with pytest.raises(CursorError, match="close failed"):
        client.close()
    assert first._owner.closed and second._owner.closed
    assert set(attempted) == {"cursor-1", "cursor-2"}
    assert client._pending_value_cleanup == {"cursor-1"}
    monkeypatch.setattr(client, "_cursor_call", original)
    client.close()
    assert set(closed) == {"cursor-1", "cursor-2"}


def test_match_and_tree_contexts_keep_dependent_children_alive(owned_client):
    client, requests, closed = owned_client
    with client:
        with client.parse("example.cc") as tree:
            functions = tree.match('functionDecl().bind("f")')
        assert closed == ["cursor-1"]
        with functions:
            alias = functions
            calls = functions.binding("f").match('callExpr().bind("call")')
            first = functions[0].binding("f").match('callExpr().bind("call")')
        assert alias._owner.closed
        with pytest.raises(MatchValueError, match="closed"):
            alias.binding("f").match("callExpr()")
        functions.close()
        assert closed.count("cursor-2") == 1
        with calls:
            child = calls.binding("call").match('integerLiteral().bind("n")')
        assert len(child) == 1
        assert requests[-1][1][0].binding.expected_result_revision == 1
        with client.match('functionDecl().bind("f")', file="example.cc") as singular:
            assert isinstance(singular, MatchValue)
        first.close()
    assert len(closed) == len(set(closed)) == 6


def test_singular_and_plural_file_match_arguments_cannot_conflict(owned_client):
    client, requests, _ = owned_client
    with pytest.raises(ValueError, match="either file or files"):
        client.match("decl()", file="one.cc", files=["two.cc"])
    assert not requests


def test_async_singular_matches_tree_contexts_and_ergonomic_continuation(monkeypatch):
    async def run():
        client = AsyncClient()
        client._loop = asyncio.get_running_loop()
        count = 0
        closed = []

        async def parse(path, **kwargs):
            nonlocal count
            count += 1
            return parse_response_pb2.ParseResponse(session_id=f"context-{count}", result_revision=1)

        async def match(request, *, on_row=None, source_session_id=None):
            nonlocal count
            count += 1
            return await streamed_response(response(f"context-{count}", request.query), on_row)

        async def close(identifier):
            closed.append(identifier)

        monkeypatch.setattr(client, "_ensure_stub", lambda: None)
        monkeypatch.setattr(client, "_parse_response", parse)
        monkeypatch.setattr(client, "_stream_cursor_match", match)
        monkeypatch.setattr(client, "close_match", close)
        async with client:
            async with await client.parse("example.cc") as tree:
                functions = await tree.match('functionDecl().bind("f")')
            assert closed == ["context-1"]
            async with functions:
                calls = await functions.binding("f").match('callExpr().bind("call")')
            assert set(closed) == {"context-1", "context-2"}
            async with calls:
                child = await calls.binding("call").match("integerLiteral()")
            assert len(child) == 1
            async with await client.match('functionDecl().bind("f")', file="example.cc") as singular:
                assert len(singular) == 2
            with pytest.raises(ValueError, match="either file or files"):
                await client.match("decl()", ["one.cc"], file="two.cc")
        assert set(closed) == {f"context-{index}" for index in range(1, 6)}
        assert not client._value_cleanup and not client._pending_value_cleanup

    asyncio.run(run())
