"""Proven scalar loop specializations with no per-element runtime dispatch."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from functools import lru_cache
from itertools import islice
from threading import Event
from typing import Any

from .semantics import CancelledError, Context, MAX_INT64, MIN_INT64, _error

_EVENT_IS_SET = Event.is_set
_TICK = Context.tick
_TICK_MANY = Context.tick_many
_CHUNK_SIZE = 128


@dataclass(frozen=True)
class ScalarLoop:
    body: Any
    parameter: str
    executable: Any
    expression: Any
    source: str
    ticks: int
    result_kind: str

    def safe_for(self, low: int, high: int) -> bool:
        return _expression(self.expression, self.parameter, low, high) is not None


def _expression(node: Any, parameter: str, low: int, high: int) -> Any:
    """Return native AST, result type, interval and exact source tick count."""
    kind, value = node.kind, node.value
    if kind == "ref" and value == parameter:
        if low < MIN_INT64 or high > MAX_INT64:
            return None
        return ast.Name("head", ast.Load()), "int", low, high, 1
    if kind == "literal" and (type(value) is int or type(value) is bool):
        if value < MIN_INT64 or value > MAX_INT64:
            return None
        return (
            ast.Constant(value),
            "bool" if type(value) is bool else "int",
            value,
            value,
            1,
        )
    if kind not in {"binary", "unary"}:
        return None
    parts = [_expression(child, parameter, low, high) for child in node.children]
    if not parts or any(part is None for part in parts):
        return None
    native, result_kind, lower, upper, count = parts[0]
    if kind == "unary":
        if value == "not" and result_kind == "bool":
            return ast.UnaryOp(ast.Not(), native), "bool", 0, 1, count + 1
        if result_kind != "int" or value not in {"+", "-"}:
            return None
        if value == "-":
            lower, upper = -upper, -lower
        if lower < MIN_INT64 or upper > MAX_INT64:
            return None
        return (
            ast.UnaryOp(ast.UAdd() if value == "+" else ast.USub(), native),
            "int",
            lower,
            upper,
            count + 1,
        )
    if len(parts) != 2:
        return None
    right, right_kind, rlow, rhigh, rcount = parts[1]
    count += rcount + 1
    comparisons = {
        "==": ast.Eq,
        "!=": ast.NotEq,
        "<": ast.Lt,
        "<=": ast.LtE,
        ">": ast.Gt,
        ">=": ast.GtE,
    }
    if value in comparisons:
        if (
            result_kind != right_kind
            or result_kind == "bool"
            and value not in {"==", "!="}
        ):
            return None
        return ast.Compare(native, [comparisons[value]()], [right]), "bool", 0, 1, count
    if result_kind != "int" or right_kind != "int":
        return None
    if value == "+":
        lower, upper, operator = lower + rlow, upper + rhigh, ast.Add()
    elif value == "-":
        lower, upper, operator = lower - rhigh, upper - rlow, ast.Sub()
    elif value == "*":
        products = (lower * rlow, lower * rhigh, upper * rlow, upper * rhigh)
        lower, upper, operator = min(products), max(products), ast.Mult()
    elif (
        value == "%"
        and node.children[0].kind == "ref"
        and node.children[1].kind == "literal"
        and rlow == rhigh
        and rlow != 0
    ):
        # DSL remainders follow the dividend's sign, including negative inputs.
        divisor = abs(rlow)
        native = ast.IfExp(
            ast.Compare(native, [ast.GtE()], [ast.Constant(0)]),
            ast.BinOp(native, ast.Mod(), ast.Constant(divisor)),
            ast.UnaryOp(
                ast.USub(),
                ast.BinOp(
                    ast.UnaryOp(ast.USub(), native), ast.Mod(), ast.Constant(divisor)
                ),
            ),
        )
        return native, "int", -(divisor - 1), divisor - 1, count
    else:
        return None
    if lower < MIN_INT64 or upper > MAX_INT64:
        return None
    return ast.BinOp(native, operator, right), "int", lower, upper, count


def compile_scalar_loop(
    body: Any, parameters: tuple[Any, ...], executable: Any
) -> ScalarLoop | None:
    if len(parameters) != 1 or type(parameters[0]) is not str or parameters[0] == "_":
        return None
    if (
        body.kind != "block"
        or len(body.children) != 1
        or body.children[0].kind != "observe"
    ):
        return None
    expression = body.children[0].children[0]
    pending, count = [expression], 0
    while pending:
        current = pending.pop()
        count += 1
        if count > 32:
            return None
        pending.extend(current.children)
    # Recognition is independent of input bounds; validate actual intervals later.
    result = _expression(expression, parameters[0], 0, 0)
    if result is None or result[4] > 32:
        return None
    native, result_kind, _low, _high, ticks = result
    module = ast.fix_missing_locations(ast.Expression(native))
    return ScalarLoop(
        body,
        parameters[0],
        executable,
        expression,
        ast.unparse(module),
        ticks + 1,
        result_kind,
    )


def _cancelled(context: Context, node: Any) -> None:
    """An observed cancellation stays cancelled even if another thread clears it."""
    context.location = context.current_location = (node.line, node.column)
    raise _error(context, node, "execution cancelled", CancelledError)


def prepare_plain(loop: Any) -> Any:
    """Hoist all invariants before native code, retaining guarded fallback."""
    from .repl import ReplSession, _ReplContext
    from .runnables import RunnableBlock

    context, plan, shape = loop.context, loop.plan, loop.shape
    plan.last_plain = None
    if (
        type(context) is not Context
        and type(context) is not _ReplContext
        or getattr(context.tick, "__func__", None) is not _TICK
        or getattr(context.tick_many, "__func__", None) is not _TICK_MANY
        or "tick_many" in context.__dict__
        or context.cleanup_depth
        or type(context.steps) is not int
        or type(context.max_steps) is not int
        or type(context.max_items) is not int
    ):
        return None
    cancel = context.cancel_hook
    if cancel is not None and (
        getattr(cancel, "__func__", None) is not _EVENT_IS_SET
        or Event.is_set is not _EVENT_IS_SET
        or type(getattr(cancel, "__self__", None)) is not Event
        or Event.__getattribute__ is not object.__getattribute__
        or type(cancel.__self__._flag) is not bool
    ):
        return None
    observer = context.statement_observer
    session = getattr(context, "session", None)
    if observer is not None and (
        getattr(observer, "__func__", None) is not ReplSession._plain_observer
        or ReplSession.observe is not ReplSession._plain_observer
        or type(session) is not ReplSession
        or getattr(observer, "__self__", None) is not session
    ):
        return None
    observed = session if observer is not None else None
    if not plan.observe_base or not plan.observe_push:
        return None
    nodes = [shape.push, plan.base_value]
    scalar = None
    if shape.kind == "reverse":
        if (
            not plan.observe_assignment
            or not plan.observe_final
            or len(loop.items) > context.max_items
        ):
            return None
        nodes.extend((plan.assignment, plan.final))
        prefix = len(plan.enter_steps) + len(plan.recursive_steps) + 2
        maximum = len(loop.items) * (prefix + 4) + (1 if loop.items else 2)
        expression, callback_ticks = "head", 0
    else:
        callback = loop.callback
        if (
            type(callback) is not RunnableBlock
            or callback.defaults
            or callback.recursion is not None
        ):
            return None
        scalar = callback.scalar_loop
        if (
            scalar is None
            or scalar.body is not callback.body
            or scalar.executable is not callback.executable
            or type(callback.parameters) is not tuple
            or len(callback.parameters) != 1
            or type(callback.parameters[0]) is not str
            or callback.parameters[0] != scalar.parameter
            or callback.__dict__.get("__ctk_filter_name__") is not None
        ):
            return None
        runtime = getattr(session, "runtime", None)
        depth = getattr(runtime, "_matcher_call_depth", context.call_depth)
        if depth >= 64:
            return None
        if shape.kind == "filter" and (
            scalar.result_kind != "bool" or not plan.observe_condition
        ):
            return None
        nodes.append(scalar.expression)
        if shape.kind == "filter":
            nodes.append(shape.condition)
        expression, callback_ticks = scalar.source, scalar.ticks
        # Maximum filter cost assumes every item is kept; insufficient budgets
        # retain the old path, including all partial outputs and exact errors.
        first = len(plan.enter_steps) + 1 + callback_ticks + len(plan.recursive_steps)
        first += len(plan.callback_steps) if shape.kind == "map" else 4
        maximum = len(loop.items) * (first + 2) + (1 if loop.items else 2)
    if context.steps + maximum > context.max_steps:
        return None
    if observed is not None and (
        any(id(node) in observed.top_statements for node in nodes)
        or id(shape.push) in observed.host_displays
    ):
        return None
    low = high = 0
    for index, item in enumerate(loop.items):
        if cancel is not None and index % _CHUNK_SIZE == 0 and cancel():
            _cancelled(context, plan.body if loop.items else plan.base)
        item_type = type(item)
        if scalar is not None:
            if item_type is not int:
                return None
            low, high = min(low, item), max(high, item)
        elif not (
            item_type is int
            or item_type is float
            or item_type is str
            or item_type is bool
            or item is None
        ):
            return None
    if scalar is not None and not scalar.safe_for(low, high):
        return None
    kernel = _compile_plain(shape.kind, expression)
    plan.last_plain = kernel
    callback_tail = scalar.expression.kind if scalar is not None else "ref"
    return _run_plain_chunks, (
        context,
        loop.items,
        loop.output,
        cancel,
        observed,
        plan,
        kernel,
        callback_ticks,
        callback_tail,
    )


def _run_plain_chunks(
    context: Context,
    items: list[Any],
    output: list[Any],
    cancel: Any,
    observer: Any,
    plan: Any,
    kernel: Any,
    callback_ticks: int,
    callback_tail: str,
) -> list[Any]:
    """Run proven kernels with one shared set of bounded source checkpoints."""
    reverse = plan.shape.kind == "reverse"
    filtering = plan.shape.kind == "filter"
    size = len(items)
    consumed = getattr(plan, "consumed", 0)
    each = 4 if reverse else 11 + callback_ticks
    if reverse:
        if cancel is not None and cancel():
            _cancelled(context, plan.body if items else plan.base)
        context.steps += size * (6 + consumed) + (1 if items else 2)
        context.step_count = context.steps
        context.consume_depth += size * consumed
        output = []
        pending = reversed(items)
        if observer is not None:
            observer.last_tail = "list"
    else:
        pending = iter(items)
    for start in range(0, size, _CHUNK_SIZE):
        count = min(_CHUNK_SIZE, size - start)
        if reverse:
            context.consume_depth -= consumed
            if observer is not None:
                observer.last_tail = "let"
        if cancel is not None and cancel():
            node = (
                plan.shape.push
                if reverse
                else (plan.body if start == 0 else plan.shape.group)
            )
            _cancelled(context, node)
        before = len(output) if filtering else 0
        keep = kernel(islice(pending, _CHUNK_SIZE), output)
        cost = count * each
        if not reverse and start == 0:
            cost -= 2
        if filtering:
            cost += (len(output) - before) * 3
        context.steps += cost
        context.step_count = context.steps
        if reverse:
            context.consume_depth -= (count - 1) * consumed
        if observer is not None:
            observer.last_tail = (
                "ref" if reverse else "host" if not filtering or keep else callback_tail
            )
    if not reverse:
        if cancel is not None and cancel():
            _cancelled(context, plan.shape.group if items else plan.base)
        context.steps += 3 if items else 2
        context.step_count = context.steps
        if observer is not None:
            observer.last_tail = "ref"
    final = plan.final if reverse and items else plan.base_value
    context.location = context.current_location = (final.line, final.column)
    return output


@lru_cache(maxsize=128)
def _compile_plain(kind: str, expression: str) -> Any:
    """Emit only a pure for/append kernel; the shared runner owns checkpoints."""
    if kind == "map":
        source = f"""def plain_map(items, output):
    for head in items:
        output.append({expression})
"""
    elif kind == "filter":
        source = f"""def plain_filter(items, output):
    keep = False
    for head in items:
        keep = {expression}
        if keep:
            output.append(head)
    return keep
"""
    else:
        source = """def plain_reverse(items, output):
    for head in items:
        output.append(head)
"""
    namespace = {"__builtins__": {}}
    module = ast.parse(source)
    exec(compile(module, "<ctk-plain-list-loop>", "exec"), namespace)  # noqa: S102 - compiler-built AST
    function = namespace["plain_" + kind]
    function.__ctk_source__ = ast.unparse(module)
    return function
