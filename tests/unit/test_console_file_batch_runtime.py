from __future__ import annotations

from dataclasses import dataclass
import os
import asyncio
from pathlib import Path
import signal
import threading
import time
from types import SimpleNamespace

import pytest
import grpc

from clang_toolkit.analysis_error import AnalysisError
from clang_toolkit.cli.runtime.evaluator import EvaluationError, Runtime
from clang_toolkit.cli.runtime.batch_execution import BatchInterrupted
from clang_toolkit.cli.app import _run_batch_with_interrupts
from clang_toolkit.cli.app import dispatch_result
from clang_toolkit.cursors import CursorError
from clang_toolkit.resources import FileHandle, FileSet, InputDescriptor
from clang_toolkit._generated.match.v1 import match_service_pb2
from clang_toolkit._value_lifecycle import CursorOwner
from clang_toolkit.match_values import MatchValue


@dataclass
class _ScopeInfo:
    cleanup_acknowledged: bool = True
    state: str = "released"
    peak_accounted_bytes: int = 64
    peak_reserved_bytes: int = 128
    file_leases: int = 0


class _Scope:
    def __init__(self, owner, inputs, kwargs):
        self.owner = owner
        self.inputs = tuple(inputs)
        self.kwargs = kwargs
        self.info = _ScopeInfo()
        self.cancelled = False
        self.released = False

    def cancel(self):
        self.cancelled = True
        return self.info

    def release(self):
        self.released = True
        return self.info

    def describe(self):
        return self.info


class _Client:
    def __init__(self):
        self.scopes = []
        self.opened = []
        self.closed = []
        self.discovery_args = None
        self.matches = []

    def discover_files(self, paths, **kwargs):
        self.discovery_args = (paths, kwargs)
        return FileSet(
            tuple(
                InputDescriptor.from_path(
                    path, working_directory=kwargs["working_directory"]
                )
                for path in paths
            )
        )

    def open_file(self, value, **kwargs):
        descriptor = (
            value
            if isinstance(value, InputDescriptor)
            else InputDescriptor.from_path(value)
        )
        handle = FileHandle(f"lease-{len(self.opened) + 1}", descriptor, self)
        self.opened.append((handle, kwargs))
        return handle

    def list_files(self):
        return tuple(handle for handle, _ in self.opened)

    def file_info(self, handle):
        return {"lease_id": handle.lease_id, "path": handle.path}

    def close_file(self, handle):
        self.closed.append(handle)
        return {"closed": handle.lease_id}

    def close_all_files(self):
        return {"closed_count": len(self.opened)}

    def refresh_file(self, handle, **kwargs):
        return self.open_file(handle.input, **kwargs)

    def open_resource_scope(self, *, inputs, **kwargs):
        scope = _Scope(self, inputs, kwargs)
        self.scopes.append(scope)
        return scope

    def resource_status(self):
        from types import SimpleNamespace

        return SimpleNamespace(
            explicit_file_leases=1,
            scopes=[scope.info for scope in self.scopes if not scope.released],
        )

    def match_in(self, query, target, **kwargs):
        self.matches.append((query, target, kwargs))
        return _FakeMatch()


def _FakeMatch():
    response = match_service_pb2.MatchResponse()
    response.results.add().source_match_index = 1
    owner = CursorOwner(object(), "unit-cursor", 1, lambda _session: None)
    return MatchValue._from_response(response, owner, source_file="fixture.cc")


def _runtime(tmp_path: Path) -> tuple[Runtime, _Client]:
    client = _Client()
    return Runtime(client, cwd=tmp_path, environment={"HOME": str(tmp_path)}), client


def test_file_discovery_and_lease_commands_preserve_aliases(tmp_path: Path):
    runtime, client = _runtime(tmp_path)
    runtime.execute('let inputs = files ["a.cc", "b.cc"]')
    inputs = runtime.bindings["inputs"]
    assert isinstance(inputs, FileSet)
    assert len(inputs) == 2
    assert client.discovery_args[1]["working_directory"] == tmp_path

    runtime.execute("file open $inputs.inputs[0] into $source")
    handle = runtime.bindings["source"]
    assert isinstance(handle, FileHandle)
    alias = handle
    assert "file_info" not in str(runtime.execute("file info $source"))
    runtime.execute("file close $source")
    assert client.closed == [alias]
    assert runtime.bindings["source"] is alias

    runtime.execute("file refresh $source into $updated")
    assert runtime.bindings["updated"].path == alias.path
    runtime.execute("resource status")
    runtime.close()


