"""Immutable patterns lowered once to Python length/index checks."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Callable


@dataclass(frozen=True)
class ListPattern:
    elements: tuple[Any, ...]

    def __str__(self) -> str:
        return "[" + ", ".join(format_pattern(item) for item in self.elements) + "]"


@dataclass(frozen=True)
class ConsPattern:
    head: Any
    tail: Any

    def __str__(self) -> str:
        head = format_pattern(self.head)
        if isinstance(self.head, ConsPattern):
            head = "(" + head + ")"
        return head + " : " + format_pattern(self.tail)


def pattern_names(pattern: Any) -> tuple[str, ...]:
    if isinstance(pattern, str):
        return () if pattern == "_" else (pattern,)
    parts = (pattern.head, pattern.tail) if isinstance(pattern, ConsPattern) else (
        pattern.elements if isinstance(pattern, ListPattern) else pattern
    )
    return tuple(name for item in parts for name in pattern_names(item))


def format_pattern(pattern: Any) -> str:
    if isinstance(pattern, (str, ConsPattern, ListPattern)):
        return str(pattern)
    return "(" + ", ".join(format_pattern(item) for item in pattern) + ("," if len(pattern) == 1 else "") + ")"


@lru_cache(maxsize=256)
def compile_matcher(patterns: tuple[Any, ...], internal: bool = False) -> Callable[[list[Any]], dict[str, Any] | None]:
    """Check every shape before binding; only successful, named tails copy."""
    checks: list[ast.stmt] = []
    bindings: dict[str, ast.expr] = {}

    def call(name: str, *args: ast.expr) -> ast.Call:
        return ast.Call(ast.Name(name, ast.Load()), list(args), [])

    def check(condition: ast.expr) -> None:
        checks.append(ast.If(ast.UnaryOp(ast.Not(), condition), [ast.Return(ast.Constant(None))], []))

    def safe(value: ast.expr) -> ast.expr:
        return call("_pattern_value", value, ast.Name("arena", ast.Load())) if internal else value

    def index(value: ast.expr, ordinal: int) -> ast.expr:
        return ast.Subscript(safe(value), ast.Constant(ordinal), ast.Load())

    def emit(pattern: Any, value: ast.expr, offset: int = 0, region: bool = False) -> None:
        if isinstance(pattern, str):
            if pattern != "_":
                bindings[pattern] = (call("_tail", value, ast.Constant(offset), ast.Name("arena", ast.Load())) if internal else ast.Subscript(value, ast.Slice(ast.Constant(offset), None, None), ast.Load())) if region else value
            return
        if isinstance(pattern, ConsPattern):
            check(call("_is_list", safe(value)) if internal else call("isinstance", value, ast.Name("list", ast.Load())))
            check(ast.Compare(call("len", safe(value)), [ast.Gt()], [ast.Constant(offset)]))
            emit(pattern.head, index(value, offset))
            emit(pattern.tail, value, offset + 1, True)
            return
        is_list = isinstance(pattern, ListPattern)
        elements = pattern.elements if is_list else pattern
        if region and not is_list:
            check(ast.Constant(False))
            return
        check(call("_is_list", safe(value)) if internal and is_list else call("isinstance", safe(value), ast.Name("list" if is_list else "tuple", ast.Load())))
        check(ast.Compare(call("len", safe(value)), [ast.Eq()], [ast.Constant(offset + len(elements))]))
        for ordinal, item in enumerate(elements, offset):
            emit(item, index(value, ordinal))

    check(ast.Compare(call("len", ast.Name("values", ast.Load())), [ast.Eq()], [ast.Constant(len(patterns))]))
    for ordinal, pattern in enumerate(patterns):
        emit(pattern, index(ast.Name("values", ast.Load()), ordinal))
    body = [*checks, ast.Return(ast.Dict([ast.Constant(name) for name in bindings], list(bindings.values())))]
    module = ast.fix_missing_locations(ast.Module([
        ast.FunctionDef("match", ast.arguments([], [ast.arg(name) for name in (("values", "arena") if internal else ("values",))], None, [], [], None, []), body, [])
    ], []))
    namespace = {"__builtins__": {}, "len": len, "isinstance": isinstance, "list": list, "tuple": tuple}
    if internal:
        from .list_recursion import _is_list, _pattern_value, _tail
        namespace.update(_is_list=_is_list, _pattern_value=_pattern_value, _tail=_tail)
    exec(compile(module, "<ctk-pattern>", "exec"), namespace)
    function = namespace["match"]
    function.__ctk_source__ = ast.unparse(module)
    return function


def define_pattern(context: Any, node: Any, value: Any) -> Any:
    from .semantics import _error

    bindings = compile_matcher((node.value,))([value])
    if bindings is None:
        raise _error(context, node, f"destructuring pattern {format_pattern(node.value)} does not match")
    for name, item in bindings.items():
        context.define(name, item)
    return value
