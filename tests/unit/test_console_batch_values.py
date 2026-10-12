"""Collected batch values remain bounded, quiet, and useful after cleanup."""

from __future__ import annotations

import json
import threading

import pytest

from clang_toolkit.cli.runtime import EvaluationError
from clang_toolkit.cli.runtime.batch_execution import BatchInterrupted
from clang_toolkit.cli.runtime.persistence import load
from clang_toolkit.cli.runtime.values import MatchSet
from clang_toolkit.resources import FileSet, InputDescriptor
from test_console_file_batch_runtime import _runtime
from test_file_output import _semantic_collection


@pytest.fixture
def batch_runtime(tmp_path):
    runtime, client = _runtime(tmp_path)
    runtime.bindings["inputs"] = FileSet(tuple(
        InputDescriptor.from_path(f"{index}.cc", working_directory=tmp_path)
        for index in range(3)
    ))
    yield runtime, client
    runtime.close()


def test_assigned_batch_collects_final_group_values_with_indices_and_no_output(batch_runtime, capsys, tmp_path):
    runtime, client = batch_runtime
    runtime.execute('set output to "display.txt"')
    assert runtime.execute(
        'let report = batch part in $inputs size 2 progress off do { '
        'print $part.index; let ignored = 99; {group: $part.index, length: $part.length}; }'
    ) == ""
    report = runtime.bindings["report"]
    assert report["status"] == "completed"
    assert report["results"] == [{"group": 1, "length": 2}, {"group": 2, "length": 1}]
    assert report["result_group_indices"] == [1, 2]
    assert report["results_complete"] is True
    assert report["cleanup_acknowledged"] is True
    assert all(scope.released for scope in client.scopes)
    assert "part" not in runtime.bindings and "ignored" not in runtime.bindings
    assert capsys.readouterr().out == ""
    assert (tmp_path / "display.txt").read_text() == ""


def test_standalone_batch_keeps_default_progress_and_off_preserves_body_display(batch_runtime, capsys):
    runtime, _ = batch_runtime
    report = json.loads(runtime.execute("batch part in $inputs size 2 do { $part.index; }"))
    assert report["completed_groups"] == 2
    assert "started" in capsys.readouterr().out
    report = json.loads(runtime.execute("batch part in $inputs size 2 progress off do { print $part.index; }"))
    output = capsys.readouterr().out
    assert "started" not in output and "completed" not in output
    assert output.splitlines() == ["1", "2"]
    assert report["cleanup_acknowledged"]


@pytest.mark.parametrize("progress", ["", "progress on"])
def test_assigned_batch_prints_heartbeat_before_body_returns(batch_runtime, monkeypatch, capsys, progress):
    from clang_toolkit.cli.runtime import batch_execution

    runtime, _ = batch_runtime
    monkeypatch.setattr(batch_execution, "_PROGRESS_INTERVAL_SECONDS", 0.01)
    arrived = threading.Event()
    original_emit = batch_execution._emit

    def emit(runtime, text):
        original_emit(runtime, text)
        if " running:" in text:
            arrived.set()

    monkeypatch.setattr(batch_execution, "_emit", emit)
    original = runtime._evaluate_statement_once

    def blocked_body(statement, source, *, value_context):
        if str(statement.data) == "display":
            assert arrived.wait(2), "no feedback while the assigned body was blocked"
        return original(statement, source, value_context=value_context)

    monkeypatch.setattr(runtime, "_evaluate_statement_once", blocked_body)
    runtime.execute(f"let report = batch part in $inputs size 3 {progress} do {{ $part.index; }}")
    output = capsys.readouterr().out
    assert "running: 0/3 completed" in output
    assert "group 1 completed" in output
    assert runtime.bindings["report"]["results"] == [1]
    assert not any(thread.name == "ctk-batch-progress" for thread in threading.enumerate())


def test_parallel_failure_cancels_scope_before_joining_a_blocked_earlier_file(batch_runtime, monkeypatch):
    runtime, client = batch_runtime
    blocked = threading.Event()
    cancelled = threading.Event()
    scope = client.open_resource_scope(inputs=runtime.bindings["inputs"].inputs)
    scope.cancel = lambda: cancelled.set()
    runtime._active_resource_scope = scope
    runtime._batch_jobs = 2

    def match(text, target, options, on_row):
        if target == "slow":
            blocked.set()
            assert cancelled.wait(2), "scope cancellation happened after joining the pool"
            raise EvaluationError("cancelled sibling")
        assert blocked.wait(2)
        raise EvaluationError("memory limit")

    monkeypatch.setattr(runtime, "_match_target", match)
    try:
        with pytest.raises(EvaluationError, match="memory limit"):
            runtime._match_files("decl()", ["slow", "failed"])
        assert cancelled.is_set()
    finally:
        runtime._active_resource_scope = None


