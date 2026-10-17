"""Inspect reachable callable bodies before console/batch admission."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator

from lark import Token, Tree

from .runnables import MultiClauseBlock, RunnableBlock
from .patterns import ConsPattern, ListPattern, pattern_names
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


@dataclass
class _Alternatives:
    values: tuple[Any, ...]


def execution_trees(program: Any, bindings: dict[str, Any]) -> Iterator[Tree]:
    from clang_toolkit.cli.runtime.matcher_functions import MatcherFunction

    active = set()
    resolving: set[int] = set()
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
        if isinstance(node, Node) and node.kind == "clause_runnable":
            return _Alternatives(tuple(_Definition(node.value, clause.value[1], clause.children[0], environment)
                                       for clause in node.children))
        if isinstance(node, Node) and node.kind == "ref":
            return environment.get(node.value)
        if isinstance(node, Node) and node.kind == "literal":
            return node.value
        if isinstance(node, Node) and node.kind in {"list", "tuple"}:
            values = [resolve(child, environment) for child in node.children]
            return tuple(values) if node.kind == "tuple" else values
        if isinstance(node, Node) and node.kind == "dict":
            return {child.value: resolve(child.children[0], environment) for child in node.children}
        if isinstance(node, Node) and node.kind == "conditional":
            condition = resolve(node.children[0], environment)
            if type(condition) is bool:
                return resolve(node.children[1 if condition else 2], environment)
            return _Alternatives(tuple(resolve(branch, environment) for branch in node.children[1:]))
        if isinstance(node, Node) and node.kind in {"index", "get"}:
            base = resolve(node.children[0], environment)
            key = node.value if node.kind == "get" else resolve(node.children[1], environment)
            return project(base, key)
        if isinstance(node, Node) and node.kind in {"call", "invoke"}:
            callee = environment.get(node.value) if node.kind == "call" else resolve(node.children[0], environment)
            args = node.children if node.kind == "call" else node.children[1:]
            return call_result(callee, args, environment)
        if isinstance(node, Node) and node.kind in {"program", "block"}:
            local = dict(environment)
            result = None
            for child in node.children:
                while child.kind in {"consume", "observe"}:
                    child = child.children[0]
                if child.kind == "let":
                    result = resolve(child.children[0], local)
                    local[child.value] = result
                elif child.kind == "destructure":
                    result = resolve(child.children[0], local)
                    bind_pattern(local, child.value, result)
                elif child.kind == "runnable":
                    name, parameters = child.value
                    result = _Definition(name, parameters, child.children[0], local, child.children[1:])
                    local[name] = result
                else:
                    result = resolve(child, local)
            return result
        return None

    def project(base: Any, key: Any) -> Any:
        if isinstance(base, _Alternatives):
            return _Alternatives(tuple(project(candidate, key) for candidate in base.values))
        if type(base) in {list, tuple, dict}:
            if type(key) in {int, str}:
                try:
                    return base[key]
                except (IndexError, KeyError, TypeError):
                    return None
            if key is None:
                return _Alternatives(tuple(base.values()) if type(base) is dict else tuple(base))
        return None

    def call_result(callee: Any, args: tuple[Node, ...], environment: dict[str, Any]) -> Any:
        if isinstance(callee, MultiClauseBlock):
            if id(callee) in resolving:
                return None
            resolving.add(id(callee))
            try:
                captured = {key: item for scope in callee.scopes for key, item in scope.items()}
                return call_result(resolve(callee.body, captured), args, environment)
            finally:
                resolving.remove(id(callee))
        if isinstance(callee, _Alternatives):
            return _Alternatives(tuple(call_result(candidate, args, environment) for candidate in callee.values))
        if not isinstance(callee, (RunnableBlock, _Definition)) or id(callee) in resolving:
            return None
        resolving.add(id(callee))
        try:
            captured = ({key: value for scope in callee.scopes for key, value in scope.items()}
                        if isinstance(callee, RunnableBlock) else dict(callee.environment))
            captured[callee.name] = callee
            positional = [arg for arg in args if arg.kind != "keyword_arg"]
            keywords = {arg.value: arg.children[0] for arg in args if arg.kind == "keyword_arg"}
            defaults = callee.default_nodes if isinstance(callee, RunnableBlock) else callee.defaults
            default_start = len(callee.parameters) - len(defaults)
            for index, pattern in enumerate(callee.parameters):
                if index < len(positional):
                    value = resolve(positional[index], environment)
                elif isinstance(pattern, str) and pattern in keywords:
                    value = resolve(keywords[pattern], environment)
                elif index >= default_start:
                    value = resolve(defaults[index - default_start].children[0], captured)
                else:
                    value = None
                bind_pattern(captured, pattern, value)
            return resolve(callee.body, captured)
        finally:
            resolving.remove(id(callee))

    def call(value: Any, arguments: list[Any], environment: dict[str, Any],
             keywords: dict[str, Any] | None = None) -> Iterator[Tree]:
        if isinstance(value, MultiClauseBlock):
            if id(value) in active:
                return
            active.add(id(value))
            try:
                captured = {key: item for scope in value.scopes for key, item in scope.items()}
                yield from call(resolve(value.body, captured), arguments, environment, keywords)
            finally:
                active.remove(id(value))
            return
        if isinstance(value, _Alternatives):
            for candidate in value.values:
                yield from call(candidate, arguments, environment, keywords)
            return
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
        if isinstance(value, _Alternatives):
            candidates = []
            for item in value.values:
                candidate: dict[str, Any] = {}
                bind_pattern(candidate, pattern, item)
                candidates.append(candidate)
            for name in pattern_names(pattern):
                target[name] = _Alternatives(tuple(candidate.get(name) for candidate in candidates))
            return
        if isinstance(pattern, str):
            if pattern != "_":
                target[pattern] = value
            return
        if isinstance(pattern, ConsPattern):
            if isinstance(value, list) and value:
                bind_pattern(target, pattern.head, value[0])
                bind_pattern(target, pattern.tail, value[1:])
            else:
                target.update((name, None) for name in pattern_names(pattern))
            return
        if isinstance(pattern, ListPattern):
            elements = pattern.elements
            values = value if isinstance(value, list) and len(value) == len(elements) else (None,) * len(elements)
            for item, child in zip(elements, values):
                bind_pattern(target, item, child)
            return
        values = value if type(value) is tuple and len(value) == len(pattern) else (None,) * len(pattern)
        for item, child in zip(pattern, values):
            bind_pattern(target, item, child)

    def callback_definition(node: Any, environment: dict[str, Any]) -> Any:
        value = resolve(node.children[0], environment) if isinstance(node, Node) and node.kind == "keyword_arg" else resolve(node, environment)
        return value if isinstance(value, (RunnableBlock, _Definition, MatcherFunction, _Alternatives)) else None

    def callback_arity(callback: Any) -> int:
        if isinstance(callback, _Alternatives):
            return max((callback_arity(item) for item in callback.values), default=1)
        if not isinstance(callback, (RunnableBlock, _Definition, MatcherFunction)):
            return 1
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
            if node.kind in {"inline_runnable", "clause_runnable"}:
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
            if node.kind == "destructure":
                bind_pattern(environment, node.value, resolve(node.children[0], environment))
            if node.kind == "call":
                yield from visit_call(node, environment)
            if node.kind == "invoke":
                arguments = node.children[1:]
                yield from call(resolve(node.children[0], environment),
                                [resolve(arg, environment) for arg in arguments if arg.kind != "keyword_arg"],
                                environment,
                                {arg.value: resolve(arg.children[0], environment)
                                 for arg in arguments if arg.kind == "keyword_arg"})
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
