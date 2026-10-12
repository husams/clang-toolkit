"""Shared value and execution semantics for the scripting prototype.

This module is deliberately independent of the production evaluator.  The tree
interpreter and the generated engine both use these small operations so that
their observable behaviour stays identical.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any


MIN_INT64 = -(1 << 63)
MAX_INT64 = (1 << 63) - 1


@dataclass(frozen=True, slots=True)
class Node:
    """The parser worker's immutable intermediate representation.

    Parser implementations may provide an equivalent immutable object; the
    engines intentionally use the public attributes rather than requiring this
    class by identity.
    """

    kind: str
    value: Any = None
    children: Any = ()
    line: int | None = None
    column: int | None = None


class PrototypeError(RuntimeError):
    """Base class for errors reported by either prototype engine."""


class EvaluationError(PrototypeError):
    pass


class ExecutionLimitError(PrototypeError):
    pass


class CancelledError(PrototypeError):
    pass


class Context:
    """Mutable execution state with lexical bindings and bounded execution."""

    def __init__(
        self,
        bindings: dict[str, Any] | None = None,
        functions: Mapping[str, Callable[..., Any]] | None = None,
        max_steps: int = 1_000_000,
        max_items: int = 10_000,
        cancel_hook: Callable[[], bool] | None = None,
        cancel: Callable[[], bool] | None = None,
        cancel_check: Callable[[], bool] | None = None,
        host_evaluator: Callable[[Context, Any], Any] | None = None,
        statement_observer: Callable[[Context, Any, Any], None] | None = None,
    ) -> None:
        if max_steps < 0 or max_items < 0:
            raise ValueError("execution limits must be nonnegative")
        self.bindings: dict[str, Any] = bindings if bindings is not None else {}
        self.functions: dict[str, Callable[..., Any]] = dict(functions or {})
        self.max_steps = max_steps
        self.max_items = max_items
        self.cancel_hook = cancel_hook or cancel or cancel_check
        self.host_evaluator = host_evaluator
        self.statement_observer = statement_observer
        self.output: list[Any] = []
        self.consume_depth = 0
        self.steps = 0
        self.step_count = 0
        self.current_location: tuple[int | None, int | None] = (None, None)
        self.location: tuple[int | None, int | None] = self.current_location
        self._scopes: list[dict[str, Any]] = [self.bindings]
        self.functions.setdefault("len", lambda value: _bounded_len(value, self.max_items))
        self.functions.setdefault("range", lambda *args: _bounded_range(args, self.max_items))

    @property
    def scopes(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._scopes)

    def push_scope(self, initial: Mapping[str, Any] | None = None) -> None:
        self._scopes.append(dict(initial or {}))

    def pop_scope(self) -> dict[str, Any]:
        if len(self._scopes) == 1:
            raise RuntimeError("cannot pop the root execution scope")
        return self._scopes.pop()

    def define(self, name: str, value: Any) -> Any:
        self._scopes[-1][name] = value
        return value

    def lookup_scope(self, name: str) -> dict[str, Any] | None:
        for scope in reversed(self._scopes):
            if name in scope:
                return scope
        return None

    def lookup(self, name: str, node: Any = None) -> Any:
        scope = self.lookup_scope(name)
        if scope is None:
            raise _error(self, node, f"undefined binding {name!r}")
        return scope[name]

    def assign_binding(self, name: str, value: Any, node: Any = None) -> Any:
        scope = self.lookup_scope(name)
        if scope is None:
            raise _error(self, node, f"cannot assign undefined binding {name!r}")
        scope[name] = value
        return value

    def emit(self, value: Any, node: Any = None) -> Any:
        if len(self.output) >= self.max_items:
            raise _error(self, node, "output exceeds item limit", ExecutionLimitError)
        try:
            from ..collections import snapshot_collections

            captured = snapshot_collections(value)
        except Exception:
            captured = value
        self.output.append(captured)
        return value

    def tick(self, node: Any = None) -> None:
        if node is not None:
            self.current_location = (getattr(node, "line", None), getattr(node, "column", None))
            self.location = self.current_location
        if self.cancel_hook is not None and self.cancel_hook():
            raise _error(self, node, "execution cancelled", CancelledError)
        self.steps += 1
        self.step_count = self.steps
        if self.steps > self.max_steps:
            raise _error(self, node, "execution step limit exceeded", ExecutionLimitError)


def _location(node: Any) -> str:
    line = getattr(node, "line", None)
    column = getattr(node, "column", None)
    if line is None and column is None:
        return ""
    if column is None:
        return f" at line {line}"
    return f" at line {line}, column {column}"


def _error(ctx: Context, node: Any, message: str, cls: type[PrototypeError] = EvaluationError) -> PrototypeError:
    return cls(f"{message}{_location(node)}")


def children(node: Any) -> Any:
    return getattr(node, "children", ())


def node_value(node: Any, default: Any = None) -> Any:
    value = getattr(node, "value", default)
    return default if value is None and default is not None else value


def child(node: Any, name: str, position: int | None = None, default: Any = None) -> Any:
    values = children(node)
    if isinstance(values, Mapping):
        if name in values:
            return values[name]
        if position is None:
            return default
        try:
            return tuple(values.values())[position]
        except IndexError:
            return default
    if position is None:
        return default
    if hasattr(values, "kind") and position == 0:
        return values
    try:
        return values[position]
    except (IndexError, KeyError, TypeError):
        return default


def child_values(node: Any) -> tuple[Any, ...]:
    values = children(node)
    if isinstance(values, Mapping):
        for field in ("args", "items", "elements", "entries", "statements", "children"):
            selected = values.get(field)
            if isinstance(selected, (tuple, list)):
                return tuple(selected)
        return tuple(values.values())
    if isinstance(values, tuple):
        return values
    if isinstance(values, list):
        return tuple(values)
    return (values,) if values is not None else ()


def _kind(node: Any) -> str:
    return str(getattr(node, "kind", ""))


def _name(node: Any) -> str:
    value = node_value(node)
    if isinstance(value, str):
        return value
    name = child(node, "name", 0)
    if isinstance(name, str):
        return name
    raise EvaluationError(f"node {_kind(node)!r} has no name")


def _expr(node: Any, position: int = 0, name: str = "expr") -> Any:
    result = child(node, name, position)
    if result is None and isinstance(children(node), Mapping):
        result = child(node, name, None)
    if result is None:
        raise EvaluationError(f"node {_kind(node)!r} has no {name}")
    return result


def _as_bool(ctx: Context, value: Any, node: Any) -> bool:
    if type(value) is not bool:
        raise _error(ctx, node, f"condition requires bool, got {type(value).__name__}")
    return value


def _finite(ctx: Context, value: float, node: Any) -> float:
    if not math.isfinite(value):
        raise _error(ctx, node, "non-finite floating-point result")
    return value


def _int(ctx: Context, value: int, node: Any) -> int:
    if value < MIN_INT64 or value > MAX_INT64:
        raise _error(ctx, node, "signed 64-bit integer overflow")
    return value


def _numeric_pair(ctx: Context, left: Any, right: Any, node: Any) -> tuple[int | float, int | float]:
    if type(left) not in (int, float) or type(right) not in (int, float):
        raise _error(ctx, node, f"numeric operands required, got {type(left).__name__} and {type(right).__name__}")
    if type(left) is int:
        _int(ctx, left, node)
    if type(right) is int:
        _int(ctx, right, node)
    if isinstance(left, float) and not math.isfinite(left) or isinstance(right, float) and not math.isfinite(right):
        raise _error(ctx, node, "non-finite floating-point operand")
    if type(left) is int and type(right) is float:
        converted = float(left)
        if not math.isfinite(converted) or int(converted) != left:
            raise _error(ctx, node, "integer-to-float conversion is not lossless")
        left = converted
    elif type(left) is float and type(right) is int:
        converted = float(right)
        if not math.isfinite(converted) or int(converted) != right:
            raise _error(ctx, node, "integer-to-float conversion is not lossless")
        right = converted
    return left, right


def _binary(ctx: Context, op: str, left: Any, right: Any, node: Any) -> Any:
    if op in {"and", "or"}:
        return _as_bool(ctx, left, node) and _as_bool(ctx, right, node) if op == "and" else _as_bool(ctx, left, node) or _as_bool(ctx, right, node)
    if op in {"==", "!="}:
        if type(left) is bool or type(right) is bool:
            result = type(left) is type(right) and left == right
        elif type(left) in (int, float) and type(right) in (int, float):
            left, right = _numeric_pair(ctx, left, right, node)
            result = left == right
        elif left is None or right is None or type(left) is type(right) and isinstance(left, (str, type(None))):
            result = left == right
        else:
            raise _error(ctx, node, "equality supports scalar values only")
        return not result if op == "!=" else result
    if op in {"<", "<=", ">", ">="}:
        if isinstance(left, str) and isinstance(right, str):
            pass
        else:
            left, right = _numeric_pair(ctx, left, right, node)
        return {"<": left < right, "<=": left <= right, ">": left > right, ">=": left >= right}[op]
    left, right = _numeric_pair(ctx, left, right, node)
    if op in {"+", "-", "*"}:
        if type(left) is int and type(right) is int:
            return _int(ctx, {"+": left + right, "-": left - right, "*": left * right}[op], node)
        return _finite(ctx, {"+": left + right, "-": left - right, "*": left * right}[op], node)
    if op == "/":
        if right == 0:
            raise _error(ctx, node, "division by zero")
        return _finite(ctx, left / right, node)
    if op == "%":
        if type(left) is not int or type(right) is not int:
            raise _error(ctx, node, "remainder requires integer operands")
        if right == 0:
            raise _error(ctx, node, "remainder by zero")
        quotient = (abs(left) // abs(right)) * (-1 if (left < 0) != (right < 0) else 1)
        return _int(ctx, left - quotient * right, node)
    raise _error(ctx, node, f"unknown binary operator {op!r}")


def _unary(ctx: Context, op: str, value: Any, node: Any) -> Any:
    if op == "not":
        return not _as_bool(ctx, value, node)
    if op not in {"+", "-"} or type(value) not in (int, float):
        raise _error(ctx, node, f"invalid unary operation {op!r}")
    if type(value) is int:
        return _int(ctx, value if op == "+" else -value, node)
    return _finite(ctx, value if op == "+" else -value, node)


def _bounded_len(value: Any, maximum: int) -> int:
    try:
        result = len(value)
    except TypeError as error:
        raise EvaluationError(f"len requires a sized value, got {type(value).__name__}") from error
    if result > maximum:
        raise ExecutionLimitError("len result exceeds item limit")
    return result


def _bounded_range(args: tuple[Any, ...], maximum: int) -> list[int]:
    if not 1 <= len(args) <= 3 or any(type(arg) is not int for arg in args):
        raise EvaluationError("range accepts one to three integer arguments")
    if any(arg < MIN_INT64 or arg > MAX_INT64 for arg in args):
        raise EvaluationError("range arguments must be signed 64-bit integers")
    values = range(*args)
    try:
        count = len(values)
    except OverflowError as error:
        raise ExecutionLimitError("range result exceeds item limit") from error
    if count > maximum:
        raise ExecutionLimitError("range result exceeds item limit")
    return list(values)


def _ensure_insertable(ctx: Context, target: list[Any] | dict[str, Any], value: Any, node: Any) -> None:
    try:
        from ..collections import ensure_insertable

        ensure_insertable(target, value)
    except Exception as error:
        raise _error(ctx, node, str(error)) from error


def _ensure_dict_capacity(ctx: Context, target: dict[str, Any], key: str, node: Any) -> None:
    if key not in target and len(target) >= ctx.max_items:
        raise _error(ctx, node, "dictionary exceeds item limit", ExecutionLimitError)


def iterable_value(ctx: Context, node: Any, value: Any) -> Any:
    try:
        return iter(value)
    except TypeError as error:
        raise _error(ctx, node, f"foreach requires an iterable, got {type(value).__name__}") from error


def property_value(value: Any, name: str) -> Any:
    """Read a safe property, including CTK's descriptor-backed semantic views."""
    try:
        from ..references import property_value as ctk_property_value

        return ctk_property_value(value, name)
    except Exception:
        if isinstance(value, Mapping) and name in value:
            return value[name]
        if isinstance(value, (list, tuple, str)) and name == "length":
            return len(value)
        if isinstance(value, (list, tuple, str)) and name == "isEmpty":
            return len(value) == 0
        raise