@pytest.mark.parametrize("phase", ["admitting", "cleaning up"])
def test_progress_stays_live_during_admission_and_cleanup_and_ignores_file_sink(batch_runtime, monkeypatch, capsys, tmp_path, phase):
    from clang_toolkit.cli.runtime import batch_execution

    runtime, client = batch_runtime
    runtime.execute('set output to "values.txt"')
    monkeypatch.setattr(batch_execution, "_PROGRESS_INTERVAL_SECONDS", 0.01)
    arrived = threading.Event()
    original_emit = batch_execution._emit

    def emit(runtime, text):
        original_emit(runtime, text)
        if f"({phase})" in text:
            arrived.set()

    monkeypatch.setattr(batch_execution, "_emit", emit)
    original_open = client.open_resource_scope

    def open_scope(**kwargs):
        if phase == "admitting":
            assert arrived.wait(2)
        scope = original_open(**kwargs)
        original_release = scope.release

        def release():
            assert arrived.wait(2)
            return original_release()

        if phase == "cleaning up":
            scope.release = release
        return scope

    monkeypatch.setattr(client, "open_resource_scope", open_scope)
    runtime.execute("let report = batch part in $inputs size 3 do { $part.index; }")
    assert f"({phase})" in capsys.readouterr().out
    assert (tmp_path / "values.txt").read_text() == ""
    assert runtime.bindings["report"]["cleanup_acknowledged"]


def test_interactive_assigned_batch_recovers_from_sigint_and_runs_next_batch(batch_runtime, monkeypatch):
    import asyncio
    import os
    import signal
    from types import SimpleNamespace
    from clang_toolkit.cli.app import _run_interactive_command

    runtime, client = batch_runtime
    started = threading.Event()
    original = runtime._evaluate_statement_once

    def blocked(statement, source, *, value_context):
        if str(statement.data) == "display" and not started.is_set():
            started.set()
            assert runtime._batch_cancel_requested.wait(2)
        return original(statement, source, value_context=value_context)

    monkeypatch.setattr(runtime, "_evaluate_statement_once", blocked)

    async def cancel_scope(scope_id):
        scope = next(scope for scope in client.scopes if scope.resource_scope_id == scope_id)
        scope.cancel()

    # The test scope implements the same stable identity used by async control.
    open_scope = client.open_resource_scope

    def identified_scope(**kwargs):
        scope = open_scope(**kwargs)
        scope.resource_scope_id = str(len(client.scopes))
        return scope

    monkeypatch.setattr(client, "open_resource_scope", identified_scope)

    def interrupt():
        assert started.wait(2)
        os.kill(os.getpid(), signal.SIGINT)

    async def run():
        control = SimpleNamespace(cancel_resource_scope=cancel_scope)
        outcome = await _run_interactive_command(client, "let report = batch part in $inputs size 3 do { $part.index; }", runtime, control)
        assert not outcome.success and "interrupted" in outcome.output
        assert client.scopes[0].released
        assert "report" not in runtime.bindings
        outcome = await _run_interactive_command(client, "let report = batch part in $inputs size 3 do { $part.index; }", runtime, control)
        assert outcome.success
        assert runtime.bindings["report"]["status"] == "completed"

    timer = threading.Thread(target=interrupt)
    timer.start()
    try:
        asyncio.run(run())
    finally:
        timer.join(2)


def test_assigned_failure_is_inspectable_while_standalone_failure_remains_an_error(batch_runtime, capsys):
    runtime, client = batch_runtime
    runtime.bindings["answers"] = {"1": "first"}
    source = 'batch part in $inputs size 1 progress off do { $answers["${part.index}"]; }'
    assert runtime.execute("let report = " + source) == ""
    report = runtime.bindings["report"]
    assert report["status"] == "failed"
    assert report["results"] == ["first"]
    assert report["result_group_indices"] == [1]
    assert report["completed_groups"] == 1
    assert report["failed_groups"] == 1 and report["skipped_groups"] == 1
    assert report["group_errors_total"] == 1
    assert report["group_errors_sample"][0]["group_index"] == 2
    assert "key" in report["group_errors_sample"][0]["message"]
    assert report["cleanup_acknowledged"]
    assert all(scope.released for scope in client.scopes)
    assert capsys.readouterr().out == ""
    with pytest.raises(EvaluationError, match="batch failed"):
        runtime.execute(source)


def test_continue_keeps_only_successful_group_values_and_their_original_indices(batch_runtime):
    runtime, client = batch_runtime
    runtime.bindings["answers"] = {"1": "first", "3": "third"}
    runtime.execute('let report = batch part in $inputs size 1 on error continue do { $answers["${part.index}"]; }')
    report = runtime.bindings["report"]
    assert report["status"] == "failed"
    assert report["results"] == ["first", "third"]
    assert report["result_group_indices"] == [1, 3]
    assert report["completed_groups"] == 2 and report["failed_groups"] == 1
    assert report["skipped_groups"] == 0
    assert all(scope.released for scope in client.scopes)


def test_empty_body_has_an_explicit_value_for_each_successful_group(batch_runtime):
    runtime, _ = batch_runtime
    runtime.execute("let report = batch part in $inputs size 2 do {}")
    assert runtime.bindings["report"]["results"] == [None, None]
    assert runtime.bindings["report"]["result_group_indices"] == [1, 2]


