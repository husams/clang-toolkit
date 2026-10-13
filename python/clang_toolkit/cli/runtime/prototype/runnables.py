"""Lexical runnable values shared by the tree and Python AST engines."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Callable

from .semantics import Context, ExecutionLimitError, PrototypeError, _error, child_values


@dataclass(frozen=True, repr=False)
class RunnableBlock:
    name: str
    parameters: tuple[str, ...]
    body: Any
    executable: Callable[[Context], Any]
    scopes: tuple[dict[str, Any], ...]
    source: str
    string_templates: dict[str, Any]
    definition_location: tuple[int | None, int | None]
    source_name: str

    def __str__(self) -> str:
        return f"{self.name}({', '.join(self.parameters)})"

    def invoke(self, context: Context, node: Any, arguments: list[Any]) -> Any:
        runtime = getattr(getattr(context, "session", None), "runtime", None)
        depth = getattr(runtime, "_matcher_call_depth", context.call_depth)
        if depth >= 64:
            raise _error(context, node, "runnable call depth exceeds 64", ExecutionLimitError)
        previous_scopes = list(context._scopes)
        previous_source = context.source
        previous_source_name = context.source_name
        previous_templates = context.string_templates
        context.call_depth += 1
        if runtime is not None:
            runtime._matcher_call_depth += 1
        context._scopes[:] = [*self.scopes, {self.name: self},
                             dict(zip(self.parameters, arguments, strict=True))]
        context.source = self.source
        context.source_name = self.source_name
        context.string_templates = self.string_templates
        try:
            return self.executable(context)
        except Exception as error:
            if not getattr(error, "runnable_frame", False):
                line, column = self.definition_location
                detail = (f"{error}; runnable {self.name} defined at line {line}, column {column} in {self.source_name}, "
                          f"called at line {getattr(node, 'line', None)}, column {getattr(node, 'column', None)} in {previous_source_name}")
                kind = type(error) if isinstance(error, PrototypeError) else PrototypeError
                framed = kind(detail)
                framed.runnable_frame = True
                raise framed from error
            raise
        finally:
            context._scopes[:] = previous_scopes
            context.source = previous_source
            context.source_name = previous_source_name
            context.string_templates = previous_templates
            context.call_depth -= 1
            if runtime is not None:
                runtime._matcher_call_depth -= 1


def define_runnable(context: Context, node: Any, executable: Callable[[Context], Any]) -> RunnableBlock:
    from clang_toolkit.cli.matcher_catalog import SCRIPT_BUILTIN_MATCHERS

    name, parameters = node.value
    if name in context.functions or name in SCRIPT_BUILTIN_MATCHERS | {"glob", "flatten"}:
        raise _error(context, node, f"{name} is a built-in callable name")
    if len(set(parameters)) != len(parameters):
        raise _error(context, node, f"{name} has duplicate parameter names")
    value = RunnableBlock(name, parameters, node.children[0], executable,
                          context.scopes, context.source, context.string_templates,
                          (node.line, node.column), context.source_name)
    context.define(name, value)
    return value


def invoke_named(context: Context, node: Any, name: str,
                 arguments: Callable[[], list[Any]]) -> Any:
    present, value = context.binding_state(name, node)
    if present:
        if isinstance(value, RunnableBlock):
            count = len(child_values(node))
            if count != len(value.parameters):
                raise _error(context, node,
                             f"{name} expects {len(value.parameters)} argument(s), got {count}")
            return value.invoke(context, node, arguments())
        from clang_toolkit.cli.runtime.matcher_functions import MatcherFunction

        if isinstance(value, MatcherFunction):
            runtime = getattr(getattr(context, "session", None), "runtime", None)
            if runtime is not None:
                if len(child_values(node)) != len(value.parameters):
                    raise _error(context, node, f"{name} expects {len(value.parameters)} argument(s)")
                return value.call(runtime, arguments())
        raise _error(context, node, f"{name!r} is not callable")
    function = context.functions.get(name)
    if function is None:
        raise _error(context, node, f"unregistered host function {name!r}")
    return function(*arguments())


def snapshot_scopes(scopes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Freeze plain captures for one group, preserving aliases and recursion."""
    copies: dict[int, Any] = {}

    def copy(value: Any) -> Any:
        if id(value) in copies:
            return copies[id(value)]
        if isinstance(value, RunnableBlock):
            result = replace(value, scopes=())
            copies[id(value)] = result
            object.__setattr__(result, "scopes", tuple(copy(scope) for scope in value.scopes))
            return result
        if type(value) is dict:
            result = {}
            copies[id(value)] = result
            result.update((key, copy(item)) for key, item in value.items())
            return result
        if type(value) is list:
            result = []
            copies[id(value)] = result
            result.extend(copy(item) for item in value)
            return result
        if type(value) is tuple:
            return tuple(copy(item) for item in value)
        # Native objects retain their ownership and stale-handle checks.
        return value

    return [copy(scope) for scope in scopes]
