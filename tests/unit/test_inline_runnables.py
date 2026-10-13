from __future__ import annotations

import pytest

from clang_toolkit.cli.runtime.prototype.compiler import compile_program
from clang_toolkit.cli.runtime.prototype.repl_language import parse as parse_repl
from clang_toolkit.cli.runtime.prototype.runnables import RunnableBlock
from clang_toolkit.cli.runtime.prototype.semantics import (
    Context,
    EvaluationError,
    ExecutionLimitError,
)
from clang_toolkit.cli.runtime.prototype.syntax import parse
from clang_toolkit.cli.runtime.prototype.tree import evaluate


@pytest.fixture(
    params=[
        (parse, "tree"),
        (parse, "compiled"),
        (parse_repl, "tree"),
        (parse_repl, "compiled"),
    ]
)
def execute(request):
    parser, engine = request.param

    def run(source, context=None):
        context = context or Context()
        context.source = source
        program = parser(source)
        value = (
            evaluate(program, context)
            if engine == "tree"
            else compile_program(program)(context)
        )
        return value, context

    return run


@pytest.mark.parametrize(
    "body, expected",
    [
        ("x + 1", 6),
        ("{ let extra = 1; x + extra }", 6),
        ("if x > 0 then x + 1 else 0", 6),
        ("if x < 0 then x", None),
        ("{}", None),
    ],
)
def test_inline_argument_expression_and_block_bodies(execute, body, expected):
    value, context = execute(
        f"let apply(operation, value) = operation(value); apply((x) = {body}, 5)"
    )
    assert value == expected
    assert context.bindings.keys() == {"apply"}
    assert context.scopes == (context.bindings,)
    assert context.call_depth == 0


def test_inline_zero_parameters_and_multiple_parameters(execute):
    value, _ = execute(
        "let run(f) = f(); let apply(f, l, r) = f(l, r); "
        "[run(() = 42), apply((l, r) = l + r, 19, 23)]"
    )
    assert value == [42, 42]


def test_inline_defaults_are_dormant_fresh_and_evaluated_in_order(execute):
    seen = []
    context = Context(functions={"next": lambda: seen.append(1) or len(seen)})
    value, _ = execute(
        "let f = (a, b = a * next(), c = [b]) = { c[0] += 1; c }; "
        "[f(2), f(3), f(9, 10)]",
        context,
    )
    assert value == [[3], [7], [11]]
    assert seen == [1, 1]


def test_inline_bodies_and_defaults_do_not_run_until_called(execute):
    context = Context(functions={"side": lambda: pytest.fail("dormant body ran")})
    value, _ = execute(
        "let ignore(operation) = 42; ignore((x = side()) = { side() })", context
    )
    assert value == 42
    assert "<inline>" not in context.bindings


def test_inline_closures_can_escape_and_capture_definition_locals(execute):
    value, _ = execute(
        "let make(base) = (x, delta = base) = x + delta; "
        "let f = make(2); let alias = f; let caller(base) = alias(40); "
        "[caller(100), f(1)]"
    )
    assert value == [42, 3]


def test_inline_captures_by_reference_and_remains_a_first_class_value(execute):
    value, context = execute(
        "let offset = 1; let operations = [(x) = x + offset]; "
        "let operation = operations[0]; offset = 2; operation(40)"
    )
    assert value == 42
    assert isinstance(context.bindings["operation"], RunnableBlock)
    assert "<inline>" not in context.bindings


def test_inline_callbacks_can_be_other_callbacks_default_values(execute):
    value, _ = execute(
        "let apply(f, x) = f(x); apply((x, operation = (n) = n + 1) = operation(x), 41)"
    )
    assert value == 42


def test_inline_conditional_bodies_keep_their_else(execute):
    value, _ = execute(
        "let make(flag) = if flag then (x) = if x > 0 then x else 0 else (x) = 9; "
        "let positive = make(true); let other = make(false); "
        "[positive(5), positive(-1), other(5)]"
    )
    assert value == [5, 0, 9]


def test_inline_handlers_run_with_body_locals_and_cleanup(execute):
    value, context = execute(
        "let state = [0]; let apply(f, x) = f(x); "
        "let answer = apply((x) = { on error fallback; "
        "on exit { state[0] += 1 }; let fallback = 7; 10 / x }, 0); "
        "[answer, state[0]]"
    )
    assert value == [7, 1]
    assert "fallback" not in context.bindings


def test_inline_arity_is_checked_before_argument_effects(execute):
    context = Context(functions={"side": lambda: pytest.fail("argument evaluated")})
    with pytest.raises(EvaluationError, match="expects 0 argument"):
        execute("let f = () = {}; f(side())", context)
    assert context.scopes == (context.bindings,)
    assert context.call_depth == 0


def test_inline_calls_share_limits_and_cleanup_frames(execute):
    context = Context(max_steps=30)
    with pytest.raises(ExecutionLimitError, match="step limit"):
        execute(
            "let apply(f) = f(); apply(() = { foreach n in range(100) do n })", context
        )
    assert context.scopes == (context.bindings,)
    assert context.call_depth == 0


@pytest.mark.parametrize(
    "source, message",
    [
        ("let f = (x, x) = x", "duplicate parameter"),
        ("let f = (x = 1, y) = x", "required parameters"),
        ("foreach item in [1] do { let f = () = { break }; 1 }", "enclosing foreach"),
        (
            "foreach item in [1] do { let f = () = { on error continue; 1 }; 1 }",
            "enclosing foreach",
        ),
        ("let f = () = { 1; on exit 0 }", "beginning of a block"),
    ],
)
def test_inline_validation_precedes_effects(execute, source, message):
    with pytest.raises(ValueError, match=message):
        execute(source)


@pytest.mark.parametrize("parser", [parse, parse_repl])
def test_inline_source_locations_and_defaults_share_runnable_ir(parser):
    node = parser("let f = (x, y = 1) = x + y").children[0].children[0]
    assert node.kind == "inline_runnable"
    assert node.value == ("<inline>", ("x", "y"))
    assert node.children[0].kind == "block"
    assert node.children[1].kind == "parameter"
    assert (node.line, node.column) == (1, 9)


@pytest.mark.parametrize("body", ["x + 1", "{ on error 0; on exit 7; x + 1 }"])
def test_inline_python_functions_do_not_use_tree_dispatch(monkeypatch, body):
    source = f"let apply(f, x) = f(x); apply((x) = {body}, 41)"
    compiled = compile_program(parse_repl(source))
    monkeypatch.setattr(
        "clang_toolkit.cli.runtime.prototype.semantics.eval_statement",
        lambda *_: pytest.fail("tree statement dispatch"),
    )
    monkeypatch.setattr(
        "clang_toolkit.cli.runtime.prototype.semantics.eval_expr",
        lambda *_: pytest.fail("tree expression dispatch"),
    )
    context = Context()
    context.source = source
    assert compiled(context) == 42
    assert "_create_runnable" in compiled.__ctk_source__
    assert "eval_statement" not in compiled.__ctk_source__
