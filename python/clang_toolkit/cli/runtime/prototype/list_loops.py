"""Structural recognition for direct indexed list loops."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .patterns import ConsPattern, ListPattern


def _statement(node: Any) -> Any:
    return node.children[0] if node.kind == "observe" else node


def _reference(node: Any, name: str) -> bool:
    return node.kind == "ref" and node.value == name


def _push(node: Any) -> tuple[str, Any, tuple[Any, ...]] | None:
    """Return target, argument and pre-argument ticks for an exact list push."""
    if node.kind == "invoke" and len(node.children) == 2:
        method, argument = node.children
        if (
            method.kind == "get"
            and method.value == "push"
            and method.children[0].kind == "ref"
        ):
            return (
                method.children[0].value,
                argument,
                (node, method, method.children[0]),
            )
    if node.kind == "host":
        tree, mode = node.value
        if (
            mode != "expression"
            or str(tree.data) != "reference"
            or len(tree.children) != 4
        ):
            return None
        dollar, name, dot, method = tree.children
        if (
            str(dollar) != "$"
            or str(dot) != "."
            or str(getattr(method, "data", "")) != "generic_method_call"
        ):
            return None
        if len(method.children) != 4:
            return None
        method_name, left, arguments, right = method.children
        if (
            str(method_name.children[0]) != "push"
            or str(left) != "("
            or str(right) != ")"
        ):
            return None
        if (
            str(arguments.data) == "method_arguments"
            and len(arguments.children) == 1
            and hasattr(arguments.children[0], "kind")
        ):
            return str(name), arguments.children[0], (node,)
    return None


@dataclass(frozen=True)
class LoopShape:
    kind: str
    group: Any
    empty: Any
    full: Any
    head: str
    tail: str
    callback: str
    output: str
    push: Any
    argument: Any
    push_steps: tuple[Any, ...]
    recursive: Any
    condition: Any = None
    result: str = ""


def recognize_loop(node: Any) -> LoopShape | None:
    if node.kind != "clause_runnable" or len(node.children) != 2:
        return None
    empty, full = node.children
    ep, fp = empty.value[1], full.value[1]
    if len(ep) != 3 or len(fp) != 3 or ep[0] != ListPattern(()):
        return None
    pattern = fp[0]
    if not isinstance(pattern, ConsPattern):
        return None
    names = (pattern.head, pattern.tail, *fp[1:], *ep[1:])
    if any(not isinstance(name, str) or name in {"_", node.value} for name in names):
        return None
    if len(empty.children) != 1 or len(full.children) != 1:
        return None
    base, body = empty.children[0], full.children[0]
    if (
        base.kind != "block"
        or body.kind != "block"
        or len(base.children) != 1
        or len(body.children) != 2
    ):
        return None
    if not _reference(_statement(base.children[0]), ep[2]):
        return None
    first, recursive = map(_statement, body.children)
    expected = (pattern.tail, fp[1], fp[2])
    if (
        recursive.kind != "call"
        or recursive.value != node.value
        or len(recursive.children) != 3
    ):
        return None
    if not all(
        _reference(argument, name)
        for argument, name in zip(recursive.children, expected)
    ):
        return None
    push = _push(first)
    if push is None or push[0] != fp[2]:
        return None
    _, callback, steps = push
    if (
        callback.kind != "call"
        or callback.value != fp[1]
        or len(callback.children) != 1
        or not _reference(callback.children[0], pattern.head)
    ):
        return None
    return LoopShape(
        "map",
        node,
        empty,
        full,
        pattern.head,
        pattern.tail,
        fp[1],
        fp[2],
        first,
        callback,
        steps,
        recursive,
    )


def _can_loop(context: Any, arguments: list[Any], host: bool) -> bool:
    from threading import Event
    from .runnables import MultiClauseBlock, RunnableBlock
    from .repl import ReplSession

    if (
        len(arguments) != 3
        or type(arguments[0]) is not list
        or type(arguments[2]) is not list
    ):
        return False
    if arguments[0] and type(arguments[1]) not in (RunnableBlock, MultiClauseBlock):
        return False
    hook = context.cancel_hook
    if hook is not None and not (
        getattr(hook, "__func__", None) is Event.is_set
        and type(getattr(hook, "__self__", None)) is Event
    ):
        return False
    if (
        host
        and getattr(context.host_evaluator, "__func__", None) is not ReplSession.host
    ):
        return False
    runtime = getattr(getattr(context, "session", None), "runtime", None)
    return runtime is None or runtime._active_resource_scope is None


def _scope(
    context: Any,
    owner: Any,
    shape: LoopShape,
    items: list[Any],
    index: int,
    arena: Any,
    callback: Any,
    output: list[Any],
) -> None:
    from .list_recursion import _Cursor

    local = {owner.name: owner}
    if index < len(items):
        local.update(
            {
                shape.head: items[index],
                shape.tail: _Cursor(items, index + 1, len(items), arena, True),
                shape.callback: callback,
                shape.output: output,
            }
        )
    else:
        parameters = shape.empty.value[1]
        local.update({parameters[1]: callback, parameters[2]: output})
    context._scopes[:] = [*owner.scopes, local]


def _insertable(context: Any, node: Any, output: list[Any], value: Any) -> None:
    from ..collections import ensure_insertable
    from .semantics import _error

    try:
        ensure_insertable(output, value)
    except ValueError as error:
        message = str(error) if node.kind == "host" else f"call failed: {error}"
        raise _error(context, node, message) from error


def compile_direct_loop(node: Any, context: Any) -> Any:
    shape = recognize_loop(node)
    if shape is None:
        return None
    from .list_recursion import _Arena
    from .runnables import _preflight, invoke_prepared
    from .semantics import observe_statement
    import ast

    source = """def direct_map(context, arguments, owner, call_node):
    if not can_loop(context, arguments, host):
        return owner.recursion.run(context, arguments, owner, call_node)
    saved_scopes = list(context._scopes)
    arena = Arena()
    items = arguments[0].copy()
    callback, output = arguments[1:]
    try:
        for index in range(len(items)):
            context.tick(group)
            context.tick(group)
            bind_scope(context, owner, shape, items, index, arena, callback, output)
            context.tick(body)
            for step in push_steps:
                context.tick(step)
            for step in callback_steps:
                context.tick(step)
            preflight(context, callback_node, callback_name, callback, 1, ())
            context.tick(head_node)
            value = invoke(context, callback_node, callback, [items[index]], {})
            insertable(context, push_node, output, value)
            output.append(value)
            if observe_push:
                observe(context, push_node, output)
            for step in recursive_steps:
                context.tick(step)
        context.tick(group)
        bind_scope(context, owner, shape, items, len(items), arena, callback, output)
        for step in base_steps:
            context.tick(step)
        if observe_base:
            observe(context, base_value, output)
        return output
    finally:
        context._scopes[:] = saved_scopes
