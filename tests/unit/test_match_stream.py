"""Streaming match publication, spooling and cleanup contracts."""

from __future__ import annotations

import asyncio

import grpc
import pytest

from clang_toolkit import AsyncClient, MatchValue
from clang_toolkit import client as client_module
from clang_toolkit import _row_store as row_store_module
from clang_toolkit._generated.match.v1 import match_result_pb2, match_service_pb2
from clang_toolkit._generated.match.v1 import match_stream_pb2
from clang_toolkit._row_store import RowStore
from clang_toolkit.cli.runtime import Runtime


def row(name: str) -> match_result_pb2.MatchResult:
    value = match_result_pb2.MatchResult()
    value.bindings[name].unsupported.clang_kind = "FunctionDecl"
    value.bindings[name].unsupported.detail = "original"
    return value


def completed(session_id: str, count: int) -> match_stream_pb2.MatchStreamEvent:
    value = match_stream_pb2.MatchStreamCompleted(
        session_id=session_id, result_revision=1, row_count=count
    )
    value.expires_at.GetCurrentTime()
    return match_stream_pb2.MatchStreamEvent(completed=value)


class Stream:
    def __init__(self, events, *, status=grpc.StatusCode.OK, before_terminal=None):
        self.events = list(events)
        self.status = status
        self.before_terminal = before_terminal
        self.cancelled = False
        self.finished = False

    def __aiter__(self):
        self.index = 0
        return self

    async def __anext__(self):
        if self.index >= len(self.events):
            self.finished = True
            raise StopAsyncIteration
        event = self.events[self.index]
        self.index += 1
        if event.WhichOneof("event") == "completed" and self.before_terminal:
            self.before_terminal()
        return event

    async def code(self):
        return self.status

    def details(self):
        return "mock terminal status"

    def done(self):
        return self.finished

    def cancel(self):
        self.cancelled = True
        return True


class Stub:
    def __init__(self, stream):
        self.stream = stream
        self.request = None
        self.stream_calls = 0

    def StreamMatch(self, request, *, timeout=None):
        self.stream_calls += 1
        self.request = request
        self.timeout = timeout
        return self.stream

    async def CloseSession(self, request, *, timeout=None):
        return match_service_pb2.CloseSessionResponse()


class Channel:
    async def close(self):
        return None


def patch_stream(monkeypatch, stream):
    stub = Stub(stream)
    monkeypatch.setattr(client_module.grpc.aio, "insecure_channel", lambda *_a, **_k: Channel())
    monkeypatch.setattr(client_module.query_pb2_grpc, "QueryServiceStub", lambda _c: object())
    monkeypatch.setattr(client_module.match_service_pb2_grpc, "MatchServiceStub", lambda _c: stub)
    return stub


def test_async_stream_calls_back_before_completion_and_publishes_copy(monkeypatch):
    original = row("f")
    saw_callback = []
    stream = Stream(
        [match_stream_pb2.MatchStreamEvent(row=original), completed("new-cursor", 1)],
        before_terminal=lambda: saw_callback.append("before-completion"),
    )
    stub = patch_stream(monkeypatch, stream)
    closed = []

    async def run():
        client = AsyncClient(address="unix:///tmp/test.sock")
        async def close(identifier):
            closed.append(identifier)
        monkeypatch.setattr(client, "close_match", close)

        callback_count = []
        def on_row(value):
            callback_count.append(1)
            value.bindings["f"].unsupported.detail = "callback mutation"

        value = await client.match_in("functionDecl()", "sample.cc", on_row=on_row)
        assert callback_count == [1]
        assert saw_callback == ["before-completion"]
        assert value[0].bindings["f"].unsupported.detail == "original"
        assert value._owner.session_id == "new-cursor"
        assert stub.request.WhichOneof("target") == "file"
        value.close()
        await client.aclose()
        return value, closed

    value, closed_ids = asyncio.run(run())
    assert closed_ids == ["new-cursor"]
    assert isinstance(value, MatchValue)


