from __future__ import annotations

import pytest

from clang_toolkit.cli.runtime.prototype.compiler import compile_program
from clang_toolkit.cli.runtime.prototype.semantics import Context, EvaluationError
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