def test_batch_scopes_are_sequential_and_do_not_export_locals(tmp_path: Path, capsys):
    runtime, client = _runtime(tmp_path)
    runtime.bindings["inputs"] = FileSet(
        tuple(
            InputDescriptor.from_path(f"{index}.cc", working_directory=tmp_path)
            for index in range(5)
        )
    )

    report = runtime.execute(
        'batch part in $inputs size 2 jobs 1 memory "16MiB" do { '
        "let summary = $part.index; print $part.length; }"
    )

    assert '"completed_groups":3' in report
    assert '"accepted_inputs":5' in report
    assert '"completed_files":0' in report
    assert '"unattempted_files":5' in report
    assert '"exported_outputs":0' in report
    assert '"peak_accounted_bytes":64' in report
    assert '"peak_reserved_bytes":128' in report
    assert '"remaining_external_pins":1' in report
    assert [scope.inputs for scope in client.scopes] == [
        runtime.bindings["inputs"].inputs[:2],
        runtime.bindings["inputs"].inputs[2:4],
        runtime.bindings["inputs"].inputs[4:],
    ]
    assert all(scope.released and not scope.cancelled for scope in client.scopes)
    assert all(
        scope.kwargs["memory_bytes"] == 16 * 1024 * 1024 for scope in client.scopes
    )
    assert "summary" not in runtime.bindings
    output_lines = capsys.readouterr().out.splitlines()
    assert [line for line in output_lines if line in {"1", "2"}] == ["2", "2", "1"]


def test_batch_match_uses_frozen_input_profile_and_active_scope(tmp_path: Path):
    runtime, client = _runtime(tmp_path)
    descriptor = InputDescriptor(
        str(tmp_path / "profiled.cc"),
        profile_id="profile-7",
        working_directory=str(tmp_path),
        compile_arguments=("-DVALUE=7",),
    )
    runtime.bindings["inputs"] = FileSet((descriptor,))

    runtime.execute(
        "batch part in $inputs size 1 do { "
        'let rows = match functionDecl().bind("f") in $part.inputs; }'
    )

    assert len(client.matches) == 1
    _, target, kwargs = client.matches[0]
    assert target is descriptor
    assert target.profile_id == "profile-7"
    assert kwargs["scope"] is client.scopes[0]
    assert client.scopes[0].inputs == (descriptor,)


def test_batch_implicit_match_targets_the_admitted_group(tmp_path: Path):
    runtime, client = _runtime(tmp_path)
    descriptor = InputDescriptor(
        str(tmp_path / "implicit.cc"),
        profile_id="implicit-profile",
        working_directory=str(tmp_path),
    )
    runtime.bindings["inputs"] = FileSet((descriptor,))

    runtime.execute(
        'batch part in $inputs size 1 do { let rows = match functionDecl().bind("f"); }'
    )

    assert len(client.matches) == 1
    _, target, kwargs = client.matches[0]
    assert target is descriptor
    assert kwargs["scope"] is client.scopes[0]


def test_batch_counts_only_inputs_actually_targeted_by_body(tmp_path: Path):
    runtime, client = _runtime(tmp_path)
    descriptors = tuple(
        InputDescriptor.from_path(f"{index}.cc", working_directory=tmp_path)
        for index in range(3)
    )
    runtime.bindings["inputs"] = FileSet(descriptors)

    report = runtime.execute(
        "batch part in $inputs size 3 do { "
        'let rows = match functionDecl().bind("f") in $part.inputs[0]; }'
    )

    assert '"completed_files":1' in report
    assert '"unattempted_files":2' in report
    assert len(client.matches) == 1
    assert client.matches[0][1] is descriptors[0]


def test_batch_match_collection_exports_only_path_provenance(
    tmp_path: Path, monkeypatch
):
    runtime, _ = _runtime(tmp_path)
    descriptor = InputDescriptor.from_path("one.cc", working_directory=tmp_path)
    runtime.bindings["inputs"] = FileSet((descriptor,))
    monkeypatch.setattr(runtime, "_match_files", lambda *args, **kwargs: [_FakeMatch()])

    result = runtime.evaluate('match functionDecl().bind("f") in $inputs')

    assert result.files == (descriptor.path,)