def index_value(value: Any, key: Any, ctx: Context, node: Any) -> Any:
    if type(key) is bool:
        raise _error(ctx, node, "boolean is not a valid index")
    try:
        if isinstance(value, Mapping):
            return value[key]
        if isinstance(value, (list, tuple, str)):
            if type(key) is not int:
                raise TypeError("sequence index must be an integer")
            return value[key]
        from ..references import index_value as semantic_index_value

        return semantic_index_value(value, key)
    except Exception as error:
        raise _error(ctx, node, f"invalid index {key!r} for {type(value).__name__}") from error


def _entry_nodes(node: Any) -> tuple[Any, ...]:
    values = children(node)
    if isinstance(values, Mapping):
        if "entries" in values:
            entries = values["entries"]
            return tuple(entries) if isinstance(entries, (tuple, list)) else (entries,)
        # A parser may preserve dictionary keys directly.  Turn each pair into
        # a tiny entry-like tuple; _entry_key_value accepts that representation.
        if not any(key in values for key in ("args", "items", "elements", "statements", "children")):
            return tuple((key, value) for key, value in values.items())
        return tuple(values.values())
    return child_values(node)


def _entry_key_value(entry: Any) -> tuple[Any, Any]:
    if isinstance(entry, tuple) and len(entry) == 2 and not hasattr(entry, "kind"):
        return entry
    key = node_value(entry)
    expr = child(entry, "expr", 0)
    if expr is None:
        vals = child_values(entry)
        if len(vals) >= 2:
            key, expr = vals[0], vals[1]
        elif vals:
            expr = vals[0]
    if hasattr(key, "kind"):
        return key, expr
    return key, expr


