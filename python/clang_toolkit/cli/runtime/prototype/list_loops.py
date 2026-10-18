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


def _reverse_shape(node: Any, empty: Any, full: Any) -> LoopShape | None:
    ep, fp = empty.value[1], full.value[1]
    if ep != (ListPattern(()),) or len(fp) != 1 or not isinstance(fp[0], ConsPattern):
        return None
    pattern = fp[0]
    if (
        any(
            not isinstance(name, str) or name in {"_", node.value}
            for name in (pattern.head, pattern.tail)
        )
        or pattern.head == pattern.tail
    ):
        return None
    if len(empty.children) != 1 or len(full.children) != 1:
        return None
    base, body = empty.children[0], full.children[0]
    if (
        base.kind != "block"
        or body.kind != "block"
        or len(base.children) != 1
        or len(body.children) != 3
    ):
        return None
    value = _statement(base.children[0])
    if value.kind != "list" or value.children:
        return None
    assignment, push_node, final = map(_statement, body.children)
    if assignment.kind != "let" or assignment.value in {
        node.value,
        pattern.head,
        pattern.tail,
    }:
        return None
    recursive = assignment.children[0]
    if recursive.kind == "consume":
        recursive = recursive.children[0]
    if (
        recursive.kind != "call"
        or recursive.value != node.value
        or len(recursive.children) != 1
        or not _reference(recursive.children[0], pattern.tail)
    ):
        return None
    push = _push(push_node)
    if (
        push is None
        or push[0] != assignment.value
        or not _reference(push[1], pattern.head)
        or not _reference(final, assignment.value)
    ):
        return None
    return LoopShape(
        "reverse",
        node,
        empty,
        full,
        pattern.head,
        pattern.tail,
        "",
        "",
        push_node,
        push[1],
        push[2],
        recursive,
        result=assignment.value,
    )


def recognize_loop(node: Any) -> LoopShape | None:
    if node.kind != "clause_runnable" or len(node.children) != 2:
        return None
    empty, full = node.children
    ep, fp = empty.value[1], full.value[1]
    if len(ep) == len(fp) == 1:
        return _reverse_shape(node, empty, full)
    if len(ep) != 3 or len(fp) != 3 or ep[0] != ListPattern(()):
        return None
    pattern = fp[0]
    if not isinstance(pattern, ConsPattern):
        return None
    names = (pattern.head, pattern.tail, *fp[1:], *ep[1:])
    if any(not isinstance(name, str) or name in {"_", node.value} for name in names):
        return None
    if len({pattern.head, pattern.tail, *fp[1:]}) != 4 or len(set(ep[1:])) != 2:
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
    condition = first if first.kind == "conditional" else None
    if condition is not None:
        predicate, yes, no = condition.children
        if (
            yes.kind != "block"
            or no.kind != "block"
            or len(yes.children) != 1
            or no.children
        ):
            return None
        pushed = _statement(yes.children[0])
    else:
        pushed = first
    push = _push(pushed)
    if push is None or push[0] != fp[2]:
        return None
    _, argument, steps = push
    callback = predicate if condition is not None else argument
    if (
        callback.kind != "call"
        or callback.value != fp[1]
        or len(callback.children) != 1
        or not _reference(callback.children[0], pattern.head)
    ):
        return None
    if condition is not None and not _reference(argument, pattern.head):
        return None
    return LoopShape(
        "filter" if condition is not None else "map",
        node,
        empty,
        full,
        pattern.head,
        pattern.tail,
        fp[1],
        fp[2],
        pushed,
        callback,
        steps,
        recursive,
        condition,
    )


def _host_ready(context: Any) -> bool:
    from .repl import ReplSession

    runtime = getattr(getattr(context, "session", None), "runtime", None)
    return getattr(context.host_evaluator, "__func__", None) is ReplSession.host and (
        runtime is None or runtime._active_resource_scope is None
    )


def _can_loop(
    context: Any, arguments: list[Any], host: bool, reverse: bool = False
) -> bool:
    from threading import Event

    from .runnables import MultiClauseBlock, RunnableBlock

    if len(arguments) != (1 if reverse else 3) or type(arguments[0]) is not list:
        return False
    if not reverse and (
        type(arguments[2]) is not list
        or arguments[0]
        and type(arguments[1]) not in (RunnableBlock, MultiClauseBlock)
    ):
        return False
    hook = context.cancel_hook
    if hook is not None and not (
        getattr(hook, "__func__", None) is Event.is_set
        and type(getattr(hook, "__self__", None)) is Event
    ):
        return False
    return not host or _host_ready(context)


def _snapshot(
    context: Any, arguments: list[Any], owner: Any, call_node: Any
) -> list[Any]:
    """Match the empty/cons clauses before isolating the first logical tail."""
    from .semantics import _error

    context.tick(owner.body)
    if arguments[0]:
        context.tick(owner.body)
        if not arguments[0]:
            raise _error(context, call_node, f"no matching clause for {owner.name}")
    return arguments[0].copy()


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
            }
        )
        if shape.kind != "reverse":
            local.update({shape.callback: callback, shape.output: output})
    elif shape.kind != "reverse":
        parameters = shape.empty.value[1]
        local.update({parameters[1]: callback, parameters[2]: output})
    context._scopes[:] = [*owner.scopes, local]