def test_jobs_inherit_effective_pool_size_when_omitted(tmp_path: Path):
    runtime, client = _runtime(tmp_path)
    runtime.bindings["inputs"] = FileSet(
        (InputDescriptor.from_path("one.cc", working_directory=tmp_path),)
    )
    client.config = SimpleNamespace(pool_size=3)

    report = runtime.execute("batch part in $inputs size 1 do { print $part.index; }")

    assert '"completed_groups":1' in report
    assert client.scopes[0].kwargs["jobs"] == 3
    assert client.config.pool_size == 3


def test_batch_report_counts_successful_save_exports(tmp_path: Path):
    runtime, _ = _runtime(tmp_path)
    runtime.bindings["inputs"] = FileSet(
        tuple(
            InputDescriptor.from_path(f"{index}.cc", working_directory=tmp_path)
            for index in range(2)
        )
    )

    report = runtime.execute(
        "batch part in $inputs size 1 do { "
        "let summary = $part.index; "
        'save $summary to "group-${part.index}.json" as json; }'
    )

    assert '"exported_outputs":2' in report
    assert (tmp_path / "group-1.json").read_text(encoding="utf-8") == "1"
    assert (tmp_path / "group-2.json").read_text(encoding="utf-8") == "2"


def test_explicit_jobs_override_pool_size_without_changing_global_config(
    tmp_path: Path,
):
    runtime, client = _runtime(tmp_path)
    runtime.bindings["inputs"] = FileSet(
        (InputDescriptor.from_path("one.cc", working_directory=tmp_path),)
    )
    client.config = SimpleNamespace(pool_size=6)

    report = runtime.execute(
        "batch part in $inputs size 1 jobs 4 do { print $part.index; }"
    )

    assert '"completed_groups":1' in report
    assert client.scopes[0].kwargs["jobs"] == 4
    assert client.config.pool_size == 6


def test_batch_failure_cancels_and_releases_scope_then_continues(tmp_path: Path):
    runtime, client = _runtime(tmp_path)
    runtime.bindings["inputs"] = FileSet(
        tuple(
            InputDescriptor.from_path(f"{index}.cc", working_directory=tmp_path)
            for index in range(3)
        )
    )

    result = dispatch_result(
        client,
        "batch part in $inputs size 1 on error continue do { print $missing; }",
        runtime,
    )

    assert not result.success
    assert '"failed_groups":3' in result.output
    assert '"failed_files":0' in result.output
    assert '"unattempted_files":3' in result.output
    assert '"completed_groups":0' in result.output
    assert len(client.scopes) == 3
    assert all(scope.cancelled and scope.released for scope in client.scopes)


def test_batch_import_definitions_and_resource_aliases_stay_in_group_scope(
    tmp_path: Path,
):
    runtime, client = _runtime(tmp_path)
    runtime.bindings["inputs"] = FileSet(
        (InputDescriptor.from_path("one.cc", working_directory=tmp_path),)
    )
    runtime.bindings["part"] = "outer binding"
    (tmp_path / "library.ctk").write_text(
        "let captured = $opened\nlet selected() = functionDecl()\n",
        encoding="utf-8",
    )

    runtime.execute(
        "batch part in $inputs size 1 do { "
        'file open $part.inputs[0] into $opened; import "library.ctk"; '
        "print $part.index; }"
    )

    assert runtime.bindings["part"] == "outer binding"
    assert "opened" not in runtime.bindings
    assert "captured" not in runtime.bindings
    assert "selected" not in runtime.bindings
    assert client.opened[0][1]["scope"] is client.scopes[0]
    assert client.scopes[0].released


def test_batch_rejects_live_resource_escape_through_collection_mutation(tmp_path: Path):
    runtime, client = _runtime(tmp_path)
    runtime.bindings["inputs"] = FileSet(
        (InputDescriptor.from_path("one.cc", working_directory=tmp_path),)
    )
    outer = []
    runtime.bindings["outer"] = outer

    result = dispatch_result(
        client,
        "batch part in $inputs size 1 do { "
        "file open $part.inputs[0] into $opened; push $outer, $opened; }",
        runtime,
    )

    assert outer == []
    assert not result.success
    assert '"failed_groups":1' in result.output
    assert '"completed_files":1' in result.output
    assert client.scopes[0].cancelled and client.scopes[0].released


