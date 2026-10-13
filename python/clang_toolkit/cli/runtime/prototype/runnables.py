"""Lexical runnable values shared by the tree and Python AST engines."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from .semantics import Context, ExecutionLimitError, _error, child_values


@dataclass(frozen=True, repr=False)
class RunnableBlock:
    name: str
    parameters: tuple[str, ...]
    body: Any
    executable: Callable[[Context], Any]
    scopes: tuple[dict[str, Any], ...]
    source: str

    def __str__(self) -> str:
        return f"{self.name}({', '.join(self.parameters)})"

    def invoke(self, context: Context, node: Any, arguments: list[Any]) -> Any:
        runtime = getattr(getattr(context, "session", None), "runtime", None)
        depth = getattr(runtime, "_matcher_call_depth", context.call_depth)
        if depth >= 64:
            raise _error(context, node, "runnable call depth exceeds 64", ExecutionLimitError)
        previous_scopes = list(context._scopes)
        previous_source = context.source
        context.call_depth += 1
        if runtime is not None:
            runtime._matcher_call_depth += 1
        context._scopes[:] = [*self.scopes, {self.name: self},
                             dict(zip(self.parameters, arguments, strict=True))]
        context.source = self.source
        try:
            return self.executable(context)
        finally:
            context._scopes[:] = previous_scopes
            context.source = previous_source
            context.call_depth -= 1
            if runtime is not None:
                runtime._matcher_call_depth -= 1


def define_runnable(context: Context, node: Any, executable: Callable[[Context], Any]) -> RunnableBlock:
    from clang_toolkit.cli.matcher_catalog import NESTED_MATCHERS, ROOT_MATCHERS

    name, parameters = node.value
    if name in context.functions or name in set(ROOT_MATCHERS) | set(NESTED_MATCHERS):
        raise _error(context, node, f"{name} is a built-in callable name")
    if len(set(parameters)) != len(parameters):
        raise _error(context, node, f"{name} has duplicate parameter names")
    value = RunnableBlock(name, parameters, node.children[0], executable,
                          context.scopes, context.source)
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