def _insertable(context: Any, node: Any, output: list[Any], value: Any) -> None:
    from clang_toolkit.match_values import MatchValueError

    from ..collections import ensure_insertable
    from ..references import ReferenceError
    from .semantics import PrototypeError

    try:
        ensure_insertable(output, value)
    except (ReferenceError, MatchValueError, IndexError, KeyError) as error:
        method = node.value[0].children[3]
        raise PrototypeError(
            f"{error} at .push(...) (line {method.meta.line}, column {method.meta.column})"
        ) from error


def _callback_value(
    context: Any,
    node: Any,
    head_node: Any,
    callback: Any,
    head: Any,
    host_argument: bool,
) -> Any:
    from .runnables import _preflight, invoke_prepared
    from .semantics import PrototypeError, _error

    try:
        _preflight(context, node, str(node.value), callback, 1, ())
        context.tick(head_node)
        return invoke_prepared(context, node, callback, [head], {})
    except PrototypeError as error:
        runtime = getattr(getattr(context, "session", None), "runtime", None)
        tree_host = (
            host_argument
            and runtime is not None
            and runtime._prototype_session.engine == "tree"
        )
        location = (
            f"line {node.line}, column {node.column}"
            if tree_host
            else f"line {node.line}"
        )
        if location not in str(error):
            raise _error(context, node, str(error), type(error)) from error
        raise


def compile_direct_loop(node: Any, context: Any) -> Any:
    shape = recognize_loop(node)
    if shape is None:
        return None
    if shape.kind == "reverse":
        return _compile_reverse(shape)
    import ast

    from .list_recursion import _Arena
    from .semantics import _as_bool, observe_statement

    # Only the fixed compiler template is interpolated, never user source.
    prefix = f"""def direct_{shape.kind}(context, arguments, owner, call_node):
    if not can_loop(context, arguments, host):
        return owner.recursion.run(context, arguments, owner, call_node)
    saved_scopes = list(context._scopes)
    arena = Arena()
    callback, output = arguments[1:]
    try:
        items = snapshot(context, arguments, owner, call_node)
        for index in range(len(items)):
            if index:
                context.tick(group)
                context.tick(group)
            bind_scope(context, owner, shape, items, index, arena, callback, output)
            context.tick(body)
            generic_push = False
"""
    if shape.kind == "map":
        work = """            for step in push_steps:
                context.tick(step)
            if host_ready(context):
                for step in callback_steps:
                    context.tick(step)
                value = callback_value(context, callback_node, head_node, callback, items[index], host_argument)
                insertable(context, push_node, output, value)
                output.append(value)
                pushed = output
            else:
                pushed = context.host_evaluator(context, push_node)
                generic_push = True
            if observe_push:
                observe(context, push_node, pushed)
"""
    else:
        work = """            context.tick(condition)
            for step in callback_steps:
                context.tick(step)
            value = callback_value(context, callback_node, head_node, callback, items[index], host_argument)
            keep = as_bool(context, value, condition)
            context.push_scope()
            try:
                if keep:
                    context.tick(yes_block)
                    for step in push_steps:
                        context.tick(step)
                    if host_ready(context):
                        for step in push_argument_steps:
                            context.tick(step)
                        insertable(context, push_node, output, items[index])
                        output.append(items[index])
                        branch_value = output
                    else:
                        branch_value = context.host_evaluator(context, push_node)
                        generic_push = True
                    if observe_push:
                        observe(context, push_node, branch_value)
                else:
                    context.tick(no_block)
                    branch_value = None
            finally:
                context.pop_scope()
            if observe_condition:
                observe(context, condition, branch_value)
"""
    suffix = """            for step in recursive_steps:
                context.tick(step)
            if generic_push:
                remaining = [context.lookup(shape.tail), context.lookup(shape.callback), context.lookup(shape.output)]
                return owner.recursion.run(context, remaining, owner, recursive)
        if items:
            context.tick(group)
        bind_scope(context, owner, shape, items, len(items), arena, callback, output)
        context.push_scope()
        try:
            for step in base_steps:
                context.tick(step)
            if observe_base:
                observe(context, base_value, output)
        finally:
            context.pop_scope()
        return output
    finally:
        context._scopes[:] = saved_scopes
"""
    source = prefix + work + suffix
    callback = shape.argument
    base_block = shape.empty.children[0]
    base_value = _statement(base_block.children[0])
    namespace = {
        "__builtins__": {},
        "list": list,
        "range": range,
        "len": len,
        "can_loop": _can_loop,
        "host_ready": _host_ready,
        "host": shape.push.kind == "host",
        "Arena": _Arena,
        "bind_scope": _scope,
        "snapshot": _snapshot,
        "shape": shape,
        "group": shape.group,
        "body": shape.full.children[0],
        "push_steps": shape.push_steps,
        "callback_steps": (callback, callback)
        if shape.kind == "map" and shape.push.kind == "host"
        else (callback,),
        "callback_node": callback,
        "callback_value": _callback_value,
        "host_argument": shape.kind == "map" and shape.push.kind == "host",
        "head_node": callback.children[0],
        "insertable": _insertable,
        "push_node": shape.push,
        "observe_push": shape.full.children[0].children[0].kind == "observe",
        "observe": observe_statement,
        "recursive_steps": (shape.recursive, *shape.recursive.children),
        "recursive": shape.recursive,
        "base_steps": (base_block, base_value),
        "base_value": base_value,
        "observe_base": base_block.children[0].kind == "observe",
    }
    if shape.kind == "filter":
        yes, no = shape.condition.children[1:]
        push_argument = _push(shape.push)[1]
        namespace.update(
            condition=shape.condition,
            yes_block=yes,
            no_block=no,
            as_bool=_as_bool,
            push_argument_steps=(push_argument, push_argument)
            if shape.push.kind == "host"
            else (push_argument,),
            observe_push=yes.children[0].kind == "observe",
            observe_condition=shape.full.children[0].children[0].kind == "observe",
        )
    module = ast.parse(source)
    exec(compile(module, "<ctk-direct-list-loop>", "exec"), namespace)  # noqa: S102 - fixed compiler template
    function = namespace["direct_" + shape.kind]
    function.__ctk_source__ = ast.unparse(module)
    return function