def test_batch_rejects_exporting_a_matcher_closure_that_can_capture_group_values(
    tmp_path: Path,
):
    runtime, client = _runtime(tmp_path)
    runtime.bindings["inputs"] = FileSet(
        (InputDescriptor.from_path("one.cc", working_directory=tmp_path),)
    )
    outer: list[object] = []
    runtime.bindings["outer"] = outer

    result = dispatch_result(
        client,
        "batch part in $inputs size 1 do { "
        "let selected() = functionDecl(); push $outer, $selected; }",
        runtime,
    )

    assert not result.success
    assert outer == []
    assert '"failed_groups":1' in result.output


def test_batch_rejects_exporting_a_matcher_with_nested_live_arguments(
    tmp_path: Path,
):
    runtime, client = _runtime(tmp_path)
    runtime.bindings["inputs"] = FileSet(
        (InputDescriptor.from_path("one.cc", working_directory=tmp_path),)
    )
    outer: list[object] = []
    runtime.bindings["outer"] = outer

    result = dispatch_result(
        client,
        "batch part in $inputs size 1 do { "
        "file open $part.inputs[0] into $opened; "
        "let wrapped = hasName($opened); push $outer, $wrapped; }",
        runtime,
    )

    assert not result.success
    assert outer == []
    assert '"failed_groups":1' in result.output


def test_batch_output_cap_fails_group_without_marking_it_complete(tmp_path: Path):
    runtime, client = _runtime(tmp_path)
    runtime.bindings["inputs"] = FileSet(
        (InputDescriptor.from_path("one.cc", working_directory=tmp_path),)
    )
    runtime.bindings["large"] = "x" * 1_000_001

    result = dispatch_result(
        client,
        "batch part in $inputs size 1 do { print $large; }",
        runtime,
    )

    assert not result.success
    assert '"completed_groups":0' in result.output
    assert '"completed_files":0' in result.output
    assert '"failed_groups":1' in result.output
    assert client.scopes[0].released


def test_batch_cleanup_unknown_report_uses_fixed_sample(tmp_path: Path):
    runtime, client = _runtime(tmp_path)
    runtime.bindings["inputs"] = FileSet(
        tuple(InputDescriptor.from_path(f"{index}.cc") for index in range(24))
    )
    client.open_resource_scope = _unacknowledged_scope(client)

    result = dispatch_result(
        client,
        "batch part in $inputs size 1 on error continue do { print $missing; }",
        runtime,
    )
    assert not result.success
    assert '"cleanup_unknown_groups_total":1' in result.output
    assert '"cleanup_unknown_groups_sample":[1]' in result.output
    assert '"skipped_groups":23' in result.output
    assert len(client.scopes) == 1
    assert len(result.output) < 4_500


def test_batch_interrupt_emits_final_report_after_scope_cleanup(tmp_path: Path, capsys):
    runtime, client = _runtime(tmp_path)
    runtime.bindings["inputs"] = FileSet(
        (InputDescriptor.from_path("one.cc", working_directory=tmp_path),)
    )

    evaluate_statement = runtime._evaluate_statement_once

    def interrupt(node, source, *, value_context):
        if node.data == "print":
            raise KeyboardInterrupt
        return evaluate_statement(node, source, value_context=value_context)

    runtime._evaluate_statement_once = interrupt
    with pytest.raises(KeyboardInterrupt):
        runtime.execute("batch part in $inputs size 1 do { print $part.index; }")

    assert client.scopes[0].cancelled and client.scopes[0].released
    lines = capsys.readouterr().out.splitlines()
    report = next(line for line in lines if line.startswith('{"accepted_inputs"'))
    assert '"cancelled_groups":1' in report
    assert '"cleanup_acknowledged":true' in report