def _resolve_target(ctx: Context, target: Any, operator: str) -> tuple[Callable[[], Any], Callable[[Any], Any]]:
    kind = _kind(target)
    if kind == "ref":
        name = _name(target)
        scope = ctx.lookup_scope(name)
        if scope is None:
            raise _error(ctx, target, f"cannot assign undefined binding {name!r}")
        return lambda: scope[name], lambda value: scope.__setitem__(name, value)
    if kind == "get":
        base = eval_expr(ctx, _expr(target, 0, "base"))
        key = str(node_value(target, child(target, "property", None)))
        if not isinstance(base, dict):
            raise _error(ctx, target, "dot assignment requires a mutable dictionary")
        if operator != "=" and key not in base:
            raise _error(ctx, target, f"undefined dictionary key {key!r}")
        return (lambda: base[key] if key in base else None), lambda value: (_ensure_dict_capacity(ctx, base, key, target), _ensure_insertable(ctx, base, value, target), base.__setitem__(key, value))[2]
    if kind != "index":
        raise _error(ctx, target, "assignment target must be a binding or mutable index")
    base_node = _expr(target, 0, "base")
    key_node = _expr(target, 1, "key")
    base = eval_expr(ctx, base_node)
    key = eval_expr(ctx, key_node)
    if isinstance(base, list):
        if type(key) is not int or key < 0 or key >= len(base):
            raise _error(ctx, target, "list assignment index out of range")
        return lambda: base[key], lambda value: (_ensure_insertable(ctx, base, value, target), base.__setitem__(key, value))[1]
    if isinstance(base, dict):
        try:
            present = key in base
        except TypeError as error:
            raise _error(ctx, target, f"dictionary assignment key is not hashable: {type(key).__name__}") from error
        if type(key) is not str:
            raise _error(ctx, target, "dictionary assignment keys must be strings")
        if not present and operator != "=":
            raise _error(ctx, target, f"undefined dictionary key {key!r}")
        return (lambda: base[key] if key in base else None), lambda value: (_ensure_dict_capacity(ctx, base, key, target), _ensure_insertable(ctx, base, value, target), base.__setitem__(key, value))[2]
    raise _error(ctx, target, "assignment requires a mutable list or dictionary")