def _compile_reverse(shape: LoopShape) -> Any:
    import ast

    from .list_recursion import _Arena
    from .semantics import ExecutionLimitError, _error, observe_statement

    assignment = _statement(shape.full.children[0].children[0])
    consume = assignment.children[0]
    consumed = consume.kind == "consume"
    body = shape.full.children[0]
    base = shape.empty.children[0]
    base_value = _statement(base.children[0])
    final = _statement(body.children[2])
    source = """def direct_reverse(context, arguments, owner, call_node):
    if not can_loop(context, arguments, host, True):
        return owner.recursion.run(context, arguments, owner, call_node)
    saved_scopes = list(context._scopes)
    saved_depth = context.consume_depth
    arena = Arena()
    try:
        items = snapshot(context, arguments, owner, call_node)
        for index in range(len(items)):
            if index:
                context.tick(group)
                context.tick(group)
            bind_scope(context, owner, shape, items, index, arena, None, None)
            for step in descent_steps:
                context.tick(step)
            context.consume_depth += consumed
            for step in recursive_steps:
                context.tick(step)
            if index >= context.max_items:
                raise error(context, recursive, "continuation stack exceeds item limit", LimitError)
        if items:
            context.tick(group)
        bind_scope(context, owner, shape, items, len(items), arena, None, None)
        context.push_scope()
        try:
            context.tick(base_block)
            context.tick(base_value)
            output = []
            if observe_base:
                observe(context, base_value, output)
        finally:
            context.pop_scope()
        for index in range(len(items) - 1, -1, -1):
            context.consume_depth -= consumed
            bind_scope(context, owner, shape, items, index, arena, None, None)
            context.define(result_name, output)
            if observe_assignment:
                observe(context, assignment, output)
            for step in push_steps:
                context.tick(step)
            if host_ready(context):
                for step in push_argument_steps:
                    context.tick(step)
                insertable(context, push_node, output, items[index])
                output.append(items[index])
                pushed = output
            else:
                pushed = context.host_evaluator(context, push_node)
            if observe_push:
                observe(context, push_node, pushed)
            context.tick(final)
            output = context.lookup(result_name)
            if observe_final:
                observe(context, final, output)
        return output
    finally:
        context.consume_depth = saved_depth
        context._scopes[:] = saved_scopes
"""
    argument_steps = (
        (shape.argument, shape.argument)
        if shape.push.kind == "host"
        else (shape.argument,)
    )
    namespace = {
        "__builtins__": {},
        "list": list,
        "range": range,
        "len": len,
        "can_loop": _can_loop,
        "host_ready": _host_ready,
        "host": shape.push.kind == "host",
        "Arena": _Arena,
        "bind_scope": _scope,
        "snapshot": _snapshot,
        "shape": shape,
        "group": shape.group,
        "descent_steps": (body, assignment, consume)
        if consumed
        else (body, assignment),
        "consumed": int(consumed),
        "recursive_steps": (shape.recursive, *shape.recursive.children),
        "recursive": shape.recursive,
        "error": _error,
        "LimitError": ExecutionLimitError,
        "base_block": base,
        "base_value": base_value,
        "observe_base": base.children[0].kind == "observe",
        "observe": observe_statement,
        "result_name": shape.result,
        "assignment": assignment,
        "observe_assignment": body.children[0].kind == "observe",
        "push_steps": shape.push_steps,
        "push_argument_steps": argument_steps,
        "insertable": _insertable,
        "push_node": shape.push,
        "observe_push": body.children[1].kind == "observe",
        "final": final,
        "observe_final": body.children[2].kind == "observe",
    }
    module = ast.parse(source)
    exec(compile(module, "<ctk-direct-list-loop>", "exec"), namespace)  # noqa: S102 - fixed compiler template
    function = namespace["direct_reverse"]
    function.__ctk_source__ = ast.unparse(module)
    return function