def test_interrupt_preserves_terminal_failure_beside_in_flight_cancellation(
    tmp_path: Path, capsys
):
    runtime, client = _runtime(tmp_path)
    runtime.bindings["inputs"] = FileSet(
        (InputDescriptor.from_path("one.cc", working_directory=tmp_path),)
    )
    evaluate_statement = runtime._evaluate_statement_once

    def fail_one_and_interrupt(node, source, *, value_context):
        result = evaluate_statement(node, source, value_context=value_context)
        if node.data == "print":
            runtime._batch_file_outcomes[("one.cc", "profile")] = "failed"
            runtime._batch_file_outcomes[("two.cc", "profile")] = "attempting"
            runtime.request_batch_cancel()
        return result

    runtime._evaluate_statement_once = fail_one_and_interrupt
    with pytest.raises(BatchInterrupted):
        runtime.execute("batch part in $inputs size 1 do { print $part.index; }")

    report = next(
        line for line in capsys.readouterr().out.splitlines()
        if line.startswith('{"accepted_inputs"')
    )
    assert '"failed_files":1' in report
    assert '"cancelled_files":1' in report
    assert client.scopes[0].cancelled and client.scopes[0].released


@pytest.mark.parametrize(
    ("error_type", "status", "message", "outcome"),
    [
        (CursorError, grpc.StatusCode.CANCELLED, "cancelled", "cancelled"),
        (CursorError, grpc.StatusCode.UNAVAILABLE, "unavailable", "unknown"),
        (CursorError, grpc.StatusCode.DEADLINE_EXCEEDED, "deadline", "unknown"),
        (CursorError, grpc.StatusCode.INVALID_ARGUMENT, "invalid", "failed"),
        (CursorError, grpc.StatusCode.RESOURCE_EXHAUSTED,
         "Received message larger than max (77 vs. 1)", "unknown"),
        (AnalysisError, grpc.StatusCode.CANCELLED, "cancelled", "cancelled"),
        (AnalysisError, grpc.StatusCode.UNAVAILABLE, "unavailable", "unknown"),
        (AnalysisError, grpc.StatusCode.DEADLINE_EXCEEDED, "deadline", "unknown"),
        (AnalysisError, grpc.StatusCode.INVALID_ARGUMENT, "invalid", "failed"),
        (AnalysisError, grpc.StatusCode.RESOURCE_EXHAUSTED,
         "Received message larger than max (77 vs. 1)", "unknown"),
    ],
)
def test_scoped_rpc_errors_have_truthful_terminal_file_outcomes(
    tmp_path: Path, error_type, status, message, outcome
):
    runtime, _client = _runtime(tmp_path)
    descriptor = InputDescriptor.from_path("one.cc", working_directory=tmp_path)
    runtime._active_resource_scope = object()
    runtime._active_batch_inputs = (descriptor,)

    def fail_operation():
        raise error_type(status, message)

    with pytest.raises(error_type):
        runtime._scoped_file_call(descriptor, fail_operation)

    assert runtime._batch_file_outcomes[
        (descriptor.path, descriptor.profile_id)
    ] == outcome


def test_lost_scope_admission_reply_is_unknown_and_stops_later_groups(
    tmp_path: Path,
):
    runtime, client = _runtime(tmp_path)
    runtime.bindings["inputs"] = FileSet(
        tuple(InputDescriptor.from_path(f"{index}.cc") for index in range(3))
    )

    class LostReply(Exception):
        code = type("Status", (), {"name": "UNAVAILABLE"})()

    def lost_reply(**_kwargs):
        raise LostReply("admission reply lost")

    client.open_resource_scope = lost_reply
    result = dispatch_result(
        client,
        "batch part in $inputs size 1 on error continue do { print $part.index; }",
        runtime,
    )

    assert not result.success
    assert '"cleanup_acknowledged":false' in result.output
    assert '"cleanup_unknown_groups_total":1' in result.output
    assert '"skipped_groups":2' in result.output
    assert '"unattempted_files":1' in result.output


def test_resource_exhausted_admission_is_known_rejection(tmp_path: Path):
    runtime, client = _runtime(tmp_path)
    runtime.bindings["inputs"] = FileSet(
        tuple(InputDescriptor.from_path(f"{index}.cc") for index in range(2))
    )

    class Rejected(Exception):
        code = type("Status", (), {"name": "RESOURCE_EXHAUSTED"})()

    client.open_resource_scope = lambda **_kwargs: (_ for _ in ()).throw(
        Rejected("resource scope count limit exceeded")
    )
    result = dispatch_result(
        client,
        "batch part in $inputs size 1 on error continue do { print $part.index; }",
        runtime,
    )

    assert not result.success
    assert '"cleanup_acknowledged":true' in result.output
    assert '"cleanup_unknown_groups_total":0' in result.output
    assert '"failed_groups":2' in result.output
    assert '"unattempted_files":2' in result.output