def host_value(ctx: Context, node: Any) -> Any:
    """Execute a validated CTK operation without interpreting script control flow."""
    if ctx.host_evaluator is None:
        raise _error(ctx, node, "no CTK host evaluator is configured")
    return ctx.host_evaluator(ctx, node)


def observe_statement(ctx: Context, node: Any, value: Any) -> None:
    if ctx.statement_observer is not None:
        ctx.statement_observer(ctx, node, value)


def consumed_value(ctx: Context, thunk: Callable[[], Any]) -> Any:
    ctx.consume_depth += 1
    try:
        return thunk()
    finally:
        ctx.consume_depth -= 1


def eval_expr(ctx: Context, node: Any) -> Any:
    """Evaluate one expression node; shared by both execution engines."""
    ctx.tick(node)
    kind = _kind(node)
    if kind == "literal":
        value = node_value(node)
        if type(value) is int:
            return _int(ctx, value, node)
        if type(value) is float:
            return _finite(ctx, value, node)
        return value
    if kind == "ref":
        return ctx.lookup(_name(node), node)
    if kind == "list":
        if len(child_values(node)) > ctx.max_items:
            raise _error(ctx, node, "list exceeds item limit", ExecutionLimitError)
        values = [eval_expr(ctx, item) for item in child_values(node)]
        return values
    if kind == "dict":
        if len(_entry_nodes(node)) > ctx.max_items:
            raise _error(ctx, node, "dictionary exceeds item limit", ExecutionLimitError)
        result: dict[Any, Any] = {}
        for entry in _entry_nodes(node):
            key, value_node = _entry_key_value(entry)
            if hasattr(key, "kind"):
                key = eval_expr(ctx, key)
            if type(key) is not str:
                raise _error(ctx, entry, "dictionary keys must be strings")
            if value_node is None:
                raise _error(ctx, entry, "dictionary entry has no value")
            result[key] = eval_expr(ctx, value_node)
        return result
    if kind == "get":
        base = _expr(node, 0, "base")
        value = eval_expr(ctx, base)
        name = str(node_value(node, child(node, "property", None)))
        try:
            return property_value(value, name)
        except PrototypeError:
            raise
        except Exception as error:
            raise _error(ctx, node, f"property {name!r} is unavailable on {type(value).__name__}: {error}") from error
    if kind == "index":
        return index_value(eval_expr(ctx, _expr(node, 0, "base")), eval_expr(ctx, _expr(node, 1, "key")), ctx, node)
    if kind == "consume":
        return consumed_value(ctx, lambda: eval_expr(ctx, child_values(node)[0]))
    if kind == "host":
        return host_value(ctx, node)
    if kind == "call":
        name = _name(node)
        function = ctx.functions.get(name)
        if function is None:
            raise _error(ctx, node, f"unregistered host function {name!r}")
        args = [eval_expr(ctx, arg) for arg in child_values(node)]
        try:
            return function(*args)
        except PrototypeError as error:
            if _location(node) and _location(node) not in str(error):
                raise _error(ctx, node, str(error), type(error)) from error
            raise
        except Exception as error:
            raise _error(ctx, node, f"host function {name!r} failed: {error}") from error
    if kind == "foreach":
        return eval_foreach(ctx, node, ticked=True)
    if kind == "binary":
        op = str(node_value(node))
        left_node = _expr(node, 0, "lhs")
        left = eval_expr(ctx, left_node)
        if op == "and":
            if not _as_bool(ctx, left, node):
                return False
            return _binary(ctx, op, left, eval_expr(ctx, _expr(node, 1, "rhs")), node)
        if op == "or":
            if _as_bool(ctx, left, node):
                return True
            return _binary(ctx, op, left, eval_expr(ctx, _expr(node, 1, "rhs")), node)
        return _binary(ctx, op, left, eval_expr(ctx, _expr(node, 1, "rhs")), node)
    if kind == "unary":
        return _unary(ctx, str(node_value(node)), eval_expr(ctx, _expr(node, 0, "expr")), node)
    if kind == "conditional":
        condition = eval_expr(ctx, _expr(node, 0, "condition"))
        selected = _expr(node, 1 if _as_bool(ctx, condition, node) else 2, "block")
        ctx.push_scope()
        try:
            return eval_block(ctx, selected, scoped=False)
        finally:
            ctx.pop_scope()
    if kind == "block":
        return eval_block(ctx, node)
    raise _error(ctx, node, f"node kind {kind!r} is not an expression")


