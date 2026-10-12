"""Session-level acceptance for scripts executed from either console UI."""

import asyncio
from unittest.mock import Mock

import pytest

from clang_toolkit.cli.app import dispatch_result
from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
from clang_toolkit.client import Client


@pytest.fixture(params=["tree", "compiled"])
def runtime(request, tmp_path):
    instance = PrototypeRuntime(Client(), script_engine=request.param, cwd=tmp_path, environment={})
    yield instance
    instance.close()
    instance.client.close()


def submit(runtime, source):
    return dispatch_result(runtime.client, source, runtime)


def test_variables_persist_and_branch_locals_do_not_escape(runtime):
    assert submit(runtime, "let total = 0").output == ""
    result = submit(runtime, "foreach item in [2,4,6] do { if $item > 2 do $total += $item; let local = $item }")
    assert result.success
    assert runtime.bindings["total"] == 10
    assert "item" not in runtime.bindings and "local" not in runtime.bindings
    assert submit(runtime, "print $total").output == "10"
    assert submit(runtime, "let label = unless $total > 20 do \"small\" else \"large\"").success
    assert submit(runtime, "$label").output == "small"


def test_multiline_groups_and_ternary_in_dictionary(runtime):
    outcome = submit(runtime, 'let n = (\n 2 +\n 3 * 4\n)\nlet report = {count: $n, label: $n > 10 ? "large" : "small"}\nprint $report')
    assert outcome.success
    assert runtime.bindings["report"] == {"count": 14, "label": "large"}
    assert '"count": 14' in outcome.output


def test_prints_before_failure_survive_and_failed_target_is_atomic(runtime):
    result = submit(runtime, 'let total = 7; print "before"; $total /= 0; print "after"')
    assert not result.success
    assert result.output.startswith("before\nerror:")
    assert "after" not in result.output
    assert runtime.bindings["total"] == 7
    assert runtime._scopes == []
    assert submit(runtime, "$total += 1; $total").output == "8"


def test_entire_submission_is_validated_before_effects(runtime):
    result = submit(runtime, 'let total = 7; print "before"; let broken =')
    assert not result.success
    assert "total" not in runtime.bindings
    assert "before\n" not in result.output


def test_host_adapter_sees_loop_locals_once(runtime):
    result = submit(runtime, 'let values = foreach item in [2,4] do ctk("print $item"); $values')
    assert result.success, result.output
    assert runtime.bindings["values"] == [2, 4]
    assert "item" not in runtime.bindings
    assert runtime._scopes == []


def test_native_commands_and_compiled_expressions_share_bindings(runtime):
    result = submit(runtime, 'let paths = glob("*.cc"); let count = $paths.length + 2; bindings')
    assert result.success, result.output
    assert runtime.bindings["count"] == 2
    assert "count" in result.output


def test_output_sink_is_preserved(runtime, tmp_path):
    outcome = submit(runtime, 'set output to "values.txt"; let total = 2 + 3; print $total')
    assert outcome.success, outcome.output
    assert (tmp_path / "values.txt").read_text().strip().endswith("5")
    assert submit(runtime, "print 7").output == ""
    assert (tmp_path / "values.txt").read_text().strip().endswith("7")


def test_workspace_print_snapshots_and_no_duplicate_branch_output(runtime):
    runtime.capture_display = True
    outcome = submit(runtime, 'let report={count: 1}; print $report; $report.count=2; if true do print 3')
    assert outcome.success, outcome.output
    assert len(outcome.parts) == 2
    assert outcome.parts[0].outline_value[1] == {"count": 1}
    assert outcome.parts[1].output == "3"
    assert runtime.bindings["report"] == {"count": 2}


def test_history_records_whole_submission_once(runtime):
    runtime.history = Mock()
    source = "let n=2; print $n+3"
    assert submit(runtime, source).success
    runtime.history.append.assert_called_once_with(source, runtime.session_id, runtime.label)


def test_lazy_host_call_and_cancellation_recovery(runtime):
    runtime.client.server_status = Mock(side_effect=AssertionError("should be lazy"))
    assert submit(runtime, 'let safe = false and ctk("server status"); print $safe').output == "false"
    runtime.client.server_status.assert_not_called()
    runtime.request_batch_cancel()
    assert not submit(runtime, "foreach item in range(1000) do $item + 1").success
    assert runtime._scopes == []
    runtime.clear_batch_cancel()
    assert submit(runtime, "2 + 3").output == "5"


def test_help_and_exit_keep_console_control_semantics(runtime):
    assert "match" in submit(runtime, "help").output
    result = submit(runtime, 'print "before"; quit; print "after"')
    assert result.success
    assert result.exit_requested
    assert result.output == "before"


def test_compiled_submissions_are_cached_and_do_not_walk_the_tree(tmp_path, monkeypatch):
    from clang_toolkit.cli.runtime.prototype import semantics

    def unexpected(*args, **kwargs):
        raise AssertionError("compiled execution must not walk script nodes")
    for name in ("eval_expr", "eval_statement", "eval_block", "eval_foreach", "eval_program"):
        monkeypatch.setattr(semantics, name, unexpected)
    runtime = PrototypeRuntime(Client(), cwd=tmp_path, environment={})
    try:
        source = "let total=0; let values=foreach item in range(3) do $total += $item; $total"
        assert submit(runtime, source).output == "3"
        executable = runtime._prototype_session.cache[source][1]
        assert submit(runtime, source).output == "3"
        assert runtime._prototype_session.cache[source][1] is executable
        for number in range(70):
            assert submit(runtime, str(number)).success
        assert len(runtime._prototype_session.cache) == 64
        assert source not in runtime._prototype_session.cache
    finally:
        runtime.close()
        runtime.client.close()


def test_assigned_loop_is_silent_and_bare_condition_returns_last_value(runtime, tmp_path):
    assert submit(runtime, 'set output to "silent.txt"').success
    result = submit(runtime, 'let values = foreach item in [1,2] do { print $item; {item: $item} }')
    assert result.success, result.output
    assert (tmp_path / "silent.txt").read_text() == ""
    assert runtime.bindings["values"] == [{"item": 1}, {"item": 2}]
    assert submit(runtime, "clear output").success
    result = submit(runtime, "if true do { print 2; 3 }")
    assert result.success, result.output
    assert result.output == "2\n3"


def test_native_and_implicit_outputs_share_the_output_budget(runtime):
    result = submit(runtime, "foreach item in range(6000) do { inspect $item; inspect $item }")
    assert not result.success
    assert "output exceeds item limit" in result.output
    assert len(result.parts) == 10001  # 10000 outputs followed by one diagnostic.
    assert submit(runtime, "print 7").output == "7"


def test_interrupted_script_keeps_output_and_can_run_again(runtime):
    from clang_toolkit._generated.match.v1 import match_service_pb2
    from clang_toolkit.cli.app import _run_interactive_command

    def interrupt_after_status():
        runtime.request_batch_cancel()
        return match_service_pb2.ServerStatusResponse()

    runtime.client.server_status = Mock(side_effect=interrupt_after_status)
    result = asyncio.run(_run_interactive_command(
        runtime.client, 'print "before"; server status; print "after"', runtime, None,
    ))
    assert not result.success
    assert result.output.startswith("before\n")
    assert "Server status" in result.output
    assert "after" not in result.output
    assert len(result.parts) == 3
    runtime.client.server_status.assert_called_once()
    assert runtime._scopes == []
    assert asyncio.run(_run_interactive_command(
        runtime.client, "print 7", runtime, None,
    )).output == "7"
