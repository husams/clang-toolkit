"""Collected batch values remain bounded, quiet, and useful after cleanup."""

from __future__ import annotations

import json

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
        'let report = batch part in $inputs size 2 do { '
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


def test_assigned_failure_is_inspectable_while_standalone_failure_remains_an_error(batch_runtime, capsys):
    runtime, client = batch_runtime
    runtime.bindings["answers"] = {"1": "first"}
    source = 'batch part in $inputs size 1 do { $answers["${part.index}"]; }'
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
    runtime.execute("let report = batch part in $inputs size 1 on error continue do { $part.index; }")
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
