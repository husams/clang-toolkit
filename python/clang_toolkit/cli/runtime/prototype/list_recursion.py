"""Compile direct list recursion to resumable Python functions and an explicit loop."""

from __future__ import annotations

import ast
import copy
from dataclasses import dataclass, field
from typing import Any, Callable
from collections.abc import Generator
from weakref import WeakSet

from .patterns import ConsPattern, ListPattern, compile_matcher, pattern_names
from .semantics import (
    Context,
    Node,
    ExecutionLimitError,
    _as_bool,
    _binary,
    _error,
    observe_statement,
)


def observer_allows_optimization(context: Context) -> bool:
    observer = context.statement_observer
    if observer is None:
        return True
    from .repl import ReplSession

    # Arbitrary runtime hooks may inspect/mutate each logical frame and tail.
    return getattr(observer, "__func__", None) is ReplSession.observe


class _Cursor:
    """An internal logical tail; materialization preserves shallow-list identity."""

    def __init__(
        self,
        items: list[Any],
        start: int,
        stop: int,
        arena: _Arena,
        private: bool = False,
    ) -> None:
        self.items, self.start, self.stop = items, start, stop
        self.private, self.owned, self.arena = private, None, arena
        if not private:
            arena.public.add(self)

    def __len__(self) -> int:
        return len(self.owned) if self.owned is not None else self.stop - self.start

    def __getitem__(self, index: int) -> Any:
        if index < 0:
            index += len(self)
        if not 0 <= index < len(self):
            raise IndexError(index)
        return (
            self.owned[index]
            if self.owned is not None
            else self.items[self.start + index]
        )

    def materialize(self) -> list[Any]:
        if self.owned is None:
            self.owned = self.items[self.start : self.stop]
            self.arena.public.discard(self)
        return self.owned


class _Arena:
    def __init__(self) -> None:
        self.public = WeakSet()

    def freeze(self) -> None:
        # One shallow snapshot per exposed backing, shared by all logical tails.
        # Nested objects remain shared, just as with ordinary Python list slices.
        snapshots = {}
        for cursor in list(self.public):
            key = id(cursor.items)
            if key not in snapshots:
                snapshots[key] = cursor.items.copy()
            cursor.items = snapshots[key]
            cursor.private = True
        self.public.clear()


def _is_list(value: Any) -> bool:
    return isinstance(value, (list, _Cursor))


def _pattern_value(value: Any, arena: _Arena) -> Any:
    kind = type(value)
    if kind is not list and kind is not tuple and kind is not _Cursor:
        # Subclass length/index/type hooks may mutate another matched argument.
        arena.freeze()
    return value


def _tail(value: Any, offset: int, arena: _Arena) -> Any:
    if isinstance(value, _Cursor) and value.owned is None:
        return _Cursor(
            value.items, value.start + offset, value.stop, arena, value.private
        )
    items = value.materialize() if isinstance(value, _Cursor) else value
    if type(items) is not list:
        # Preserve subclass slicing hooks instead of applying plain-list sharing.
        arena.freeze()
        return items[offset:]
    return _Cursor(items, offset, len(items), arena)


def _materialize(value: Any) -> Any:
    return value.materialize() if isinstance(value, _Cursor) else value


def _references(node: Node, context: Context) -> set[str]:
    from lark import Token

    result = set()

    def visit(item: Any) -> None:
        if getattr(item, "kind", None) == "ref":
            result.add(item.value)
        if getattr(item, "kind", None) == "host":
            visit(item.value[0])
        for child in getattr(item, "children", ()):
            visit(child)
        if isinstance(item, Token):
            if item.type in {"NAME", "CNAME"}:
                result.add(str(item))
            template = context.string_templates.get(str(item))
            if template is not None:
                for expression in template.expressions:
                    visit(expression)

    visit(node)
    return result


def _leaf(
    context: Context,
    arena: _Arena,
    function: Callable[[Context], Any],
    names: set[str],
    effect: bool,
    raw: bool,
) -> Any:
    if effect:
        arena.freeze()
    if not raw:
        for name in names:
            scope = context.lookup_scope(name)
            if scope is not None and isinstance(scope[name], _Cursor):
                scope[name] = scope[name].materialize()
    return function(context)