"""
    callback = shape.argument
    base_block = shape.empty.children[0]
    base_value = _statement(base_block.children[0])
    namespace = {
        "__builtins__": {},
        "list": list,
        "range": range,
        "len": len,
        "can_loop": _can_loop,
        "host": shape.push.kind == "host",
        "Arena": _Arena,
        "bind_scope": _scope,
        "shape": shape,
        "group": shape.group,
        "body": shape.full.children[0],
        "push_steps": shape.push_steps,
        "callback_steps": (callback, callback)
        if shape.push.kind == "host"
        else (callback,),
        "callback_node": callback,
        "callback_name": shape.callback,
        "head_node": callback.children[0],
        "preflight": _preflight,
        "invoke": invoke_prepared,
        "insertable": _insertable,
        "push_node": shape.push,
        "observe_push": shape.full.children[0].children[0].kind == "observe",
        "observe": observe_statement,
        "recursive_steps": (shape.recursive, *shape.recursive.children),
        "base_steps": (base_block, base_value),
        "base_value": base_value,
        "observe_base": base_block.children[0].kind == "observe",
    }
    module = ast.parse(source)
    exec(compile(module, "<ctk-direct-list-loop>", "exec"), namespace)
    function = namespace["direct_map"]
    function.__ctk_source__ = ast.unparse(module)
    return function
