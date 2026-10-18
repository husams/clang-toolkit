from __future__ import annotations

import ast
import inspect
import sys
from dataclasses import replace
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
def test_generated_kernels_only_transform_and_append(execute, target, expression):
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
    assert len(loops) == 1, "generated kernels need one ordinary for loop"
    assert [arg.arg for arg in ast.parse(native.__ctk_source__).body[0].args.args] == [
        "items",
        "output",
    ]
    for node in ast.walk(ast.parse(native.__ctk_source__)):
        assert not (
            isinstance(node, ast.Name)
            and node.id in {"context", "observer", "cancel", "plan", "islice"}
        )
        if isinstance(node, ast.Call):
            assert isinstance(node.func, ast.Attribute) and node.func.attr == "append"


@pytest.mark.parametrize("size", [0, 1, 128, 129, 257])
def test_shared_runner_invokes_kernels_once_per_bounded_chunk(
    execute, monkeypatch, size
):
    from clang_toolkit.cli.runtime.prototype import plain_list_loops

    prepare = plain_list_loops.prepare_plain
    entries = []
    for target, expression in CASES:
        context = Context(bindings={"xs": list(range(size)), "out": []})
        execute(DEFINITIONS, context)
        direct = context.lookup(target).direct_loop
        calls = []

        def capture(loop):
            result = prepare(loop)
            assert result is not None
            runner, arguments = result
            kernel = loop.plan.last_plain
            entries.append(runner)
            assert runner is not kernel
            assert arguments[6] is kernel

            def counted(items, output):
                values = list(items)
                calls.append(values)
                return kernel(values, output)

            return runner, (*arguments[:6], counted, *arguments[7:])

        monkeypatch.setitem(direct.__globals__, "prepare_plain", capture)
        actual = execute(expression, context)
        values = list(range(size))
        expected = (
            [x * 2 for x in values]
            if target == "map_into"
            else [x for x in values if x % 2 == 0]
            if target == "filter_into"
            else list(reversed(values))
        )
        assert actual == expected
        ordered = list(reversed(values)) if target == "reverse_list" else values
        assert calls == [ordered[i : i + 128] for i in range(0, size, 128)]
        assert context.call_depth == context.consume_depth == 0
        assert context.scopes == (context.bindings,)
    assert len(set(entries)) == 1, "all three kinds must use the same chunk runner"


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
        prepared.update(
            code=plan.last_plain.__code__,
            runner=result[0].__code__,
            steps=context.steps,
        )
        sys.settrace(cancel_inside_chunk)
        return result

    target_head = size - 1 - trigger if target == "reverse_list" else trigger

    def cancel_inside_chunk(frame, action, value):
        if action == "line" and frame.f_code is prepared.get("code"):
            if frame.f_locals.get("head") == target_head:
                event.set()
        if (
            action == "call"
            and frame.f_code is plain_list_loops._cancelled.__code__
            and event.is_set()
        ):
            runner_frame = frame.f_back
            assert runner_frame.f_code is prepared["runner"]
            captured.update(
                output=runner_frame.f_locals["output"].copy(),
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


def test_shared_loop_has_no_per_operation_branches():
    from clang_toolkit.cli.runtime.prototype import plain_list_loops

    source = inspect.getsource(plain_list_loops._run_plain_chunks)
    tree = ast.parse(source)
    loops = [node for node in ast.walk(tree) if isinstance(node, ast.For)]
    assert len(loops) == 1
    body = [child for statement in loops[0].body for child in ast.walk(statement)]
    branches = [node for node in body if isinstance(node, (ast.If, ast.IfExp))]
    assert len(branches) == 1, "the shared loop should only branch for cancellation"
    assert "cancel" in ast.unparse(branches[0].test)
    calls = [node for node in body if isinstance(node, ast.Call)]
    assert (
        sum(
            isinstance(node.func, ast.Name) and node.func.id == "settle"
            for node in calls
        )
        == 1
    )
    assert not any(
        isinstance(node, ast.Name) and node.id == "checkpoint"
        for node in ast.walk(tree)
    ), "checkpoint preparation belongs to setup/settlement"
    assert not any(
        isinstance(node, ast.Name) and node.id in {"reverse", "filtering"}
        for node in ast.walk(tree)
    )


@pytest.mark.parametrize("target,expression", CASES)
@pytest.mark.parametrize("size", [0, 1, 128, 129, 256, 257])
def test_operation_policy_is_selected_once_and_owns_chunk_transitions(
    execute, monkeypatch, target, expression, size
):
    from clang_toolkit.cli.runtime.prototype import plain_list_loops

    context = Context(bindings={"xs": list(range(size)), "out": []})
    execute(DEFINITIONS, context)
    selections = []
    events = []
    policies = plain_list_loops._CHUNK_POLICIES
    kind = {"map_into": "map", "filter_into": "filter", "reverse_list": "reverse"}[
        target
    ]
    policy = policies[kind]
    assert not hasattr(policy, "checkpoint")

    def setup(run, items):
        events.append("setup")
        return policy.setup(run, items)

    def settle(run, count, before, keep):
        events.append(("settle", count))
        return policy.settle(run, count, before, keep)

    def finish(run, nonempty):
        events.append("finish")
        return policy.finish(run, nonempty)

    class SelectedPolicies(dict):
        def __getitem__(self, key):
            selections.append(key)
            return super().__getitem__(key)

    configured = SelectedPolicies(policies)
    configured[kind] = replace(policy, setup=setup, settle=settle, finish=finish)
    monkeypatch.setattr(plain_list_loops, "_CHUNK_POLICIES", configured)
    result = execute(expression, context)
    values = list(range(size))
    assert result == (
        [x * 2 for x in values]
        if kind == "map"
        else [x for x in values if x % 2 == 0]
        if kind == "filter"
        else values[::-1]
    )
    assert selections == [kind]
    assert events == (
        ["setup"]
        + [("settle", min(128, size - start)) for start in range(0, size, 128)]
        + ["finish"]
    )
    assert context.call_depth == context.consume_depth == 0
    assert context.scopes == (context.bindings,)


@pytest.mark.parametrize("target,expression", CASES)
def test_final_chunk_cancellation_preserves_finish_checkpoints(
    execute, monkeypatch, target, expression
):
    from clang_toolkit.cli.runtime.prototype import plain_list_loops

    size = 257
    event = Event()
    context = Context(
        bindings={"xs": list(range(size)), "out": []}, cancel_hook=event.is_set
    )
    execute(DEFINITIONS, context)
    direct = context.lookup(target).direct_loop
    plan = direct.__ctk_plan__
    prepare = plain_list_loops.prepare_plain
    captured = {}

    def prepare_capture(loop):
        entry = prepare(loop)
        assert entry is not None
        runner, arguments = entry
        captured["steps"] = context.steps
        kernel_code = arguments[6].__code__
        last_head = 0 if target == "reverse_list" else size - 1

        def cancel_last_item(frame, action, value):
            if action == "line" and frame.f_code is kernel_code:
                if frame.f_locals.get("head") == last_head:
                    event.set()
            return cancel_last_item

        def run(*args):
            previous_trace = sys.gettrace()
            try:
                sys.settrace(cancel_last_item)
                return runner(*args)
            finally:
                sys.settrace(previous_trace)
                captured["tail"] = context.session.last_tail
                captured["location"] = context.current_location
                captured["end_steps"] = context.steps
                captured["depth"] = context.consume_depth
                # Isolate the runner's finish checkpoint from enclosing calls.
                event.clear()

        return run, arguments

    monkeypatch.setitem(direct.__globals__, "prepare_plain", prepare_capture)
    if target == "reverse_list":
        assert execute(expression, context) == list(range(size - 1, -1, -1))
        delta, node, tail = size * 11 + 1, plan.final, "ref"
    else:
        with pytest.raises(CancelledError, match="execution cancelled"):
            execute(expression, context)
        if target == "map_into":
            assert context.bindings["out"] == [x * 2 for x in range(size)]
            delta = size * 15 - 2
        else:
            assert context.bindings["out"] == list(range(0, size, 2))
            delta = size * 17 + len(context.bindings["out"]) * 3 - 2
        node, tail = plan.shape.group, "host"
    assert captured["end_steps"] == captured["steps"] + delta
    assert captured["location"] == (node.line, node.column)
    assert captured["tail"] == tail
    assert captured["depth"] == 0
    assert context.call_depth == context.consume_depth == 0
    assert context.scopes == (context.bindings,)
