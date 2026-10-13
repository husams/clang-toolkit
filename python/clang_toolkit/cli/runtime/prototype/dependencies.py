"""Inspect reachable callable bodies before console/batch admission."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator

from lark import Token, Tree

from .runnables import RunnableBlock
from .syntax import Node


@dataclass
class _Definition:
    name: str
    parameters: tuple[str, ...]
    body: Node
    environment: dict[str, Any]
    defaults: tuple[Node, ...] = ()


def execution_trees(program: Any, bindings: dict[str, Any]) -> Iterator[Tree]:
    from clang_toolkit.cli.runtime.matcher_functions import MatcherFunction

    active = set()

    def resolve(node: Any, environment: dict[str, Any]) -> Any:
        if isinstance(node, Node) and node.kind in {"consume", "observe"}:
            return resolve(node.children[0], environment)
        if isinstance(node, Node) and node.kind == "ref":
            return environment.get(node.value)
        return None

    def call(value: Any, arguments: list[Any], environment: dict[str, Any]) -> Iterator[Tree]:
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
            captured.update(zip(value.parameters, arguments))
            defaults = value.default_nodes if isinstance(value, RunnableBlock) else value.defaults if isinstance(value, _Definition) else ()
            missing = len(value.parameters) - len(arguments)
            if missing > 0:
                for default in defaults[-missing:]:
                    yield from visit(default, captured)
                    captured[default.value] = resolve(default.children[0], captured)
            yield from visit(body, captured)
        finally:
            active.remove(id(value))

    def visit(node: Any, environment: dict[str, Any]) -> Iterator[Tree]:
        if isinstance(node, Node):
            if node.kind == "runnable":
                name, parameters = node.value
                environment[name] = _Definition(name, parameters, node.children[0], environment, node.children[1:])
                return
            if node.kind == "let":
                environment[node.value] = resolve(node.children[0], environment)
            if node.kind == "call":
                if node.value == "ctk":
                    # A dynamic command string cannot be inspected before admission.
                    yield Tree("dynamic_command", [])
                yield from call(environment.get(node.value),
                                [resolve(arg, environment) for arg in node.children], environment)
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