def eval_assign(ctx: Context, node: Any) -> Any:
    ctx.tick(node)
    target = _expr(node, 0, "target")
    rhs = _expr(node, 1, "expr")
    operator = str(node_value(node, "="))
    getter, setter = _resolve_target(ctx, target, operator)
    if operator == "=":
        new_value = eval_expr(ctx, rhs)
    else:
        old = getter()
        value = eval_expr(ctx, rhs)
        new_value = _binary(ctx, operator[:-1], old, value, node)
    setter(new_value)
    return new_value


def eval_statement(ctx: Context, node: Any) -> Any:
    kind = _kind(node)
    if kind == "observe":
        statement = child_values(node)[0]
        value = eval_statement(ctx, statement)
        observe_statement(ctx, statement, value)
        return value
    if kind == "let":
        ctx.tick(node)
        name = _name(node)
        value = eval_expr(ctx, _expr(node, 0, "expr"))
        return ctx.define(name, value)
    if kind == "assign":
        return eval_assign(ctx, node)
    if kind == "print":
        ctx.tick(node)
        value = eval_expr(ctx, _expr(node, 0, "expr"))
        return ctx.emit(value, node)
    if kind == "foreach":
        return eval_foreach(ctx, node)
    if kind == "block":
        return eval_block(ctx, node)
    if kind in {"conditional", "list", "dict", "literal", "ref", "get", "index", "call", "binary", "unary", "host"}:
        return eval_expr(ctx, node)
    raise _error(ctx, node, f"unknown statement node {kind!r}")


