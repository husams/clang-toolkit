from __future__ import annotations

import pytest

from clang_toolkit.cli.runtime.prototype.compiler import compile_program
from clang_toolkit.cli.runtime.prototype.semantics import Context, EvaluationError, ExecutionLimitError
from clang_toolkit.cli.runtime.prototype.syntax import parse
from clang_toolkit.cli.runtime.prototype.tree import evaluate


@pytest.fixture(params=["tree", "compiled"])
def execute(request):
    def run(source, context=None):
        context = context or Context()
        program = parse(source)
        value = evaluate(program, context) if request.param == "tree" else compile_program(program)(context)
        return value, context
    return run


def test_definition_is_dormant_and_calls_return_final_value(execute):
    _, context = execute('let greet() = { print "ready" }; let twice(x) = { x * 2 }')
    assert context.output == []
    value, _ = execute("let answer = twice(21); greet(); answer", context)
    assert value == 42
    assert context.output == ["ready"]


def test_lexical_captures_aliases_and_local_cleanup(execute):
    value, context = execute(
        "let factor = 2; let scaled(x) = { x * factor }; let alias = scaled; "
        "let caller(factor) = { scaled(10) }; let before = caller(9); factor = 3; "
        "let scaled(x) = { 0 }; [before, alias(10), scaled(10)]"
    )
    assert value == [20, 30, 0]
    assert "x" not in context.bindings
    assert context.scopes == (context.bindings,)


def test_nested_closure_retains_environment(execute):
    value, _ = execute(
        "let make(factor) = { let scale(value) = { value * factor }; scale }; "
        "let operation = make(3); operation(14)"
    )
    assert value == 42


def test_recursion_and_original_self_survive_rebinding(execute):
    value, _ = execute(
        "let sum(n) = { if n == 0 then 0 else n + sum(n - 1) }; "
        "let original = sum; let sum(n) = { 0 }; original(5)"
    )
    assert value == 15


def test_arity_rejected_before_argument_effects(execute):
    context = Context(functions={"side": lambda: pytest.fail("argument evaluated")})
    with pytest.raises(EvaluationError, match="expects 0 argument"):
        execute("let empty() = {}; empty(side())", context)
    assert context.call_depth == 0


def test_compiled_body_has_python_functions_and_no_tree_dispatch(monkeypatch):
    compiled = compile_program(parse("let twice(x) = { x * 2 }; twice(21)"))
    monkeypatch.setattr("clang_toolkit.cli.runtime.prototype.semantics.eval_statement",
                        lambda *_: pytest.fail("tree dispatch"))
    assert compiled(Context()) == 42
    assert "_define_runnable" in compiled.__ctk_source__
    assert "eval_statement" not in compiled.__ctk_source__


def test_calls_share_the_submission_step_budget(execute):
    context = Context(max_steps=30)
    with pytest.raises(ExecutionLimitError, match="step limit"):
        execute('let work() = { foreach n in range(10) do n }; work(); work()', context)
    assert context.call_depth == 0
    assert context.scopes == (context.bindings,)


def test_recursive_calls_have_a_checked_depth_limit(execute):
    with pytest.raises(ExecutionLimitError, match="call depth"):
        execute('let forever() = { forever() }; forever()')


def test_arguments_run_once_in_order(execute):
    seen = []
    context = Context(functions={"next": lambda n: seen.append(n) or n})
    value, _ = execute('let sum(a, b) = { a + b }; sum(next(1), next(2))', context)
    assert value == 3 and seen == [1, 2]


def test_body_error_reports_definition_and_call_location(execute):
    with pytest.raises(EvaluationError, match=r"defined at line 1.*called at line 2"):
        execute('let divide(n) = { 7 / n }\ndivide(0)')


def test_defaults_are_lazy_fresh_and_can_reference_earlier_parameters(execute):
    seen = []
    context = Context(functions={"next": lambda: seen.append(1) or len(seen)})
    value, _ = execute("let f(a, b = a * next(), c = [b]) = { c[0] += 1; c }; [f(2), f(3), f(9, 10)]", context)
    assert value == [[3], [7], [11]]
    assert seen == [1, 1]
    assert context.scopes == (context.bindings,)


def test_defaults_capture_definition_scope_and_stay_dormant(execute):
    value, _ = execute("let factor = 2; let f(a = factor) = { a }; let caller(factor) = { f() }; caller(9)")
    assert value == 2
    context = Context(functions={"side": lambda: pytest.fail("default evaluated")})
    execute("let f(a = side()) = { a }; f(7)", context)


def test_default_arity_is_checked_before_argument_effects(execute):
    context = Context(functions={"side": lambda: pytest.fail("argument evaluated")})
    with pytest.raises(EvaluationError, match="expects 1..2"):
        execute("let f(a, b = 1) = { a + b }; f(side(), side(), side())", context)


def test_required_parameter_after_default_is_rejected(execute):
    with pytest.raises(ValueError, match="required parameters"):
        execute("let f(a = 1, b) = { a }")


def test_expression_bodies_calls_defaults_and_lazy_conditionals(execute):
    value, context = execute(
        "let add(l, r = 1) = l + r; let inc(x) = add(x, 1); "
        "let constant(x) = add(1, 2); "
        "let add_if(l, h) = if l < h then l + h else 0; "
        "let safe(x) = if x == 0 then 7 else 10 / x; "
        "[add(2), inc(4), constant(9), add_if(2, 5), add_if(5, 2), safe(0)]"
    )
    assert value == [3, 5, 3, 7, 0, 7]
    assert context.scopes == (context.bindings,)


def test_expression_bodies_capture_alias_and_recursive_self(execute):
    value, _ = execute(
        "let factor = 2; let scale(x) = x * factor; let alias = scale; "
        "let caller(factor) = alias(3); "
        "let sum(n) = if n == 0 then 0 else n + sum(n - 1); "
        "let original = sum; let sum(n) = 0; [caller(9), original(5)]"
    )
    assert value == [6, 15]


def test_expression_body_compiles_without_tree_dispatch(monkeypatch):
    compiled = compile_program(parse("let add(l, r) = l + r; add(19, 23)"))
    monkeypatch.setattr("clang_toolkit.cli.runtime.prototype.semantics.eval_statement",
                        lambda *_: pytest.fail("tree dispatch"))
    assert compiled(Context()) == 42


def test_expression_body_is_dormant_and_conditionals_keep_their_else(execute):
    seen = []
    context = Context(functions={"side": lambda: seen.append(1) or 7})
    execute("let dormant() = side()", context)
    assert seen == []
    value, _ = execute(
        "let choose(x) = if x > 0 then if x < 10 then x else 10 else 0\n"
        "let optional(x) = if x > 0 then x\n"
        "let multiline(x) = (x +\n 1)\n"
        "[choose(5), choose(12), choose(-1), optional(0), multiline(2), dormant()]",
        context,
    )
    assert value == [5, 10, 0, None, 3, 7]
    assert seen == [1]
