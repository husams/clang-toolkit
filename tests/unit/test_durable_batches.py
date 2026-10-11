from __future__ import annotations

import pytest
import asyncio

from clang_toolkit.batches import BatchRun, start_batch_request
from clang_toolkit._generated.analysis.v1 import batch_pb2
from clang_toolkit.resources import FileSet, InputDescriptor
from clang_toolkit.cli.language import parser
from clang_toolkit.client import AsyncClient
from clang_toolkit.configuration import NetworkConfig
from clang_toolkit._generated.analysis.v1 import analysis_service_pb2_grpc


def test_start_batch_request_preserves_frozen_inputs_and_idempotency_key() -> None:
    descriptor = InputDescriptor(
        "/remote/src/a.cpp",
        "profile-7",
        "/remote",
        ("-std=c++23",),
        "/remote/compile_commands.json",
        100,
        400,
        True,
    )
    request = start_batch_request(
        FileSet((descriptor,)),
        "let rows = match functionDecl() in $part.inputs; $rows;",
        size=2,
        group_variable="part",
        jobs=3,
        memory_bytes=4096,
        continue_on_error=True,
        request_id="stable-key",
    )
    assert request.request_id == "stable-key"
    assert request.WhichOneof("partition") == "size"
    assert request.size == 2
    assert request.jobs == 3 and request.memory_bytes == 4096
    assert request.continue_on_error is True
    assert request.inputs[0].profile.profile_id == "profile-7"
    assert request.inputs[0].profile.frozen is True


@pytest.mark.parametrize(
    "kwargs", [{}, {"size": 1, "count": 1}, {"size": 0}, {"count": 0}]
)
def test_start_batch_request_requires_one_positive_partition(
    kwargs: dict[str, int],
) -> None:
    descriptor = InputDescriptor("/src/a.cpp", "p", "/src", (), "", 1, 1, True)
    with pytest.raises(ValueError):
        start_batch_request((descriptor,), "print 1;", **kwargs)


def test_start_batch_request_allows_zero_count_for_empty_manifest() -> None:
    request = start_batch_request((), "1;", count=0)
    assert request.WhichOneof("partition") == "count"
    assert request.count == 0


def test_batch_run_promotes_only_completed_detached_responses() -> None:
    report = batch_pb2.BatchRun(run_id="run-1", revision=4, state="running")
    successful = report.groups.add(index=1, state="completed")
    successful.result.executed_steps = 3
    emission = successful.result.emissions.add(name="__final__")
    emission.value.scalar.integer = 17
    report.groups.add(index=2, state="failed")
    run = BatchRun(report)
    assert run.run_id == "run-1" and run.revision == 4
    assert run.results_complete is False
    assert run.result_group_indices == (1,)
    assert run.results[0].kind == "scalar"
    assert run.results[0].to_proto().scalar.integer == 17
    assert run.promote() == (17,)


def test_batch_promotion_converts_nested_scalars_and_match_rows() -> None:
    report = batch_pb2.BatchRun(run_id="run-values")
    group = report.groups.add(index=3, state="completed")
    final = group.result.emissions.add(name="__final__").value
    final.list.values.add().scalar.text = "done"
    row = final.list.values.add().matches.rows.add()
    row.source_match_index = 9
    row.bindings["f"].symbol_identity = "usr:example"
    run = BatchRun(report)

    result = run.promote()[0]
    assert result[0] == "done"
    assert result[1].rows[0].source_match_index == 9
    assert result[1].rows[0].bindings["f"].symbol_identity == "usr:example"
    snapshot = run.results[0]
    proto = snapshot.to_proto()
    proto.list.values[0].scalar.text = "changed"
    assert run.results[0].to_proto().list.values[0].scalar.text == "done"


def test_batch_promotion_enforces_value_limit_for_match_rows() -> None:
    report = batch_pb2.BatchRun(run_id="run-too-many-matches")
    group = report.groups.add(index=1, state="completed")
    final = group.result.emissions.add(name="__final__").value.matches
    for _ in range(10_001):
        final.rows.add()

    with pytest.raises(ValueError, match="exceeds 10000 values"):
        BatchRun(report).promote()


def test_async_client_sends_revision_checked_lifecycle_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, object]] = []

    class Stub:
        def __init__(self, _channel: object) -> None:
            pass

        async def StartBatch(
            self, request: object, **_kwargs: object
        ) -> batch_pb2.BatchRun:
            calls.append(("start", request))
            return batch_pb2.BatchRun(run_id="run-2", revision=1, state="running")

        async def BatchStatus(
            self, request: object, **_kwargs: object
        ) -> batch_pb2.BatchRun:
            calls.append(("status", request))
            return batch_pb2.BatchRun(run_id="run-2", revision=2, state="running")

        async def CancelBatch(
            self, request: object, **_kwargs: object
        ) -> batch_pb2.BatchRun:
            calls.append(("cancel", request))
            return batch_pb2.BatchRun(run_id="run-2", revision=3, state="cancelled")

        ResumeBatch = CancelBatch
        RetryBatch = CancelBatch

    monkeypatch.setattr(analysis_service_pb2_grpc, "AnalysisServiceStub", Stub)
    config = NetworkConfig(
        "unix:///unused", "unix", (), (), 1.0, None, 3, 100, 10, 1000
    )
    client = AsyncClient(config=config)
    client._stub = object()  # Keep the unit test independent of a transport.
    client._channel = object()  # type: ignore[assignment]

    async def exercise() -> None:
        run = await client.start_batch(
            (InputDescriptor("/srv/a.cpp", profile_id="frozen", frozen_profile=True),),
            "print $part.index;",
            size=1,
            request_id="request-2",
        )
        assert run.revision == 1
        status = await client.batch_status(run.run_id)
        assert status.revision == 2
        cancelled = await client.cancel_batch(run)
        assert cancelled.status == "cancelled"
        with pytest.raises(ValueError, match="expected_revision"):
            await client.retry_batch(run.run_id)

    asyncio.run(exercise())
    start_request = calls[0][1]
    assert start_request.request_id == "request-2"
    assert start_request.inputs[0].profile.profile_id == "frozen"
    assert calls[-1][0] == "cancel"
    assert calls[-1][1].expected_revision == 1


@pytest.mark.parametrize(
    "command",
    [
        "background batch part in $inputs size 2 do { let index = $part.index; $index; }",
        'durable batch part in $inputs count 1 request "same-key" do { let rows = match functionDecl() in $part.inputs; $rows; }',
        "batch status $run",
        "batch cancel $run",
        "batch resume $run",
        "batch retry $run",
        "batch promote $run",
    ],
)
def test_durable_batch_console_forms_parse(command: str) -> None:
    assert parser().parse(command).children
