"""Shared guards for ordinary generated list loops; no per-item continuations."""

from __future__ import annotations

from typing import Any

from .list_loops import (
    LoopShape,
    _callback_value,
    _host_ready,
    _insertable,
    _push,
    _scope,
    _snapshot,
    _statement,
)
from .list_recursion import _Arena
from .semantics import ExecutionLimitError, _as_bool, _error, observe_statement


class LoopPlan:
    """Immutable source metadata prepared once when a runnable is compiled."""

    def __init__(self, shape: LoopShape) -> None:
        self.shape = shape
        self.body = shape.full.children[0]
        self.base = shape.empty.children[0]
        self.base_value = _statement(self.base.children[0])
        self.observe_base = self.base.children[0].kind == "observe"
        self.match_steps = (shape.group, shape.group)
        self.recursive_steps = (shape.recursive, *shape.recursive.children)
        self.base_steps = (self.base, self.base_value)
        self.callback_steps = (shape.argument,) * (2 if shape.kind == "map" else 1)
        argument = _push(shape.push)[1]
        self.argument_steps = (argument, argument)
        self.enter_steps = (
            (self.body, *shape.push_steps) if shape.kind == "map" else (self.body,)
        )
        self.observe_push = self.body.children[0].kind == "observe"
        if shape.kind == "filter":
            self.enter_steps = (self.body, shape.condition, *self.callback_steps)
            self.yes, self.no = shape.condition.children[1:]
            self.observe_push = self.yes.children[0].kind == "observe"
            self.observe_condition = self.body.children[0].kind == "observe"
        elif shape.kind == "reverse":
            self.assignment = _statement(self.body.children[0])
            consume = self.assignment.children[0]
            self.consumed = int(consume.kind == "consume")
            self.descent_steps = (
                (self.assignment, consume) if self.consumed else (self.assignment,)
            )
            self.enter_steps = (self.body, *self.descent_steps)
            self.final = _statement(self.body.children[2])
            self.observe_assignment = self.body.children[0].kind == "observe"
            self.observe_push = self.body.children[1].kind == "observe"
            self.observe_final = self.body.children[2].kind == "observe"

    def __call__(
        self, context: Any, arguments: list[Any], owner: Any, call_node: Any
    ) -> _LoopExecution:
        return _LoopExecution(self, context, arguments, owner, call_node)


class _LoopExecution:
    """One invocation's scopes, shallow snapshot, and logical execution budget.

    Adjacent pure ticks are batched only without hooks. Source ordering around
    callbacks, host operations, observations and scope changes stays explicit.
    """

    def __init__(
        self, plan: LoopPlan, context: Any, arguments: list[Any], owner: Any, node: Any
    ) -> None:
        self.plan = plan
        self.shape = plan.shape
        self.context = context
        self.arguments = arguments
        self.owner = owner
        self.node = node
        self.saved_scopes = list(context._scopes)
        self.saved_depth = context.consume_depth
        self.arena = _Arena()
        self.callback, self.output = (
            arguments[1:] if self.shape.kind != "reverse" else (None, None)
        )
        self.branch_value = None

    def __enter__(self) -> _LoopExecution:
        try:
            self.items = _snapshot(self.context, self.arguments, self.owner, self.node)
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, *exception: Any) -> None:
        if self.shape.kind == "reverse":
            self.context.consume_depth = self.saved_depth
        self.context._scopes[:] = self.saved_scopes

    def bind(self, index: int) -> None:
        _scope(
            self.context,
            self.owner,
            self.shape,
            self.items,
            index,
            self.arena,
            self.callback,
            self.output,
        )

    def enter(self, index: int) -> None:
        context, plan = self.context, self.plan
        if index:
            context.tick_many(plan.match_steps)
        self.bind(index)
        context.tick_many(plan.enter_steps)

    def host_ready(self) -> bool:
        return _host_ready(self.context)

    def map_value(self, callback: Any, head: Any) -> Any:
        context, node = self.context, self.shape.argument
        context.tick_many(self.plan.callback_steps)
        return _callback_value(context, node, node.children[0], callback, head, True)

    def keep(self, callback: Any, head: Any) -> bool:
        context, plan, shape = self.context, self.plan, self.shape
        node = shape.argument
        value = _callback_value(context, node, node.children[0], callback, head, False)
        keep = _as_bool(context, value, shape.condition)
        context.push_scope()
        self.branch_value = None
        if keep:
            context.tick(plan.yes)
            context.tick_many(shape.push_steps)
        else:
            context.tick(plan.no)
        return keep

    def validate(self, output: list[Any], value: Any) -> None:
        if self.shape.kind != "map":
            self.context.tick_many(self.plan.argument_steps)
        _insertable(self.context, self.shape.push, output, value)

    def pushed(self, value: Any) -> None:
        if self.plan.observe_push:
            observe_statement(self.context, self.shape.push, value)
        self.branch_value = value

    def end_branch(self) -> None:
        self.context.pop_scope()
        if self.plan.observe_condition:
            observe_statement(self.context, self.shape.condition, self.branch_value)

    def advance(self) -> None:
        self.context.tick_many(self.plan.recursive_steps)

    def resume(self) -> Any:
        """An altered host may rebind arguments; resume from the live scope."""
        self.host_push()
        if self.shape.kind == "filter":
            self.end_branch()
        self.advance()
        arguments = [
            self.context.lookup(name)
            for name in (self.shape.tail, self.shape.callback, self.shape.output)
        ]
        return self.owner.recursion.run(
            self.context, arguments, self.owner, self.shape.recursive
        )

    def host_push(self) -> None:
        self.pushed(self.context.host_evaluator(self.context, self.shape.push))

    def finish(self, output: list[Any]) -> list[Any]:
        context, plan = self.context, self.plan
        if self.items:
            context.tick(self.shape.group)
        self.bind(len(self.items))
        context.push_scope()
        try:
            context.tick_many(plan.base_steps)
            if plan.observe_base:
                observe_statement(context, plan.base_value, output)
        finally:
            context.pop_scope()
        return output

    def descend(self, index: int) -> None:
        self.enter(index)
        context, plan = self.context, self.plan
        context.consume_depth += plan.consumed
        self.advance()
        if index >= context.max_items:
            raise _error(
                context,
                self.shape.recursive,
                "continuation stack exceeds item limit",
                ExecutionLimitError,
            )

    def unwind(self, index: int, output: list[Any]) -> None:
        context, plan = self.context, self.plan
        context.consume_depth -= plan.consumed
        self.bind(index)
        context.define(self.shape.result, output)
        if plan.observe_assignment:
            observe_statement(context, plan.assignment, output)
        context.tick_many(self.shape.push_steps)

    def result(self) -> list[Any]:
        context, plan = self.context, self.plan
        context.tick(plan.final)
        output = context.lookup(self.shape.result)
        if plan.observe_final:
            observe_statement(context, plan.final, output)
        return output