@pytest.mark.parametrize("events", [
    [completed("empty-cursor", 0)],
    [match_stream_pb2.MatchStreamEvent(row=row("a")),
     match_stream_pb2.MatchStreamEvent(row=row("a")), completed("two", 2)],
])
def test_stream_accepts_zero_and_duplicate_rows(monkeypatch, events):
    patch_stream(monkeypatch, Stream(events))

    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            return await client.match_in("decl()", "sample.cc")

    value = asyncio.run(run())
    assert len(value) == (0 if events[0].WhichOneof("event") == "completed" else 2)


@pytest.mark.parametrize("events", [
    [match_stream_pb2.MatchStreamEvent(row=row("f"))],
    [completed("cursor", 1)],
    [completed("first", 0), completed("second", 0)],
    [completed("cursor", 0), match_stream_pb2.MatchStreamEvent(row=row("late"))],
    [match_stream_pb2.MatchStreamEvent(row=row("f")), completed("cursor", 2)],
    [match_stream_pb2.MatchStreamEvent()],
])
def test_malformed_stream_never_publishes_and_cleans_completed_cursor(monkeypatch, events):
    stream = Stream(events)
    patch_stream(monkeypatch, stream)
    closed = []

    async def run():
        client = AsyncClient(address="unix:///tmp/test.sock")
        async def close(identifier):
            closed.append(identifier)
        monkeypatch.setattr(client, "close_match", close)
        with pytest.raises(Exception):
            await client.match_in("decl()", "sample.cc")
        assert not client._values
        await client.aclose()

    asyncio.run(run())
    assert stream.cancelled
    known = [event.completed.session_id for event in events
             if event.WhichOneof("event") == "completed"]
    if known:
        assert closed == [known[0]]


def test_non_ok_after_completion_discards_rows_and_cleans_new_cursor(monkeypatch):
    stream = Stream([match_stream_pb2.MatchStreamEvent(row=row("f")), completed("new", 1)],
                    status=grpc.StatusCode.UNAVAILABLE)
    patch_stream(monkeypatch, stream)
    closed = []

    async def run():
        client = AsyncClient(address="unix:///tmp/test.sock")
        async def close(identifier):
            closed.append(identifier)
        monkeypatch.setattr(client, "close_match", close)
        with pytest.raises(Exception, match="mock terminal status"):
            await client.match_in("decl()", "sample.cc")
        assert not client._values
        await client.aclose()

    asyncio.run(run())
    assert closed == ["new"]


def test_callback_exception_cancels_stream_without_publishing_value(monkeypatch):
    stream = Stream([match_stream_pb2.MatchStreamEvent(row=row("f")), completed("new", 1)])
    patch_stream(monkeypatch, stream)
    close = RowStore.close

    def close_with_error(value):
        close(value)
        raise OSError("spool close failed")

    monkeypatch.setattr(RowStore, "close", close_with_error)

    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            def fail(_value):
                raise ValueError("callback stopped")

            with pytest.raises(ValueError, match="callback stopped"):
                await client.match_in("decl()", "sample.cc", on_row=fail)
            assert not client._values

    asyncio.run(run())
    assert stream.cancelled


def test_row_store_constructor_failure_happens_before_stream_opens(monkeypatch):
    stream = Stream([])
    stub = patch_stream(monkeypatch, stream)

    def fail_temporary_file(*_args, **_kwargs):
        raise OSError("cannot create spool index")

    monkeypatch.setattr(row_store_module.tempfile, "TemporaryFile", fail_temporary_file)

    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            with pytest.raises(OSError, match="cannot create spool index"):
                await client.match_in("decl()", "sample.cc")

    asyncio.run(run())
    assert stub.stream_calls == 0
    assert not stream.cancelled


def test_partially_initialized_row_store_finalizer_is_safe():
    partial = RowStore.__new__(RowStore)
    partial.__del__()


def test_cancel_before_completion_cancels_stream_without_source_cleanup(monkeypatch):
    class WaitingStream(Stream):
        def __init__(self):
            super().__init__([match_stream_pb2.MatchStreamEvent(row=row("f"))])
            self.waiting = asyncio.Event()

        async def __anext__(self):
            if self.index == 0:
                self.index += 1
                return self.events[0]
            self.waiting.set()
            await asyncio.Future()

    stream = WaitingStream()
    patch_stream(monkeypatch, stream)
    closed = []

    async def run():
        client = AsyncClient(address="unix:///tmp/test.sock")
        async def close(identifier):
            closed.append(identifier)
        monkeypatch.setattr(client, "close_match", close)
        operation = asyncio.create_task(client.match_in("decl()", "sample.cc"))
        await stream.waiting.wait()
        operation.cancel()
        with pytest.raises(asyncio.CancelledError):
            await operation
        await client.aclose()

    asyncio.run(run())
    assert stream.cancelled and not closed


