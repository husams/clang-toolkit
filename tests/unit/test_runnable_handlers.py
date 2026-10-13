from __future__ import annotations

import ast

import pytest

from clang_toolkit.cli.runtime.prototype.compiler import compile_program
from clang_toolkit.cli.runtime.prototype.semantics import (
    CancelledError, Context, EvaluationError, ExecutionLimitError,
)
from clang_toolkit.cli.runtime.prototype.syntax import parse
from clang_toolkit.cli.runtime.prototype.tree import evaluate


@pytest.fixture(params=["tree", "compiled"])
def execute(request):
    def run(source, context=None):
        context = context or Context()
        program = parse(source)
        value = evaluate(program, context) if request.param == "tree" else compile_program(program)(context)
        assert context.scopes == (context.bindings,)
        assert context.call_depth == context.cleanup_depth == 0
        return value, context
    return run


@pytest.mark.parametrize("fallback", ["0", "{ 0 }"])
@pytest.mark.parametrize("exit_action", ["clean()", "{ clean(); 99 }"])
def test_prefix_handlers_are_lazy_and_cleanup_preserves_result(execute, fallback, exit_action):
    seen = []
    context = Context(functions={"clean": lambda: seen.append("exit")})
    value, _ = execute(f"let divide(lhs, rhs = 1) = {{ on error {fallback}; on exit {exit_action}; lhs / rhs }}; [divide(10), divide(10, 0)]", context)
    assert value == [10, 0]
    assert seen == ["exit", "exit"]


def test_error_handler_and_cleanup_share_body_locals(execute):
    value, context = execute("let events = [0]; let f() = { on error { events[0] += local; 9 }; on exit { events[0] += local }; let local = 2; 1 / 0 }; [f(), events[0]]")
    assert value == [9, 4]
    assert "local" not in context.bindings


def test_cleanup_runs_for_unhandled_body_and_handler_errors(execute):
    events = []
    context = Context(functions={"clean": lambda: events.append("exit")})
    value, _ = execute("let fail() = { on error { 2 / 0 }; on exit clean(); 1 / 0 }; fail() on error 7", context)
    assert value == 7 and events == ["exit"]
    with pytest.raises(EvaluationError, match="zero"):
        execute("let fail() = { on exit clean(); 1 / 0 }; fail()", context)
    assert events == ["exit", "exit"]
    assert context.scopes == (context.bindings,)


def test_cleanup_error_escapes_to_call_fallback(execute):
    value, _ = execute("let f() = { on error 99; on exit { 1 / 0 }; 7 }; f() on error { 8 }")
    assert value == 8


def test_call_fallback_is_lazy_and_uses_only_escaping_errors(execute):
    context = Context(functions={"side": lambda: pytest.fail("fallback ran")})
    value, _ = execute("let f() = { on error 0; 1 / 0 }; [f() on error side(), 7 on error side()]", context)
    assert value == [0, 7]
    value, _ = execute("1 + 2 / 0 on error 9")
    assert value == 9


@pytest.mark.parametrize("action, expected, cleaned", [
    ("continue", [5, 2], [2, 0, 5]),
    ("break", [5], [2, 0]),
    ("{ continue }", [5, 2], [2, 0, 5]),
    ("{ break }", [5], [2, 0]),
])
def test_loop_error_control_runs_iteration_cleanup_first(execute, action, expected, cleaned):
    events = []
    context = Context(functions={"clean": lambda item: events.append(item)})
    value, _ = execute(f"foreach item in [2, 0, 5] do {{ on error {action}; on exit clean(item); 10 / item }}", context)
    assert value == expected and events == cleaned


def test_nested_loop_break_targets_nearest_loop(execute):
    value, _ = execute("foreach outer in [1, 2] do { foreach inner in [1, 0, 2] do { on error break; outer / inner } }")
    assert value == [[1], [2]]
    value, _ = execute("foreach item in [1, 0, 2] do { 10 / item on error continue }")
    assert value == [10, 5]


@pytest.mark.parametrize("source, message", [
    ("on error 0", "beginning"),
    ("let f() = { 7; on error 0 }", "beginning"),
    ("let f() = { on error 0; on error 1; 7 }", "once"),
    ("let f() = { on exit 0; on exit 1; 7 }", "once"),
    ("let f() = { on error break; 7 }", "enclosing foreach"),
    ("foreach item in [1] do { let f() = { continue }; f() }", "enclosing foreach"),
])
def test_invalid_handlers_and_control_fail_before_effects(execute, source, message):
    context = Context(functions={"side": lambda: pytest.fail("effect ran")})
    with pytest.raises(ValueError, match=message):
        execute(f"side(); {source}", context)


@pytest.mark.parametrize("error_type", [CancelledError, ExecutionLimitError])
def test_fatal_errors_are_not_recovered_but_cleanup_runs(execute, error_type):
    events = []
    def fail():
        raise error_type("stop")
    context = Context(functions={"fail": fail, "clean": lambda: events.append("exit")})
    with pytest.raises(error_type, match="stop"):
        execute("let f() = { on error 0; on exit clean(); fail() }; f() on error 9", context)
    assert events == ["exit"]
    assert context.scopes == (context.bindings,)
    assert context.call_depth == context.cleanup_depth == 0


def test_exhausted_budget_runs_cleanup_without_turning_failure_into_success(execute):
    events = []
    context = Context(max_steps=35, functions={"clean": lambda: events.append("exit")})
    with pytest.raises(ExecutionLimitError, match="step limit"):
        execute("let f() = { on error 0; on exit clean(); foreach item in range(100) do item }; f()", context)
    assert events == ["exit"]
    assert context.steps > context.max_steps


def test_cleanup_cancellation_is_deferred_and_reserve_is_bounded(execute):
    cancelled = False
    events = []
    def stop():
        nonlocal cancelled
        cancelled = True
        raise CancelledError("stop")
    context = Context(cancel_hook=lambda: cancelled, functions={"stop": stop, "clean": lambda: events.append("exit")})
    with pytest.raises(CancelledError):
        execute("let f() = { on exit clean(); stop() }; f()", context)
    assert events == ["exit"]
    context = Context(max_steps=35)
    with pytest.raises(ExecutionLimitError, match="cleanup step limit"):
        execute("let f() = { on exit { foreach n in range(10000) do n }; 7 }; f()", context)


def test_compiled_handlers_emit_python_try_finally_without_tree_dispatch(monkeypatch):
    compiled = compile_program(parse("let f(a = 1) = { on error 0; on exit 9; a / 0 }; f() on error 7"))
    monkeypatch.setattr("clang_toolkit.cli.runtime.prototype.semantics.eval_statement", lambda *_: pytest.fail("tree dispatch"))
    assert compiled(Context()) == 0
    assert any(isinstance(node, ast.Try) and node.finalbody for node in ast.walk(compiled.__ctk_ast__))


def test_ordinary_cleanup_uses_submission_budget_not_emergency_reserve(execute):
    value, context = execute("let f() = { on exit 1; 7 }; foreach n in range(6000) do f()")
    assert value == [7] * 6000
    assert context.cleanup_steps == 0


def test_cancellation_during_cleanup_is_reported_after_cleanup(execute):
    cancelled = False
    def stop():
        nonlocal cancelled
        cancelled = True
    context = Context(cancel_hook=lambda: cancelled, functions={"stop": stop})
    with pytest.raises(CancelledError, match="cancelled"):
        execute("let f() = { on exit stop(); 7 }; f()", context)
    assert context.cleanup_depth == context.call_depth == 0