@pytest.mark.parametrize("oversized", ["x" * 1_048_577, list(range(10_001))], ids=["bytes", "items"])
def test_collection_limit_failure_retains_prior_group_and_acknowledges_cleanup(batch_runtime, oversized):
    runtime, client = batch_runtime
    runtime.bindings["answers"] = {"1": "first", "2": oversized}
    runtime.execute('let report = batch part in $inputs size 1 do { $answers["${part.index}"]; }')
    report = runtime.bindings["report"]
    assert report["status"] == "failed"
    assert report["results_complete"] is False
    assert report["results"] == ["first"]
    assert report["result_group_indices"] == [1]
    assert report["failed_groups"] == 1
    assert report["cleanup_acknowledged"]
    assert all(scope.released for scope in client.scopes)


def test_nested_native_rows_are_detached_and_can_be_saved_after_owner_closes(batch_runtime, tmp_path):
    runtime, _ = batch_runtime
    live, owner = _semantic_collection()
    runtime.bindings["live"] = live
    runtime.execute("let report = batch part in $inputs size 3 do { {nested: [$live]}; }")
    owner.close()
    detached = runtime.bindings["report"]["results"][0]["nested"][0]
    assert isinstance(detached, MatchSet)
    assert len(detached.rows) == 1
    assert runtime.execute("$report.results[0].nested[0][0].source_match_index") == "23"
    runtime.execute('save $report.results to "detached.proto" as proto')
    restored = load(tmp_path / "detached.proto")
    assert len(restored[0]["nested"][0].rows) == 1


@pytest.mark.parametrize("interruption", [BatchInterrupted, KeyboardInterrupt])
def test_interruption_attaches_partial_report_after_cleanup_and_preserves_assignment(batch_runtime, monkeypatch, interruption):
    runtime, client = batch_runtime
    runtime.bindings["report"] = "previous value"
    original = runtime._evaluate_statement_once

    def interrupt_second_group(statement, source, *, value_context):
        if str(statement.data) == "display" and len(client.scopes) == 2:
            raise interruption("interrupted during second group")
        return original(statement, source, value_context=value_context)

    monkeypatch.setattr(runtime, "_evaluate_statement_once", interrupt_second_group)
    with pytest.raises(interruption) as captured:
        runtime.execute("let report = batch part in $inputs size 1 do { $part.index; }")
    report = captured.value.report
    assert report["status"] == "cancelled"
    assert report["results"] == [1]
    assert report["result_group_indices"] == [1]
    assert report["completed_groups"] == 1 and report["cancelled_groups"] == 1
    assert report["skipped_groups"] == 1
    assert report["results_complete"] is False
    assert report["cleanup_acknowledged"]
    assert runtime.bindings["report"] == "previous value"
    assert all(scope.released for scope in client.scopes)
    assert client.scopes[-1].cancelled


def test_quiet_failure_diagnostics_are_useful_and_bounded(batch_runtime, monkeypatch, capsys, tmp_path):
    runtime, client = batch_runtime
    runtime.bindings["inputs"] = FileSet(tuple(
        InputDescriptor.from_path(f"failure-{index}.cc", working_directory=tmp_path)
        for index in range(5)
    ))
    original = runtime._evaluate_statement_once

    def fail_body(statement, source, *, value_context):
        if str(statement.data) == "display":
            raise EvaluationError("intentional failure: " + "x" * 1000)
        return original(statement, source, value_context=value_context)

    monkeypatch.setattr(runtime, "_evaluate_statement_once", fail_body)
    runtime.execute("let report = batch part in $inputs size 1 on error continue progress off do { $part.index; }")
    report = runtime.bindings["report"]
    assert report["status"] == "failed"
    assert report["group_errors_total"] == 5
    assert len(report["group_errors_sample"]) == 4
    assert [error["group_index"] for error in report["group_errors_sample"]] == [1, 2, 3, 4]
    assert all(error["message"].startswith("intentional failure:") for error in report["group_errors_sample"])
    assert all(len(error["message"]) <= 300 for error in report["group_errors_sample"])
    assert report["results"] == [] and report["results_complete"] is False
    assert all(scope.released for scope in client.scopes)
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("body", [
    'cursor open "a.cc" functionDecl();',
    'cursor continue "cursor" "f" returnStmt();',
    'cursor restart "cursor" functionDecl();',
    'background functionDecl();',
    'session start "legacy";',
    'session add "a.cc";',
    'session match;',
    'session resume;',
    'let nested = [cursor open "a.cc" functionDecl()];',
    'let nested = {unsafe: background functionDecl()};',
    'foreach x in [1] do { cursor open "a.cc" functionDecl(); };',
])
def test_unscoped_resource_operations_are_rejected_before_any_batch_admission(batch_runtime, body):
    runtime, client = batch_runtime
    with pytest.raises(EvaluationError, match="scope|scoped"):
        runtime.execute("let report = batch part in $inputs size 1 do { " + body + " }")
    assert client.scopes == []
    assert client.matches == []
    assert "report" not in runtime.bindings
