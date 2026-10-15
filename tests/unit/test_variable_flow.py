"""Variable-flow protocol completion and failure behavior."""
from __future__ import annotations
import asyncio
from contextlib import aclosing
import grpc
import pytest
from clang_toolkit import AsyncClient
from clang_toolkit import client as module
from clang_toolkit.analysis_error import AnalysisError
from clang_toolkit._generated.analysis.v1 import variable_flow_pb2 as pb
from test_match_stream import Stream, Channel
from unittest.mock import Mock
from clang_toolkit import Client
from clang_toolkit._value_lifecycle import CursorOwner
from clang_toolkit.match_values import BindingSelection, MatchValueError
from clang_toolkit.client import _variable_flow_request
from clang_toolkit.cli.runtime import Runtime


def events():
    start = pb.VariableFlowEvent()
    start.started.snapshot_generation = start.started.declaration_id = 1
    start.started.declaration.line = 4
    return [start,
            pb.VariableFlowEvent(usage=pb.VariableUsage(id=1, kind=pb.VariableUsage.DECLARE, provisional=True)),
            pb.VariableFlowEvent(fact=pb.VariableFlowFact(usage_id=1, initialization=pb.VariableFlowFact.UNINITIALIZED)),
            pb.VariableFlowEvent(completed=pb.VariableFlowCompleted(usage_count=1, fact_count=1, is_complete=True))]


def setup(monkeypatch, values, **kwargs):
    stream = Stream(values, **kwargs)
    class Stub:
        def StreamVariableFlow(self, request, *, timeout):
            return stream
    monkeypatch.setattr(module.grpc.aio, "insecure_channel", lambda *a, **k: Channel())
    monkeypatch.setattr(module.query_pb2_grpc, "QueryServiceStub", lambda c: object())
    monkeypatch.setattr(module.match_service_pb2_grpc, "MatchServiceStub", lambda c: object())
    monkeypatch.setattr(module.analysis_service_pb2_grpc, "AnalysisServiceStub", lambda c: Stub())
    return stream


def test_collector_and_callback_backpressure(monkeypatch):
    stream = setup(monkeypatch, events())
    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            seen = []
            def consume(event):
                assert not stream.finished
                seen.append(event.WhichOneof("event"))
            done = await client._stream_variable_flow_request(pb.VariableFlowRequest(), on_event=consume)
            assert done.is_complete and seen == ["started", "usage", "fact", "completed"]
            setup(monkeypatch, events())
            report = await client._collect_variable_flow_request(pb.VariableFlowRequest())
            assert report.analysis.declaration.line == 4 and len(report.usages) == len(report.facts) == 1
    asyncio.run(run())


@pytest.mark.parametrize("bad", [lambda e: e[:-1], lambda e: e[1:], lambda e: e + [e[-1]],
                               lambda e: [e[0], e[2], e[1], e[3]],
                               lambda e: [e[0], e[1], e[3]], lambda e: [pb.VariableFlowEvent()]])
def test_malformed_stream_fails(monkeypatch, bad):
    setup(monkeypatch, bad(events()))
    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            with pytest.raises(AnalysisError) as error:
                await client._collect_variable_flow_request(pb.VariableFlowRequest())
            assert error.value.code == grpc.StatusCode.DATA_LOSS
    asyncio.run(run())


def test_early_close_callback_failure_and_terminal_failure(monkeypatch):
    stream = setup(monkeypatch, events())
    async def run():
        async with AsyncClient(address="unix:///tmp/test.sock") as client:
            async with aclosing(client._variable_flow_events(pb.VariableFlowRequest())) as values:
                async for event in values:
                    break
            assert stream.cancelled and client._value_operation_count == 0
            failed = setup(monkeypatch, events())
            def stop(event):
                raise ValueError("stop")
            with pytest.raises(ValueError, match="stop"):
                await client._stream_variable_flow_request(pb.VariableFlowRequest(), on_event=stop)
            assert failed.cancelled
            setup(monkeypatch, events(), status=grpc.StatusCode.CANCELLED)
            with pytest.raises(AnalysisError) as error:
                await client._collect_variable_flow_request(pb.VariableFlowRequest())
            assert error.value.code == grpc.StatusCode.CANCELLED
    asyncio.run(run())


def test_request_ownership_limits_and_console_collection(tmp_path):
    client = Mock(spec=Client)
    owner = CursorOwner(client, "retained", 3, lambda _: None)
    variable = BindingSelection("v", owner, 0)
    function = BindingSelection("f", owner, 0)
    request = _variable_flow_request(client, variable, function)
    assert request.variable.expected_result_revision == 3 and request.function.match_index == 0
    with pytest.raises(MatchValueError):
        _variable_flow_request(Mock(spec=Client), variable, function)
    for kwargs in [{"max_events": 0}, {"max_iterations": True}, {"max_blocks": 100001}]:
        with pytest.raises(ValueError):
            _variable_flow_request(client, variable, function, **kwargs)
    runtime = Runtime(client, cwd=tmp_path)
    runtime.bindings["v"] = variable
    runtime.bindings["f"] = function
    client.variable_flow.return_value = pb.VariableFlowReport(completed=pb.VariableFlowCompleted(is_complete=True))
    runtime.execute('let report = variableflow $v in $f events 17 iterations 88')
    assert runtime.evaluate('$report.completed.is_complete') is True
    assert client.variable_flow.call_args.args == (variable, function)
    assert client.variable_flow.call_args.kwargs == {"max_events": 17, "max_iterations": 88}
