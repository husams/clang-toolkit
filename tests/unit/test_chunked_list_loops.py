from __future__ import annotations

import ast
import sys
from threading import Event

import pytest
from clang_toolkit.cli.runtime.prototype.semantics import (
    CancelledError,
    Context,
    PrototypeError,
)
from tests.unit import test_direct_list_loops as shared

DEFINITIONS = shared.DEFINITIONS
execute = shared.execute
runtime_env = shared.runtime_env

CASES = [
    ("map_into", "map_into(xs, (x) x * 2, out)"),
    ("filter_into", "filter_into(xs, (x) x % 2 == 0, out)"),
    ("reverse_list", "reverse_list(xs)"),
]


@pytest.mark.parametrize("target,expression", CASES)
def test_generated_chunk_inner_loops_only_transform_and_append(
    execute, target, expression
):
    context = Context(bindings={"xs": list(range(257)), "out": []})
    execute(DEFINITIONS, context)
    execute(expression, context)
    native = context.lookup(target).direct_loop.__ctk_plan__.last_plain
    assert native is not None
    loops = [
        node
        for node in ast.walk(ast.parse(native.__ctk_source__))
        if isinstance(node, ast.For)
    ]
    assert len(loops) == 2, (
        "plain traversal needs bounded outer chunks and a plain inner loop"
    )
    inner = next(
        node
        for node in loops
        if not any(
            isinstance(child, ast.For)
            for statement in node.body
            for child in ast.walk(statement)
        )
    )
    for statement in inner.body:
        for node in ast.walk(statement):
            assert not (
                isinstance(node, ast.Name)
                and node.id in {"context", "observer", "cancel", "plan"}
            )
            if isinstance(node, ast.Call):
                assert (
                    isinstance(node.func, ast.Attribute) and node.func.attr == "append"
                )
    assert "islice(pending, 128)" in native.__ctk_source__


def outcome(execute, target, expression, values, enabled, budget=1_000_000):
    source = values.copy()
    context = Context(bindings={"xs": source, "out": source})
    execute(DEFINITIONS, context)
    function = context.lookup(target)
    if not enabled:
        object.__setattr__(function, "direct_loop", None)
    context.steps = context.step_count = 0
    context.max_steps = budget
    try:
        result = ("ok", execute(expression, context))
    except PrototypeError as error:
        result = (type(error).__name__, str(error))
    assert context.call_depth == context.consume_depth == 0
    assert context.scopes == (context.bindings,)
    return (
        result,
        context.steps,
        context.step_count,
        context.current_location,
        context.location,
        context.bindings["out"],
        context.session.last_tail,
    )


@pytest.mark.parametrize("target,expression", CASES)
@pytest.mark.parametrize("size", [127, 128, 129, 255, 256, 257])
def test_chunk_boundaries_preserve_values_aliases_and_execution_state(
    execute, target, expression, size
):
    values = list(range(-(size // 2), size - size // 2))
    assert outcome(execute, target, expression, values, True) == outcome(
        execute, target, expression, values, False
    )


@pytest.mark.parametrize("target,expression", CASES)
def test_chunk_budget_boundaries_preserve_partial_mutation_and_errors(
    execute, target, expression
):
    values = list(range(129))
    total = outcome(execute, target, expression, values, False)[1]
    for budget in [0, 1, total - 1, total, total + 1, total + 3, total + 100]:
        assert outcome(execute, target, expression, values, True, budget) == outcome(
            execute, target, expression, values, False, budget
        ), budget


@pytest.mark.parametrize("target,expression", CASES)
@pytest.mark.parametrize("trigger", [10, 140, 270])
def test_event_cancellation_settles_completed_chunks(
    execute, monkeypatch, target, expression, trigger
):
    from clang_toolkit.cli.runtime.prototype import plain_list_loops

    size = 400
    event = Event()
    context = Context(
        bindings={"xs": list(range(size)), "out": []}, cancel_hook=event.is_set
    )
    execute(DEFINITIONS, context)
    direct = context.lookup(target).direct_loop
    plan = direct.__ctk_plan__
    prepare = plain_list_loops.prepare_plain
    prepared = {}
    captured = {}

    def prepare_capture(loop):
        result = prepare(loop)
        assert result is not None
        function = result[0]
        prepared.update(
            code=function.__code__,
            steps=context.steps,
            lines=function.__ctk_source__.splitlines(),
        )
        sys.settrace(cancel_inside_chunk)
        return result

    target_head = size - 1 - trigger if target == "reverse_list" else trigger

    def cancel_inside_chunk(frame, action, value):
        if action == "line" and frame.f_code is prepared.get("code"):
            if frame.f_locals.get("head") == target_head:
                event.set()
            line = prepared["lines"][frame.f_lineno - 1]
            if "cancelled(" in line and event.is_set():
                captured.update(
                    output=frame.f_locals["output"].copy(),
                    steps=context.steps,
                    depth=context.consume_depth,
                    tail=context.session.last_tail,
                )
        return cancel_inside_chunk

    monkeypatch.setitem(direct.__globals__, "prepare_plain", prepare_capture)
    previous_trace = sys.gettrace()
    try:
        with pytest.raises(CancelledError, match="execution cancelled"):
            execute(expression, context)
    finally:
        sys.settrace(previous_trace)
    completed = ((trigger // 128) + 1) * 128
    if target == "map_into":
        expected = [value * 2 for value in range(completed)]
        delta = completed * 15 - 2
        node, tail = plan.shape.group, "host"
    elif target == "filter_into":
        expected = [value for value in range(completed) if value % 2 == 0]
        delta = completed * 17 + len(expected) * 3 - 2
        node, tail = plan.shape.group, "binary"
    else:
        expected = list(range(size - 1, size - 1 - completed, -1))
        delta = size * 7 + 1 + completed * 4
        node, tail = plan.shape.push, "let"
        assert captured["depth"] == size - completed - 1
    assert captured["output"] == expected
    assert captured["steps"] == context.steps == prepared["steps"] + delta
    assert captured["tail"] == context.session.last_tail == tail
    assert context.step_count == context.steps
    assert context.current_location == (node.line, node.column)
    assert context.call_depth == context.consume_depth == 0
    assert context.scopes == (context.bindings,)
