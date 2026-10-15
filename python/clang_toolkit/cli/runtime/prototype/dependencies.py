"""Inspect reachable callable bodies before console/batch admission."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator

from lark import Token, Tree

from .runnables import RunnableBlock
from .syntax import Node

_FILTER_CALLBACKS = {"map", "filter", "sort_by", "unique_by"}
_MISSING = object()


@dataclass
class _Definition:
    name: str
    parameters: tuple[Any, ...]
    body: Node
    environment: dict[str, Any]
    defaults: tuple[Node, ...] = ()


def execution_trees(program: Any, bindings: dict[str, Any]) -> Iterator[Tree]:
    from clang_toolkit.cli.runtime.matcher_functions import MatcherFunction

    active = set()
    builtin_aliases = {
        name for name, value in bindings.items()
        if getattr(value, "__ctk_filter_name__", None) in _FILTER_CALLBACKS
    }

    def resolve(node: Any, environment: dict[str, Any]) -> Any:
        if isinstance(node, Node) and node.kind in {"consume", "observe"}:
            return resolve(node.children[0], environment)
        if isinstance(node, Node) and node.kind == "inline_runnable":
            name, parameters = node.value
            return _Definition(name, parameters, node.children[0], environment, node.children[1:])
        if isinstance(node, Node) and node.kind == "ref":
            return environment.get(node.value)
        return None

    def call(value: Any, arguments: list[Any], environment: dict[str, Any],
             keywords: dict[str, Any] | None = None) -> Iterator[Tree]:
        if not isinstance(value, (RunnableBlock, _Definition, MatcherFunction)) or id(value) in active:
            return
        active.add(id(value))
        try:
            if isinstance(value, RunnableBlock):
                captured = {key: item for scope in value.scopes for key, item in scope.items()}
                body = value.body
            elif isinstance(value, _Definition):
                captured = dict(value.environment)
                body = value.body
            else:
                captured = dict(environment)
                body = value._body
            captured[value.name] = value
            assigned = {index: argument for index, argument in enumerate(arguments)}
            parameter_names = {
                pattern: index for index, pattern in enumerate(value.parameters)
                if isinstance(pattern, str) and pattern != "_"
            }
            for name, argument in (keywords or {}).items():
                if name in parameter_names and parameter_names[name] not in assigned:
                    assigned[parameter_names[name]] = argument
            for index, pattern in enumerate(value.parameters):
                if index in assigned:
                    bind_pattern(captured, pattern, assigned[index])
            defaults = value.default_nodes if isinstance(value, RunnableBlock) else value.defaults if isinstance(value, _Definition) else ()
            default_start = len(value.parameters) - len(defaults)
            for default_offset, default in enumerate(defaults):
                parameter_index = default_start + default_offset
                if parameter_index not in assigned:
                    yield from visit(default, captured)
                    captured[default.value] = resolve(default.children[0], captured)
            yield from visit(body, captured)
        finally:
            active.remove(id(value))

    def bind_pattern(target: dict[str, Any], pattern: Any, value: Any) -> None:
        if isinstance(pattern, str):
            if pattern != "_":
                target[pattern] = value
            return
        for item in pattern:
            bind_pattern(target, item, None)

    def callback_definition(node: Any, environment: dict[str, Any]) -> Any:
        value = resolve(node.children[0], environment) if isinstance(node, Node) and node.kind == "keyword_arg" else resolve(node, environment)
        return value if isinstance(value, (RunnableBlock, _Definition, MatcherFunction)) else None

    def callback_arity(callback: Any) -> int:
        defaults = (callback.default_nodes if isinstance(callback, RunnableBlock)
                    else callback.defaults if isinstance(callback, _Definition) else ())
        required = len(callback.parameters) - len(defaults)
        # Shared shorthand expands tuple elements only for a callback with more
        # than one required ordinary parameter. Tuple-pattern parameters count
        # as one and receive the whole item.
        return required if required > 1 else 1

    def visit_call(node: Node, environment: dict[str, Any], injected: Any = _MISSING) -> Iterator[Tree]:
        if node.value == "ctk":
            # A dynamic command string cannot be inspected before admission.
            yield Tree("dynamic_command", [])
        positional = [resolve(arg, environment) for arg in node.children
                      if not (isinstance(arg, Node) and arg.kind == "keyword_arg")]
        if injected is not _MISSING:
            positional.insert(0, injected)
        keywords = {str(arg.value): resolve(arg.children[0], environment)
                    for arg in node.children if isinstance(arg, Node) and arg.kind == "keyword_arg"}
        yield from call(environment.get(node.value), positional, environment, keywords)
        if node.value in _FILTER_CALLBACKS | builtin_aliases:
            for argument in reversed(node.children):
                callback = callback_definition(argument, environment)
                if callback is not None:
                    yield from call(callback, [None] * callback_arity(callback), environment)
                    break

    def visit(node: Any, environment: dict[str, Any]) -> Iterator[Tree]:
        if isinstance(node, Node):
            if node.kind == "inline_runnable":
                return
            if node.kind == "runnable":
                name, parameters = node.value
                environment[name] = _Definition(name, parameters, node.children[0], environment, node.children[1:])
                return
            if node.kind == "let":
                environment[node.value] = resolve(node.children[0], environment)
                assigned = node.children[0]
                if isinstance(assigned, Node) and assigned.kind == "ref":
                    if assigned.value in _FILTER_CALLBACKS | builtin_aliases:
                        builtin_aliases.add(node.value)
                elif getattr(environment[node.value], "__ctk_filter_name__", None) in _FILTER_CALLBACKS:
                    builtin_aliases.add(node.value)
            if node.kind == "call":
                yield from visit_call(node, environment)
            if node.kind == "pipe":
                values = node.children
                injected = None
                if values:
                    yield from visit(values[0], environment)
                    injected = resolve(values[0], environment)
                for stage in values[1:]:
                    if stage.kind == "ref":
                        stage_call = Node("call", str(stage.value), (), stage.line, stage.column)
                        yield from visit_call(stage_call, environment, injected=injected)
                    elif stage.kind == "call":
                        yield from visit_call(stage, environment, injected=injected)
                        for argument in stage.children:
                            if isinstance(argument, Node) and argument.kind == "keyword_arg":
                                yield from visit(argument.children[0], environment)
                            else:
                                yield from visit(argument, environment)
                    injected = None
                return
            if node.kind == "host":
                yield from visit(node.value[0], environment)
            for child in node.children:
                yield from visit(child, environment)
        elif isinstance(node, Tree):
            yield node
            if node.data == "matcher":
                args = [arg for child in node.children if isinstance(child, Tree)
                        and child.data == "arguments" for arg in child.children]
                yield from call(environment.get(str(node.children[0])),
                                [resolve(arg, environment) for arg in args], environment)
            for child in node.children:
                if isinstance(child, Token):
                    template = getattr(node.meta, "ctk_templates", {}).get(str(child))
                    if template is not None:
                        for expression in template.expressions:
                            yield from visit(expression, environment)
                yield from visit(child, environment)

    yield from visit(program, dict(bindings))