def test_prior_rejection_then_unacknowledged_cleanup_does_not_double_count_files(
    tmp_path: Path,
):
    runtime, client = _runtime(tmp_path)
    runtime.bindings["inputs"] = FileSet(
        tuple(InputDescriptor.from_path(f"{index}.cc") for index in range(3))
    )
    open_scope = client.open_resource_scope
    calls = 0

    class Rejected(Exception):
        code = type("Status", (), {"name": "RESOURCE_EXHAUSTED"})()

    def reject_then_unacknowledged(*, inputs, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise Rejected("resource scope count limit exceeded")
        scope = open_scope(inputs=inputs, **kwargs)
        scope.info.cleanup_acknowledged = False
        return scope

    client.open_resource_scope = reject_then_unacknowledged
    result = dispatch_result(
        client,
        "batch part in $inputs size 1 on error continue do { print $missing; }",
        runtime,
    )

    assert not result.success
    assert calls == 2
    assert '"failed_groups":2' in result.output
    assert '"skipped_groups":1' in result.output
    assert '"skipped_files":1' in result.output
    assert '"unattempted_files":2' in result.output


def test_cancel_after_group_release_skips_current_next_group_and_all_its_files(
    tmp_path: Path, capsys
):
    runtime, client = _runtime(tmp_path)
    runtime.bindings["inputs"] = FileSet(
        tuple(InputDescriptor.from_path(f"{index}.cc") for index in range(3))
    )
    open_scope = client.open_resource_scope

    def cancel_after_first_release(*, inputs, **kwargs):
        scope = open_scope(inputs=inputs, **kwargs)
        release = scope.release

        def release_and_cancel():
            result = release()
            if len(client.scopes) == 1:
                runtime.request_batch_cancel()
            return result

        scope.release = release_and_cancel
        return scope

    client.open_resource_scope = cancel_after_first_release
    with pytest.raises(BatchInterrupted):
        runtime.execute(
            "batch part in $inputs size 1 do { print $part.index; }"
        )

    report = next(
        line for line in capsys.readouterr().out.splitlines()
        if line.startswith('{"accepted_inputs"')
    )
    assert '"completed_groups":1' in report
    assert '"skipped_groups":2' in report
    assert '"unattempted_files":1' in report
    assert '"skipped_files":2' in report


def test_receive_limit_scope_admission_reply_is_unknown_and_stops(
    tmp_path: Path,
):
    runtime, client = _runtime(tmp_path)
    runtime.bindings["inputs"] = FileSet(
        tuple(InputDescriptor.from_path(f"{index}.cc") for index in range(3))
    )

    class OversizedReply(Exception):
        code = type("Status", (), {"name": "RESOURCE_EXHAUSTED"})()

    client.open_resource_scope = lambda **_kwargs: (_ for _ in ()).throw(
        OversizedReply(
            "Stream removed (CLIENT: Received message larger than max (77 vs. 1))"
        )
    )
    result = dispatch_result(
        client,
        "batch part in $inputs size 1 on error continue do { print $part.index; }",
        runtime,
    )

    assert not result.success
    assert '"cleanup_acknowledged":false' in result.output
    assert '"cleanup_unknown_groups_total":1' in result.output
    assert '"skipped_groups":2' in result.output


def test_cleanup_unknown_group_is_counted_once_when_release_and_describe_fail(
    tmp_path: Path,
):
    runtime, client = _runtime(tmp_path)
    runtime.bindings["inputs"] = FileSet(
        (InputDescriptor.from_path("one.cc", working_directory=tmp_path),)
    )
    open_scope = client.open_resource_scope

    def broken_scope(**kwargs):
        scope = open_scope(**kwargs)
        scope.release = lambda: (_ for _ in ()).throw(RuntimeError("release lost"))
        scope.describe = lambda: (_ for _ in ()).throw(RuntimeError("describe lost"))
        return scope

    client.open_resource_scope = broken_scope
    result = dispatch_result(
        client,
        "batch part in $inputs size 1 do { print $part.index; }",
        runtime,
    )

    assert not result.success
    assert '"cleanup_unknown_groups_total":1' in result.output


def test_foreground_runner_handles_first_sigint_in_worker_and_joins(tmp_path):
    started = threading.Event()
    unwound = threading.Event()
    runner_thread: list[int] = []
    runtime, _client = _runtime(tmp_path)

    def runner():
        runner_thread.append(threading.get_ident())
        started.set()
        try:
            while not runtime._batch_cancel_requested.wait(0.01):
                time.sleep(0.01)
            raise BatchInterrupted("test interrupt")
        finally:
            unwound.set()

    def send_interrupt():
        assert started.wait(timeout=2)
        os.kill(os.getpid(), signal.SIGINT)

    timer = threading.Thread(target=send_interrupt)
    timer.start()
    try:
        result, interrupted = asyncio.run(_run_batch_with_interrupts(runtime, runner))
    finally:
        timer.join(timeout=2)

    assert started.is_set()
    assert unwound.is_set()
    assert runner_thread and runner_thread[0] != threading.main_thread().ident
    assert result is None
    assert interrupted


def test_batch_async_cancellation_runs_session_hook_before_join(tmp_path):
    runtime, _client = _runtime(tmp_path)
    waiting = threading.Event()
    unblocked = threading.Event()

    def runner():
        waiting.set()
        if not unblocked.wait(timeout=3):
            raise AssertionError("runner remained blocked on session completion")
        raise BatchInterrupted("test interrupt")

    async def cancel_session():
        unblocked.set()

    async def exercise():
        current = asyncio.current_task()
        assert current is not None
        asyncio.get_running_loop().call_later(0.1, current.cancel)
        return await _run_batch_with_interrupts(
            runtime, runner, on_interrupt=cancel_session
        )

    result, interrupted = asyncio.run(exercise())

    assert waiting.is_set()
    assert unblocked.is_set()
    assert result is None and interrupted


def test_external_batch_cancel_releases_scope_and_skips_later_groups(
    tmp_path: Path, capsys
):
    runtime, client = _runtime(tmp_path)
    runtime.bindings["inputs"] = FileSet(
        tuple(
            InputDescriptor.from_path(f"{index}.cc", working_directory=tmp_path)
            for index in range(3)
        )
    )
    evaluate_statement = runtime._evaluate_statement_once
    first = True

    def request_cancel(node, source, *, value_context):
        nonlocal first
        result = evaluate_statement(node, source, value_context=value_context)
        if first and node.data == "print":
            first = False
            runtime.request_batch_cancel()
        return result

    runtime._evaluate_statement_once = request_cancel
    with pytest.raises(BatchInterrupted):
        runtime.execute(
            "batch part in $inputs size 1 do { print $part.index; print $part.index; }"
        )

    assert len(client.scopes) == 1
    assert client.scopes[0].cancelled and client.scopes[0].released
    output = capsys.readouterr().out
    assert '"cancelled_groups":1' in output
    assert '"skipped_groups":2' in output


def _unacknowledged_scope(client):
    original = client.open_resource_scope

    def open_scope(*, inputs, **kwargs):
        scope = original(inputs=inputs, **kwargs)
        scope.info.cleanup_acknowledged = False
        return scope

    return open_scope


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("batch part in $inputs size 0 do { print $part.index; }", "positive integer"),
        ("batch part in $inputs count 5 do { print $part.index; }", "cannot exceed"),
        (
            'batch part in $inputs size 2 memory "0MiB" do { print $part.index; }',
            "positive value",
        ),
    ],
)
def test_batch_options_validate_before_scope_open(
    tmp_path: Path, source: str, message: str
):
    runtime, client = _runtime(tmp_path)
    runtime.bindings["inputs"] = FileSet((InputDescriptor.from_path("a.cc"),))
    with pytest.raises(EvaluationError, match=message):
        runtime.execute(source)
    assert client.scopes == []


def test_batch_rejects_yielding_analysis_before_scope_admission(tmp_path: Path):
    runtime, client = _runtime(tmp_path)
    runtime.bindings["inputs"] = FileSet(
        (InputDescriptor.from_path("a.cc", working_directory=tmp_path),)
    )

    with pytest.raises(EvaluationError, match="yielding analysis blocks"):
        runtime.execute(
            "batch part in $inputs size 1 do { "
            "print in $part.inputs[0] { yield $part.index; }; }"
        )

    assert client.scopes == []
