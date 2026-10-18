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
    # Scalars cannot introduce a collection cycle. Avoid allocating traversal
    # sets and a visitor closure for the common map/filter/reverse case.
    value_type = type(value)
    if (
        value_type is int
        or value_type is float
        or value_type is str
        or value_type is bool
        or value is None
    ):
        return
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


# Fixed compiler templates keep traversal and append operations visible. Source
# accounting and lexical scope management are shared by one guard per invocation.
_TEMPLATES = {
    "map": """def direct_map(context, arguments, owner, call_node):
    if not can_loop(context, arguments, True):
        return owner.recursion.run(context, arguments, owner, call_node)
    with execution(context, arguments, owner, call_node) as loop:
        plain = prepare_plain(loop)
        if plain is not None:
            return plain[0](*plain[1])
        callback, output = arguments[1:]
        for index, head in enumerate(loop.items):
            loop.enter(index)
            if not loop.host_ready():
                return loop.resume()
            value = loop.map_value(callback, head)
            loop.validate(output, value)
            output.append(value)
            loop.pushed(output)
            loop.advance()
        return loop.finish(output)
""",
    "filter": """def direct_filter(context, arguments, owner, call_node):
    if not can_loop(context, arguments, True):
        return owner.recursion.run(context, arguments, owner, call_node)
    with execution(context, arguments, owner, call_node) as loop:
        plain = prepare_plain(loop)
        if plain is not None:
            return plain[0](*plain[1])
        callback, output = arguments[1:]
        for index, head in enumerate(loop.items):
            loop.enter(index)
            if loop.keep(callback, head):
                if not loop.host_ready():
                    return loop.resume()
                loop.validate(output, head)
                output.append(head)
                loop.pushed(output)
            loop.end_branch()
            loop.advance()
        return loop.finish(output)
""",
    "reverse": """def direct_reverse(context, arguments, owner, call_node):
    if not can_loop(context, arguments, True, True):
        return owner.recursion.run(context, arguments, owner, call_node)
    with execution(context, arguments, owner, call_node) as loop:
        plain = prepare_plain(loop)
        if plain is not None:
            return plain[0](*plain[1])
        for index in range(len(loop.items)):
            loop.descend(index)
        output = loop.finish([])
        for index in range(len(loop.items) - 1, -1, -1):
            head = loop.items[index]
            loop.unwind(index, output)
            if loop.host_ready():
                loop.validate(output, head)
                output.append(head)
                loop.pushed(output)
            else:
                loop.host_push()
            output = loop.result()
        return output
""",
}


def compile_direct_loop(node: Any, context: Any) -> Any:
    shape = recognize_loop(node)
    if shape is None:
        return None
    import ast

    from .list_loop_runtime import LoopPlan
    from .plain_list_loops import prepare_plain

    plan = LoopPlan(shape)

    namespace = {
        "__builtins__": {},
        "enumerate": enumerate,
        "range": range,
        "len": len,
        "can_loop": _can_loop,
        "execution": plan,
        "prepare_plain": prepare_plain,
    }
    module = ast.parse(_TEMPLATES[shape.kind])
    exec(compile(module, "<ctk-direct-list-loop>", "exec"), namespace)  # noqa: S102 - fixed compiler template
    function = namespace["direct_" + shape.kind]
    function.__ctk_source__ = ast.unparse(module)
    function.__ctk_plan__ = plan
    return function
