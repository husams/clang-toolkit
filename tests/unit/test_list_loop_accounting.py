from __future__ import annotations

import pytest

from clang_toolkit.cli.runtime.prototype.semantics import (
    Context,
    ExecutionLimitError,
    Node,
)


@pytest.mark.parametrize("budget", range(6))
def test_adjacent_steps_keep_exact_failure_and_location(budget):
    nodes = tuple(Node("ref", line=10 + i, column=3) for i in range(4))
    outcomes = []
    for batched in (True, False):
        context = Context(max_steps=budget)
        try:
            if batched:
                context.tick_many(nodes)
            else:
                for node in nodes:
                    context.tick(node)
            error = None
        except ExecutionLimitError as failure:
            error = str(failure)
        outcomes.append((error, context.steps, context.step_count, context.location))
    assert outcomes[0] == outcomes[1]


@pytest.mark.parametrize("instrumentation", ["instance", "class", "subclass"])
def test_adjacent_steps_preserve_instrumented_ticks(monkeypatch, instrumentation):
    seen = []
    original = Context.tick

    def tick(context, node=None):
        seen.append((node, context.steps))
        original(context, node)

    context = Context()
    if instrumentation == "instance":
        context.tick = lambda node=None: tick(context, node)
    elif instrumentation == "class":
        monkeypatch.setattr(Context, "tick", tick)
    else:

        class InstrumentedContext(Context):
            def tick(self, node=None):
                tick(self, node)

        context = InstrumentedContext()
    nodes = (Node("ref", line=1), Node("ref", line=2))
    context.tick_many(nodes)
    assert seen == [(nodes[0], 0), (nodes[1], 1)]


def test_adjacent_steps_preserve_cleanup_reserve_and_cancellation_checks():
    checks = []
    context = Context(max_steps=0, cancel_hook=lambda: checks.append(True) or True)
    context.cleanup_depth = 1
    nodes = (Node("ref", line=1), Node("ref", line=2))
    context.tick_many(nodes)
    assert context.steps == context.step_count == context.cleanup_steps == 2
    assert context.location == (2, None)
    # tick short-circuits cancellation once the primary budget is exhausted.
    assert checks == []


def test_scalar_shortcut_preserves_custom_type_hooks():
    from clang_toolkit.cli.runtime.collections import ensure_insertable
    from clang_toolkit.cli.runtime.prototype.list_loops import _insertable

    outcomes = []
    for guarded in (True, False):
        checks = []

        class Value:
            @property
            def __class__(self):
                checks.append("type check")
                raise ValueError("custom type check failed")

        with pytest.raises(ValueError) as failure:
            if guarded:
                _insertable(Context(), None, [], Value())
            else:
                ensure_insertable([], Value())
        outcomes.append((str(failure.value), checks))
    assert outcomes[0] == outcomes[1]
