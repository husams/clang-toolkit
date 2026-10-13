from __future__ import annotations

import pytest

from clang_toolkit.cli.runtime.prototype.compiler import compile_program
from clang_toolkit.cli.runtime.prototype.semantics import (
    Context,
    EvaluationError,
    ExecutionLimitError,
    Node,
)
from clang_toolkit.cli.runtime.prototype.tree import evaluate


def lit(value):
    return Node("literal", value)


def ref(name):
    return Node("ref", name)


def binary(operator, left, right):
    return Node("binary", operator, (left, right))


def program(*statements):
    return Node("program", children=statements)


def run_both(tree_program, bindings=None, **limits):
    results = []
    for engine in ("tree", "compiled"):
        context = Context(dict(bindings or {}), **limits)
        value = evaluate(tree_program, context) if engine == "tree" else compile_program(tree_program)(context)
        results.append((value, context.bindings, context.output, context.steps))
    return results


def test_engines_have_identical_values_output_and_steps():
    p = program(
        Node("let", "x", (lit(2),)),
        Node("assign", "+=", (ref("x"), binary("*", lit(3), lit(4)))),
        Node("print", children=(ref("x"),)),
    )
    assert run_both(p) == [(14, {"x": 14}, [14], 9)] * 2


def test_lazy_boolean_and_conditional_do_not_run_unselected_side():
    calls = []
    p = program(
        Node("let", "safe", (binary("and", lit(False), Node("call", "side", ())),)),
        Node("let", "selected", (Node("conditional", children=(lit(True), Node("block", children=(lit(7),)), Node("block", children=(Node("call", "side", ()),)))),)),
    )
    for engine in ("tree", "compiled"):
        context = Context(functions={"side": lambda: calls.append("called")})
        result = evaluate(p, context) if engine == "tree" else compile_program(p)(context)
        assert result == 7
        assert context.bindings == {"safe": False, "selected": 7}
    assert calls == []


@pytest.mark.parametrize("operator", ["+", "-", "*", "/", "%"])
def test_numeric_failures_are_shared(operator):
    if operator == "+":
        operands = (lit(1 << 63), lit(1))
    elif operator == "-":
        operands = (lit(-(1 << 63)), lit(1))
    elif operator == "*":
        operands = (lit(1 << 62), lit(3))
    else:
        operands = (lit(1), lit(0))
    value = Node("binary", operator, operands)
    p = program(value)
    for engine in ("tree", "compiled"):
        with pytest.raises(EvaluationError):
            context = Context()
            evaluate(p, context) if engine == "tree" else compile_program(p)(context)


def test_branch_and_loop_bindings_do_not_escape_but_outer_mutation_does():
    body = Node("block", children=(Node("let", "local", (ref("item"),)), Node("assign", "+=", (ref("total"), ref("item")))))
    p = program(
        Node("let", "total", (lit(0),)),
        Node("foreach", "item", (Node("list", children=(lit(2), lit(3))), body)),
    )
    for value, bindings, _, _ in run_both(p):
        assert value == [2, 5]
        assert bindings == {"total": 5}


def test_failed_compound_update_is_atomic():
    p = program(Node("let", "x", (lit(5),)), Node("assign", "+=", (ref("x"), lit(1 << 63))))
    for engine in ("tree", "compiled"):
        context = Context()
        with pytest.raises(EvaluationError):
            evaluate(p, context) if engine == "tree" else compile_program(p)(context)
        assert context.bindings == {"x": 5}


def test_foreach_result_and_steps_are_bounded():
    p = program(Node("foreach", "item", (Node("list", children=(lit(1), lit(2))), Node("block", children=()))))
    for engine in ("tree", "compiled"):
        with pytest.raises(ExecutionLimitError):
            context = Context(max_steps=2)
            evaluate(p, context) if engine == "tree" else compile_program(p)(context)


def test_compiler_lowers_control_flow_and_does_not_dispatch_tree(monkeypatch):
    body = Node("block", children=(Node("assign", "+=", (ref("total"), ref("item"))),))
    p = program(
        Node("let", "total", (lit(0),)),
        Node("foreach", "item", (Node("list", children=(lit(1), lit(2), lit(3))), body)),
    )
    compiled = compile_program(p)
    assert "for _ordinal_" in compiled.__ctk_source__
    assert "eval_statement" not in compiled.__ctk_source__
    monkeypatch.setattr("clang_toolkit.cli.runtime.prototype.semantics.eval_expr", lambda *_: (_ for _ in ()).throw(AssertionError("tree dispatch")))
    monkeypatch.setattr("clang_toolkit.cli.runtime.prototype.semantics.eval_statement", lambda *_: (_ for _ in ()).throw(AssertionError("tree dispatch")))
    context = Context()
    assert compiled(context) == [1, 3, 6]
    assert context.bindings == {"total": 6}


def test_assigned_foreach_is_a_value_in_both_engines():
    body = Node("block", children=(Node("dict", children=(Node("entry", "index", (ref("item"),)),)),))
    loop = Node("foreach", "item", (Node("list", children=(lit(0), lit(1), lit(2))), body))
    selection = Node("get", "index", (Node("index", children=(ref("rows"), lit(2))),))
    p = program(Node("let", "rows", (loop,)), selection)
    assert run_both(p) == [(2, {"rows": [{"index": 0}, {"index": 1}, {"index": 2}]}, [], 23)] * 2
