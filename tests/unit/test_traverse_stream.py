"""Incremental traversal ordering, backpressure and incomplete-stream cleanup."""
from __future__ import annotations
import asyncio
from contextlib import aclosing
import grpc
import pytest
from clang_toolkit import AsyncClient, Client
from clang_toolkit import client as module
from clang_toolkit.analysis_error import AnalysisError
from clang_toolkit._generated.analysis.v1 import traverse_stream_pb2 as pb
from clang_toolkit._generated.analysis.v1 import traversal_node_pb2 as nodes
from test_match_stream import Stream, Channel


def visit(index=0, depth=0, parent=None):
    node = nodes.TraversalNode(index=index, depth=depth, native_kind="BuiltinType")
    if parent is not None:
        node.parent_index = parent
    return pb.TraverseStreamEvent(node=node)


def complete(count):
    return pb.TraverseStreamEvent(completed=pb.TraverseCompleted(node_count=count))


def setup_stream(monkeypatch, events, **kwargs):
    stream = Stream(events, **kwargs)
    class Stub:
        def StreamTraverse(self, request, *, timeout):
            self.request = request
            return stream
    stub = Stub()
    monkeypatch.setattr(module.grpc.aio, "insecure_channel", lambda *a, **k: Channel())
    monkeypatch.setattr(module.query_pb2_grpc, "QueryServiceStub", lambda c: object())
    monkeypatch.setattr(module.match_service_pb2_grpc, "MatchServiceStub", lambda c: object())
    monkeypatch.setattr(module.analysis_service_pb2_grpc, "AnalysisServiceStub", lambda c: stub)
    return stream, stub


def test_callback_runs_before_next_event_and_completion(monkeypatch):
    stream, stub = setup_stream(monkeypatch, [visit(), visit(1, 1, 0), complete(2)])
    seen = []
    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            async def callback(node):
                assert stream.index == node.index + 1
                assert not stream.finished
                seen.append(node.index)
                await asyncio.sleep(0)
            result = await client.stream_traverse("fixture.cc", on_node=callback)
            assert result.node_count == 2
    asyncio.run(run())
    assert seen == [0, 1]
    assert stub.request.HasField("file")


@pytest.mark.parametrize("events", [
    [visit()], [visit(1), complete(1)], [visit(), complete(2)],
    [complete(0), visit()], [pb.TraverseStreamEvent()],
    [visit(), visit(1, 1, 1), complete(2)], [visit(0, 1, 0), complete(1)],
    [visit(), visit(1, 0, 0), complete(2)],
])
def test_incomplete_or_malformed_stream_is_never_success(monkeypatch, events):
    stream, _ = setup_stream(monkeypatch, events)
    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            with pytest.raises(AnalysisError) as caught:
                await client.stream_traverse("fixture.cc", on_node=lambda n: None)
            assert caught.value.code == grpc.StatusCode.DATA_LOSS
    asyncio.run(run())


def test_terminal_failure_after_completion_is_rejected(monkeypatch):
    setup_stream(monkeypatch, [visit(), complete(1)], status=grpc.StatusCode.RESOURCE_EXHAUSTED)
    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            with pytest.raises(AnalysisError) as caught:
                await client.stream_traverse("fixture.cc", on_node=lambda n: None)
            assert caught.value.code == grpc.StatusCode.RESOURCE_EXHAUSTED
    asyncio.run(run())


def test_early_iterator_close_and_callback_failure_cancel_stream(monkeypatch):
    stream, _ = setup_stream(monkeypatch, [visit(), complete(1)])
    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            async with aclosing(client.traverse_stream("fixture.cc")) as events:
                async for event in events:
                    break
    asyncio.run(run())
    assert stream.cancelled
    stream, _ = setup_stream(monkeypatch, [visit(), complete(1)])
    async def fail():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            def callback(node):
                raise ValueError("stop")
            with pytest.raises(ValueError, match="stop"):
                await client.stream_traverse("fixture.cc", on_node=callback)
    asyncio.run(fail())
    assert stream.cancelled


def test_sync_callback_streams_without_collecting(monkeypatch):
    stream, _ = setup_stream(monkeypatch, [visit(), complete(1)])
    seen = []
    def callback(node):
        assert not stream.finished
        seen.append(node.index)
    result = Client(address="unix:///tmp/test.sock").stream_traverse("fixture.cc", on_node=callback)
    assert seen == [0] and result.node_count == 1


def test_rpc_start_failure_releases_client_operation(monkeypatch):
    _, stub = setup_stream(monkeypatch, [])
    def fail(*args, **kwargs):
        raise RuntimeError("channel closed")
    monkeypatch.setattr(stub, "StreamTraverse", fail)
    async def run():
        client = AsyncClient(address="unix:///tmp/test.sock")
        with pytest.raises(RuntimeError, match="channel closed"):
            await client.stream_traverse("fixture.cc", on_node=lambda n: None)
        assert client._value_operation_count == 0
        await asyncio.wait_for(client.aclose(), timeout=1)
    asyncio.run(run())