@dataclass
class _Request:
    arguments: list[Any]
    node: Any
    observations: tuple[Any, ...] = ()


@dataclass
class _Frame:
    generator: Generator[_Request, Any, Any]
    scopes: list[dict[str, Any]]
    observations: list[Any] = field(default_factory=list)


@dataclass
class RecursiveListProgram:
    functions: tuple[Any, ...]
    matchers: tuple[Any, ...]
    grouped: bool
    __ctk_source__: str

    def run(
        self, context: Context, arguments: list[Any], owner: Any, call_node: Node
    ) -> Any:
        arena, stack = _Arena(), []
        saved_scopes = list(context._scopes)
        current = None

        def frame(
            values: list[Any], location: Node, observations: list[Any] | None = None
        ) -> _Frame:
            for matcher, function in zip(self.matchers, self.functions):
                if self.grouped:
                    context.tick(owner.body)
                bindings = matcher(values, arena)
                if bindings is not None:
                    # Capture slice semantics before any body operation or runtime hook.
                    arena.freeze()
                    scopes = [*owner.scopes, {owner.name: owner, **bindings}]
                    context._scopes[:] = scopes
                    return _Frame(
                        function(context, arena, owner), scopes, observations or []
                    )
            raise _error(context, location, f"no matching clause for {owner.name}")

        try:
            current = frame(arguments, call_node)
            result = None
            while True:
                context._scopes[:] = current.scopes
                try:
                    request = current.generator.send(result)
                except StopIteration as done:
                    result = done.value
                    if isinstance(result, _Request):
                        pending = current.observations
                        if result.observations:
                            key = tuple(id(node) for node in result.observations)
                            if pending and pending[-1][0] == key:
                                pending[-1][2] += 1
                            else:
                                pending.append([key, result.observations, 1])
                        current = frame(result.arguments, result.node, pending)
                        result = None
                        continue
                    for _, nodes, count in reversed(current.observations):
                        for _ in range(count):
                            for node in nodes:
                                observe_statement(context, node, result)
                    if not stack:
                        return _materialize(result)
                    current = stack.pop()
                else:
                    current.scopes = list(context._scopes)
                    stack.append(current)
                    if len(stack) > context.max_items:
                        raise _error(
                            context,
                            request.node,
                            "continuation stack exceeds item limit",
                            ExecutionLimitError,
                        )
                    current = frame(request.arguments, request.node)
                    result = None
        finally:
            if current is not None:
                for suspended in [current, *reversed(stack)]:
                    context._scopes[:] = suspended.scopes
                    suspended.generator.close()
            context._scopes[:] = saved_scopes


class _Unsupported(Exception):
    pass


