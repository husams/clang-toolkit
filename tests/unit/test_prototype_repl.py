"""Session-level acceptance for scripts executed from either console UI."""

import asyncio
import json
from unittest.mock import Mock

import pytest

from clang_toolkit.cli.app import dispatch_result
from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
from clang_toolkit.cli.runtime.values import matcher_text
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


def test_list_selection_uses_shared_rules_in_the_real_console_adapter(runtime):
    assert submit(runtime, "let xs = [10, 20, 30, 40, 50]").success
    for expression, expected in (
        ("xs[-1]", "50"), ("xs[1:4]", "[20, 30, 40]"),
        ("xs[::-1]", "[50, 40, 30, 20, 10]"),
        ("xs | last(2)", "[40, 50]"), ("xs | last(0)", "[]"),
        ("[] | first", "null"), ("[] | last", "null"),
    ):
        result = submit(runtime, f"print {expression} | json")
        assert result.success, result.output
        assert json.loads(result.output) == json.loads(expected)
    # Method arguments still use native command trees rather than value IR.
    assert submit(runtime, "let records = [{a: 1}, {a: 2}]").success
    result = submit(runtime, 'print records[-1].get("a")')
    assert result.success, result.output
    assert result.output == "2"


def test_multiline_groups_and_ternary_in_dictionary(runtime):
    outcome = submit(runtime, 'let n = (\n 2 +\n 3 * 4\n)\nlet report = {count: $n, label: $n > 10 ? "large" : "small"}\nprint $report')
    assert outcome.success
    assert runtime.bindings["report"] == {"count": 14, "label": "large"}
    assert '"count": 14' in outcome.output


@pytest.mark.parametrize("newline", ["\n", "\r\n"])
def test_multiline_matcher_assignment_preserves_statement_boundaries(runtime, newline):
    source = newline.join([
        "let class = recordDecl(",
        "    isExpansionInMainFile(),",
        "    unless(isImplicit())",
        ")",
        'print "MATCHER_READY"',
    ])
    outcome = submit(runtime, source)
    assert outcome.success, outcome.output
    assert matcher_text(runtime.bindings["class"]) == (
        "recordDecl(isExpansionInMainFile(), unless(isImplicit()))"
    )
    assert outcome.output == "MATCHER_READY"


def test_multiline_matcher_definition_nested_arguments_and_binding(runtime):
    outcome = submit(runtime, '''let named(
    name
) = recordDecl(
    # Keep comments and blank lines inside the matcher.
    hasName(
        $name
    )

    , unless(
        isImplicit(
        )
    )
).bind(
    "record"
)
let selected = named(
    "Sample"
)
''')
    assert outcome.success, outcome.output
    assert matcher_text(runtime.bindings["selected"]) == (
        'recordDecl(hasName("Sample"), unless(isImplicit())).bind("record")'
    )


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


def test_then_conditional_syntax_persists_across_combined_repl_submissions(runtime):
    first = submit(runtime, "let x = 2")
    second = submit(runtime, "let y = if $x > 0 then $x * 10 else 1")
    assert first.success and second.success, second.output
    assert runtime.bindings["y"] == 20
    assert submit(runtime, "let x = 0").success
    false_branch = submit(runtime, "if $x > 0 then $x * 10 else 1")
    assert false_branch.success, false_branch.output
    assert false_branch.output == "1"


def test_then_conditional_supports_nested_else_if_and_multiline_block(runtime):
    result = submit(
        runtime,
        "let x = 2\n"
        "let value = if $x < 0 then 0\n"
        "else if $x > 0 then {\n"
        "  let local = $x * 10\n"
        "  $local\n"
        "} else 1\n"
        "$value",
    )
    assert result.success, result.output
    assert result.output == "20"
    assert runtime.bindings["value"] == 20
    assert "local" not in runtime.bindings


def test_mixed_then_do_dangling_else_and_explicit_block_in_combined_repl(runtime):
    inner_else = submit(
        runtime,
        "let selected = if false then if true do 1 else 2; print $selected",
    )
    assert inner_else.success, inner_else.output
    assert inner_else.output == "None"

    same_body_form = submit(
        runtime,
        "let selected = if false then if true then 1 else 2; print $selected",
    )
    assert same_body_form.success, same_body_form.output
    assert same_body_form.output == "None"

    inverse_order = submit(
        runtime,
        "let selected = if false do if true then 1 else 2; print $selected",
    )
    assert inverse_order.success, inverse_order.output
    assert inverse_order.output == "None"

    active_inner = submit(
        runtime,
        "let selected = if true then if false do 1 else 2; print $selected",
    )
    assert active_inner.success, active_inner.output
    assert active_inner.output == "2"

    explicit_empty_inner_else = submit(
        runtime,
        "let selected = if false then if true then 1 else {} else 2; print $selected",
    )
    assert explicit_empty_inner_else.success, explicit_empty_inner_else.output
    assert explicit_empty_inner_else.output == "2"

    grouped_inner = submit(
        runtime,
        "let selected = if false then (if true then 1) else 2; print $selected",
    )
    assert grouped_inner.success, grouped_inner.output
    assert grouped_inner.output == "2"

    explicit_outer_else = submit(runtime, "if false then { if true do 1 } else 2")
    assert explicit_outer_else.success, explicit_outer_else.output
    assert explicit_outer_else.output == "2"