def eval_block(ctx: Context, node: Any, scoped: bool = True) -> Any:
    ctx.tick(node)
    if scoped:
        ctx.push_scope()
    try:
        result = None
        statements = child(node, "statements", 0, ()) if isinstance(children(node), Mapping) else child_values(node)
        if not isinstance(statements, (tuple, list)):
            statements = (statements,)
        for statement in statements:
            result = eval_statement(ctx, statement)
        return result
    finally:
        if scoped:
            ctx.pop_scope()


def eval_foreach(ctx: Context, node: Any, *, ticked: bool = False) -> list[Any]:
    if not ticked:
        ctx.tick(node)
    name = _name(node)
    iterable = eval_expr(ctx, _expr(node, 0, "iterable"))
    body = _expr(node, 1, "block")
    iterator = iterable_value(ctx, node, iterable)
    result: list[Any] = []
    for item in iterator:
        if len(result) >= ctx.max_items:
            raise _error(ctx, node, "foreach result exceeds item limit", ExecutionLimitError)
        ctx.tick(node)
        ctx.push_scope({name: item})
        try:
            result.append(eval_block(ctx, body, scoped=False))
        finally:
            ctx.pop_scope()
    return result


def eval_program(ctx: Context, program: Any) -> Any:
    ctx.tick(program)
    if _kind(program) == "program":
        statements = child(program, "statements", 0, ()) if isinstance(children(program), Mapping) else child_values(program)
    else:
        statements = (program,)
    result = None
    for statement in statements:
        result = eval_statement(ctx, statement)
    return result
