import asyncio
from pathlib import Path

import pytest

from clang_toolkit import client as client_module
from clang_toolkit._generated.query.v1 import query_pb2
from clang_toolkit.client import AsyncClient, Client, QueryError, _format_violation


class Stream:
    def __init__(self, events):
        self.events = events
        self.cancelled = False

    def __aiter__(self):
        self.iterator = iter(self.events)
        return self

    async def __anext__(self):
        try:
            return next(self.iterator)
        except StopIteration:
            raise StopAsyncIteration from None

    def done(self):
        return False

    def cancel(self):
        self.cancelled = True
        return True


class Stub:
    def __init__(self, events):
        self.events = events
        self.request = None

    def Query(self, request, timeout=None):
        self.request = request
        self.timeout = timeout
        self.stream = Stream(self.events)
        return self.stream


class Channel:
    async def close(self):
        return None


def patch_transport(monkeypatch, events):
    stub = Stub(events)
    monkeypatch.setattr(client_module.grpc.aio, "insecure_channel", lambda *_args, **_kwargs: Channel())
    monkeypatch.setattr(client_module.query_pb2_grpc, "QueryServiceStub", lambda _channel: stub)
    return stub


def test_async_query_collects_completed_and_preserves_request(monkeypatch, tmp_path):
    events = [query_pb2.QueryEvent(started=query_pb2.Started()),
              query_pb2.QueryEvent(completed=query_pb2.Completed(match_count=0))]
    stub = patch_transport(monkeypatch, events)
    source = tmp_path / "sample.cpp"
    source.write_text("int value;", encoding="utf-8")

    async def run():
        client = AsyncClient(address="unix:///tmp/test.sock")
        got = await client.query(
            "varDecl()", [Path("sample.cpp")], working_directory=tmp_path,
            compile_arguments=["-std=c++20"],
        )
        await client.aclose()
        return got

    got = asyncio.run(run())
    assert [event.WhichOneof("event") for event in got] == ["started", "completed"]
    assert stub.request.files[0].path == str(source.resolve())
    assert list(stub.request.files[0].compile_arguments) == ["-std=c++20"]


def test_stream_without_completed_raises_with_partial_events(monkeypatch):
    partial = query_pb2.QueryEvent(started=query_pb2.Started())
    patch_transport(monkeypatch, [partial])

    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            return await client.query("varDecl()")

    with pytest.raises(QueryError, match="without Completed") as error:
        asyncio.run(run())
    assert error.value.partial_events == (partial,)


def test_background_query_retains_task_until_stream_consumed(monkeypatch):
    patch_transport(monkeypatch, [
        query_pb2.QueryEvent(started=query_pb2.Started()),
        query_pb2.QueryEvent(completed=query_pb2.Completed()),
    ])

    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            background = client.start_background_query("varDecl()")
            return await background.result()

    assert len(asyncio.run(run())) == 2


def test_sync_facade_rejects_use_inside_running_loop():
    async def run():
        with pytest.raises(RuntimeError, match="active event loop"):
            Client("unix:///tmp/test.sock").match("varDecl()")

    asyncio.run(run())


def test_limit_violation_format_includes_bytes_and_gibibytes():
    violation = query_pb2.LimitViolation(
        limit_name="session.overhead_memory_bytes",
        current_value=1_073_741_824,
        configured_limit=2_147_483_648,
        requested_increment=1_073_741_824,
        projected_value=3_221_225_472,
    )
    rendered = _format_violation(violation)
    assert "current 1073741824" in rendered
    assert "requested +1073741824" in rendered
    assert "projected 3221225472" in rendered
    assert "limit 2147483648" in rendered
    assert "3.00 GiB" in rendered
    assert "2.00 GiB" in rendered


def test_callback_failure_closes_and_cancels_partial_stream(monkeypatch):
    partial = query_pb2.QueryEvent(started=query_pb2.Started())
    stub = patch_transport(monkeypatch, [partial])

    async def run():
        client = AsyncClient(address="unix:///tmp/test.sock")
        def fail(_event):
            raise ValueError("callback failed")
        with pytest.raises(ValueError, match="callback failed"):
            await client.query("varDecl()", on_event=fail)
        stream = stub.stream
        await client.aclose()
        return stream

    stream = asyncio.run(run())
    assert stream.cancelled