class _Emitter:
    def __init__(self, name: str, context: Context) -> None:
        self.name, self.namespace, self.context = name, {}, context
        self.count = 0

    def value(self, value: Any) -> str:
        name = f"_v{len(self.namespace)}"
        self.namespace[name] = value
        return name

    def fresh(self) -> str:
        self.count += 1
        return f"_r{self.count}"

    def recursive(self, node: Node) -> bool:
        if node.kind in {"inline_runnable", "runnable", "clause_runnable"}:
            return False
        return (node.kind == "call" and node.value == self.name) or any(
            self.recursive(child) for child in node.children
        )

    def effect(self, node: Node) -> bool:
        return node.kind in {"call", "invoke", "host", "pipe", "assign"} or any(
            self.effect(child) for child in node.children
        )

    def leaf(self, node: Node, raw: bool) -> str:
        from .compiler import compile_program

        function = compile_program(node)
        module = copy.deepcopy(function.__ctk_ast__)
        # compile_program adds a submission tick; an in-function island has none.
        module.body[-1].body.pop(0)
        namespace = dict(function.__globals__)
        exec(compile(module, "<ctk-recursive-island>", "exec"), namespace)
        return f"_leaf(context, arena, {self.value(namespace['_ctk_compiled_program'])}, {self.value(_references(node, self.context))}, {self.effect(node)!r}, {raw!r})"

    def emit(
        self,
        node: Node,
        lines: list[str],
        indent: int = 1,
        tail: bool = False,
        observations: tuple[Node, ...] = (),
    ) -> str:
        def put(code: str) -> None:
            lines.append("    " * indent + code)

        result = self.fresh()
        kind, n = node.kind, self.value(node)
        if not self.recursive(node):
            put(f"{result} = {self.leaf(node, False)}")
            return result
        if kind == "observe":
            statement = node.children[0]
            result = self.emit(
                statement, lines, indent, tail, (statement, *observations)
            )
            put(f"_observe(context, {self.value(statement)}, {result})")
        elif kind in {"block", "program"}:
            put(f"context.tick({n})")
            put(f"{result} = None")
            for index, statement in enumerate(node.children):
                result = self.emit(
                    statement,
                    lines,
                    indent,
                    tail and index == len(node.children) - 1,
                    observations,
                )
        elif kind == "consume":
            put(f"context.tick({n})")
            put("context.consume_depth += 1")
            put("try:")
            result = self.emit(node.children[0], lines, indent + 1, tail, observations)
            put("finally:")
            lines.append("    " * (indent + 1) + "context.consume_depth -= 1")
        elif kind == "conditional":
            put(f"context.tick({n})")
            condition = self.emit(node.children[0], lines, indent)
            put(f"if _bool(context, {condition}, {n}):")
            for index, branch in enumerate(node.children[1:]):
                if index:
                    put("else:")
                lines.append("    " * (indent + 1) + "context.push_scope()")
                lines.append("    " * (indent + 1) + "try:")
                selected = self.emit(branch, lines, indent + 2, tail, observations)
                lines.append("    " * (indent + 2) + f"{result} = {selected}")
                lines.append("    " * (indent + 1) + "finally:")
                lines.append("    " * (indent + 2) + "context.pop_scope()")
        elif kind == "binary":
            put(f"context.tick({n})")
            left = self.emit(node.children[0], lines, indent)
            if node.value in {"and", "or"}:
                put(f"{result} = _bool(context, {left}, {n})")
                test = result if node.value == "and" else f"not {result}"
                put(f"if {test}:")
                right = self.emit(node.children[1], lines, indent + 1)
                lines.append(
                    "    " * (indent + 1) + f"{result} = _bool(context, {right}, {n})"
                )
            else:
                right = self.emit(node.children[1], lines, indent)
                put(
                    f"{result} = _binary(context, {node.value!r}, {left}, {right}, {n})"
                )
        elif kind == "call":
            if any(child.kind == "keyword_arg" for child in node.children):
                raise _Unsupported()
            put(f"context.tick({n})")
            callee = self.fresh()
            if node.value != self.name:
                put("arena.freeze()")
            put(f"{callee} = _callee(context, {n}, {node.value!r})")
            if node.value == self.name:
                put(f"if {callee} is not owner:")
                lines.append("    " * (indent + 1) + "arena.freeze()")
            put(
                f"_preflight(context, {n}, {node.value!r}, {callee}, {len(node.children)}, ())"
            )
            arguments = []
            for child in node.children:
                if node.value == self.name and child.kind == "ref":
                    var = self.fresh()
                    put(f"{var} = {self.leaf(child, True)}")
                else:
                    var = self.emit(child, lines, indent)
                arguments.append(var)
            args = "[" + ", ".join(arguments) + "]"
            if node.value == self.name:
                put(f"if {callee} is owner:")
                if tail:
                    lines.append(
                        "    " * (indent + 1)
                        + f"return _Request({args}, {n}, {self.value(observations)})"
                    )
                else:
                    lines.append(
                        "    " * (indent + 1)
                        + f"{result} = yield _Request({args}, {n})"
                    )
                put("else:")
                lines.append("    " * (indent + 1) + "arena.freeze()")
                lines.append(
                    "    " * (indent + 1)
                    + f"{result} = _ready(context, {n}, {callee}, [_materialize(item) for item in {args}], {{}})"
                )
            else:
                put(f"{result} = _ready(context, {n}, {callee}, {args}, {{}})")
        elif kind in {"list", "tuple"}:
            put(f"context.tick({n})")
            put(f"_capacity(context, {n}, {len(node.children)})")
            values = [self.emit(child, lines, indent) for child in node.children]
            expression = "[" + ", ".join(values) + "]"
            put(
                f"{result} = {expression if kind == 'list' else 'tuple(' + expression + ')'}"
            )
        elif kind in {"let", "destructure", "print"}:
            put(f"context.tick({n})")
            value = self.emit(node.children[0], lines, indent)
            if kind == "let":
                put(f"{result} = context.define({node.value!r}, {value})")
            elif kind == "print":
                put(f"{result} = context.emit({value}, {n})")
            else:
                put(f"{result} = _define_pattern(context, {n}, {value})")
        else:
            raise _Unsupported()
        return result


