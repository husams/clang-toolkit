"""CFG stream ordering, terminal status, backpressure and cleanup contracts."""
from __future__ import annotations
import asyncio
from contextlib import aclosing
import grpc
import pytest
from clang_toolkit import AsyncClient, Client
from clang_toolkit import client as module
from clang_toolkit.analysis_error import AnalysisError
from clang_toolkit._generated.analysis.v1 import cfg_stream_pb2 as pb
from test_match_stream import Stream, Channel


def events():
    start = pb.CfgStreamEvent()
    start.graph_started.graph.entry_block = 1
    start.graph_started.graph.is_complete = True
    block = pb.CfgStreamEvent()
    block.block.block.block_index = 0
    end = pb.CfgStreamEvent(graph_completed=pb.CfgGraphCompleted(block_count=1, is_complete=True))
    done = pb.CfgStreamEvent(completed=pb.CfgCompleted(graph_count=1, block_count=1))
    return [start, block, end, done]


def setup_stream(monkeypatch, values, **kwargs):
    stream = Stream(values, **kwargs)
    class Stub:
        def StreamCfg(self, request, *, timeout):
            self.request = request
            return stream
    stub = Stub()
    monkeypatch.setattr(module.grpc.aio, "insecure_channel", lambda *a, **k: Channel())
    monkeypatch.setattr(module.query_pb2_grpc, "QueryServiceStub", lambda c: object())
    monkeypatch.setattr(module.match_service_pb2_grpc, "MatchServiceStub", lambda c: object())
    monkeypatch.setattr(module.analysis_service_pb2_grpc, "AnalysisServiceStub", lambda c: stub)
    return stream, stub


def test_callbacks_precede_completion_and_collector_keeps_graphs(monkeypatch):
    stream, stub = setup_stream(monkeypatch, events())
    seen = []
    def consume(event):
        assert not stream.finished
        seen.append(event.WhichOneof("event"))
    with Client(address="unix:///tmp/test.sock") as client:
        result = client.stream_cfg("f", path="fixture.cc", on_event=consume)
    assert result.graph_count == 1 and result.block_count == 1
    assert seen == ["graph_started", "block", "graph_completed", "completed"]
    assert stub.request.function == "f" and stub.request.HasField("file")
    setup_stream(monkeypatch, events())
    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            result = await client.cfg("fixture.cc", "f")
            assert len(result.graphs) == 1 and len(result.graphs[0].blocks) == 1
            assert result.graphs[0].is_complete
    asyncio.run(run())


@pytest.mark.parametrize("bad", [
    lambda e: e[:-1], lambda e: e[1:], lambda e: [e[0], e[1], e[1], *e[2:]],
    lambda e: [e[0], e[2], e[3]], lambda e: [e[0], e[1], e[3]],
    lambda e: e + [e[-1]], lambda e: [pb.CfgStreamEvent()],
    lambda e: [e[0], e[1], e[2], pb.CfgStreamEvent(completed=pb.CfgCompleted())],
])
def test_malformed_stream_is_rejected(monkeypatch, bad):
    setup_stream(monkeypatch, bad(events()))
    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            with pytest.raises(AnalysisError) as error:
                await client.cfg("fixture.cc", "f")
            assert error.value.code == grpc.StatusCode.DATA_LOSS
    asyncio.run(run())


def test_early_close_callback_failure_and_terminal_status(monkeypatch):
    stream, _ = setup_stream(monkeypatch, events())
    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            async with aclosing(client.cfg_stream("fixture.cc", "f")) as values:
                async for event in values:
                    break
            assert client._value_operation_count == 0
    asyncio.run(run())
    assert stream.cancelled
    stream, _ = setup_stream(monkeypatch, events())
    async def fail():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            def consume(event):
                raise ValueError("stop")
            with pytest.raises(ValueError, match="stop"):
                await client.stream_cfg("fixture.cc", "f", on_event=consume)
    asyncio.run(fail())
    assert stream.cancelled
    setup_stream(monkeypatch, events(), status=grpc.StatusCode.CANCELLED)
    async def cancelled():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            with pytest.raises(AnalysisError) as error:
                await client.cfg("fixture.cc", "f")
            assert error.value.code == grpc.StatusCode.CANCELLED
    asyncio.run(cancelled())


def test_rpc_start_failure_releases_operation(monkeypatch):
    _, stub = setup_stream(monkeypatch, [])
    def fail(*args, **kwargs):
        raise RuntimeError("channel closed")
    monkeypatch.setattr(stub, "StreamCfg", fail)
    async def run():
        client = AsyncClient(address="unix:///tmp/test.sock")
        with pytest.raises(RuntimeError, match="channel closed"):
            await client.cfg("fixture.cc", "f")
        assert client._value_operation_count == 0
        await asyncio.wait_for(client.aclose(), timeout=1)
    asyncio.run(run())