def test_store_failure_cancels_stream(monkeypatch):
    stream = Stream([match_stream_pb2.MatchStreamEvent(row=row("f"))])
    patch_stream(monkeypatch, stream)
    monkeypatch.setattr(RowStore, "append", lambda *_, **__: (_ for _ in ()).throw(
        OSError("disk full")))

    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            with pytest.raises(OSError, match="disk full"):
                await client.match_in("decl()", "sample.cc")

    asyncio.run(run())
    assert stream.cancelled


def test_deferred_spool_failure_discards_completed_value(monkeypatch):
    stream = Stream([match_stream_pb2.MatchStreamEvent(row=row("f")), completed("new", 1)])
    patch_stream(monkeypatch, stream)
    monkeypatch.setattr(RowStore, "flush", lambda *_: (_ for _ in ()).throw(
        OSError("deferred disk full")))
    closed = []

    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            async def close(identifier):
                closed.append(identifier)
            monkeypatch.setattr(client, "close_match", close)
            with pytest.raises(OSError, match="deferred disk full"):
                await client.match_in("decl()", "sample.cc")
            assert not client._values

    asyncio.run(run())
    assert stream.cancelled and closed == ["new"]


def test_spilled_store_random_access_and_match_rows_survive_native_close(monkeypatch):
    store = RowStore(memory_limit=2)
    values = [row("first"), row("second"), row("third")]
    for value in values:
        store.append(value.SerializeToString())
    assert store.spilled
    assert [list(match_result_pb2.MatchResult.FromString(store.read(i)).bindings)
            for i in range(3)] == [["first"], ["second"], ["third"]]

    stream = Stream([match_stream_pb2.MatchStreamEvent(row=values[0]), completed("owned", 1)])
    patch_stream(monkeypatch, stream)

    async def run():
        client = AsyncClient(address="unix:///tmp/test.sock")
        monkeypatch.setattr(client, "close_match", lambda _id: asyncio.sleep(0))
        value = await client.match_in("decl()", "sample.cc")
        row_value = next(value.iter_rows())
        value.close()
        assert row_value.bindings["first"].unsupported.detail == "original"
        await client.aclose()

    asyncio.run(run())
    store.close()


def test_streamed_binding_names_avoid_reopening_spool_for_discovery(monkeypatch, tmp_path):
    stream = Stream([
        match_stream_pb2.MatchStreamEvent(row=row("f")),
        match_stream_pb2.MatchStreamEvent(row=row("f")),
        completed("named", 2),
    ])
    patch_stream(monkeypatch, stream)

    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            value = await client.match_in("functionDecl()", "sample.cc")

            def unexpected_spool_read(*_args, **_kwargs):
                raise AssertionError("binding discovery reread serialized rows")

            monkeypatch.setattr(value._store, "read", unexpected_spool_read)
            monkeypatch.setattr(value._store, "iter_bytes", unexpected_spool_read)
            assert value.binding_names() == {"f"}
            assert value.binding_names() == {"f"}
            assert value.binding("f").name == "f"

            runtime = Runtime(client, cwd=tmp_path)
            runtime.bindings["matches"] = value
            assert runtime.completion_references()["matches"] == (
                "f", "isEmpty", "length"
            )

    asyncio.run(run())


def test_raw_row_store_append_falls_back_to_one_cached_scan(monkeypatch):
    store = RowStore()
    store.append(row("legacy").SerializeToString())
    original_iter = store.iter_bytes
    scan_count = 0

    def counted_iter():
        nonlocal scan_count
        scan_count += 1
        yield from original_iter()

    monkeypatch.setattr(store, "iter_bytes", counted_iter)
    assert store.binding_names() == {"legacy"}
    assert store.binding_names() == {"legacy"}
    assert scan_count == 1
    store.close()