def _callee(context: Context, node: Node, name: str) -> Any:
    present, value = context.binding_state(name, node)
    if not present:
        value = context.functions.get(name)
    if not present and value is None:
        raise _error(context, node, f"unregistered host function {name!r}")
    from .runnables import _current_filter_callable

    return _current_filter_callable(context, value)


def _capacity(context: Context, node: Node, count: int) -> None:
    if count > context.max_items:
        raise _error(context, node, "list exceeds item limit", ExecutionLimitError)


def compile_list_recursion(node: Node, context: Context) -> RecursiveListProgram | None:
    """Lower supported direct self calls; unsupported control retains normal execution."""
    from .patterns import define_pattern
    from .runnables import _preflight, invoke_prepared

    grouped = node.kind == "clause_runnable"
    name = node.value if grouped else node.value[0]
    clauses = node.children if grouped else (node,)
    if name == "<inline>":
        return None
    patterns = [clause.value[1] for clause in clauses]
    if not any(
        isinstance(pattern, (ConsPattern, ListPattern))
        for params in patterns
        for pattern in params
    ):
        return None
    if any(name in pattern_names(pattern) for params in patterns for pattern in params):
        return None
    emitter = _Emitter(name, context)
    if not any(emitter.recursive(clause.children[0]) for clause in clauses):
        return None

    def shadowed(item: Node) -> bool:
        if (
            (item.kind == "runnable" and item.value[0] == name)
            or (
                item.kind == "assign"
                and item.children[0].kind == "ref"
                and item.children[0].value == name
            )
            or (
                item.kind in {"let", "destructure"}
                and name in pattern_names(item.value)
            )
        ):
            return True
        return any(shadowed(child) for child in item.children)

    if any(
        len(clause.children) > 1 or shadowed(clause.children[0]) for clause in clauses
    ):
        return None
    source = []
    try:
        for index, clause in enumerate(clauses):
            source.append(f"def _step{index}(context, arena, owner):")
            source.extend(["    if False:", "        yield None"])
            result = emitter.emit(clause.children[0], source, tail=True)
            source.append(f"    return {result}")
    except _Unsupported:
        return None
    text = "\n".join(source)
    namespace = {
        "__builtins__": {},
        **emitter.namespace,
        "_leaf": _leaf,
        "_Request": _Request,
        "_observe": observe_statement,
        "_bool": _as_bool,
        "_binary": _binary,
        "_callee": _callee,
        "_preflight": _preflight,
        "_ready": invoke_prepared,
        "_capacity": _capacity,
        "tuple": tuple,
        "_define_pattern": define_pattern,
        "_materialize": _materialize,
    }
    exec(compile(ast.parse(text), "<ctk-list-continuations>", "exec"), namespace)
    return RecursiveListProgram(
        tuple(namespace[f"_step{i}"] for i in range(len(clauses))),
        tuple(compile_matcher(params, internal=True) for params in patterns),
        grouped,
        text,
    )
