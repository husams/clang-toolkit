"""Prove and lower pure self-recursive numeric right folds to bounded loops."""

from __future__ import annotations

import ast
from typing import Any, Callable

from .patterns import ConsPattern, ListPattern


def compile_right_fold(node: Any) -> Callable[..., Any] | None:
    """Recognize exactly `([]) NUMBER; (h:t) h OP self(t)`; never reassociate."""
    if len(node.children) != 2:
        return None
    empty, nonempty = node.children
    if empty.value[1] != (ListPattern(()),) or len(nonempty.value[1]) != 1:
        return None
    pattern = nonempty.value[1][0]
    if not isinstance(pattern, ConsPattern) or not all(isinstance(item, str) and item != "_" for item in (pattern.head, pattern.tail)):
        return None
    if node.value in (pattern.head, pattern.tail):
        return None
    base_block, recursive_block = empty.children[0], nonempty.children[0]
    if len(base_block.children) != 1 or len(recursive_block.children) != 1:
        return None
    base_statement, body_statement = base_block.children[0], recursive_block.children[0]
    base = base_statement.children[0] if base_statement.kind == "observe" else base_statement
    body = body_statement.children[0] if body_statement.kind == "observe" else body_statement
    if base.kind != "literal" or type(base.value) not in {int, float}:
        return None
    if body.kind != "binary" or body.value not in {"+", "-", "*", "/", "%"}:
        return None
    head, recursive = body.children
    if head.kind != "ref" or head.value != pattern.head:
        return None
    if recursive.kind != "call" or recursive.value != node.value or len(recursive.children) != 1:
        return None
    tail = recursive.children[0]
    if tail.kind != "ref" or tail.value != pattern.tail:
        return None
    from .compiler import _literal
    from .semantics import _binary, _error, observe_statement

    # The generated loop keeps recursive evaluation's right-to-left arithmetic,
    # including overflow/floating-point behavior, without frames or tail slices.
    source = '''def fold(context, arguments, call_node):
    items = arguments[0]
    if not isinstance(items, list):
        raise error(context, call_node, "no matching clause for " + name)
    for index in range(len(items)):
        context.tick(group)
        for step in descent:
            context.tick(step)
    context.tick(group)
    context.tick(base_block)
    context.tick(base)
    result = literal(context, base, initial)
    if observe_base:
        observe(context, base, result)
    for index in range(len(items) - 1, -1, -1):
        context.tick(body)
        result = binary(context, operator, items[index], result, body)
        if observe_body:
            observe(context, body, result)
    return result
'''
    namespace = {
        "__builtins__": {}, "isinstance": isinstance, "list": list, "range": range, "len": len,
        "error": _error, "binary": _binary, "literal": _literal, "name": node.value,
        "initial": base.value, "operator": body.value, "base": base, "base_block": base_block,
        "body": body, "descent": (recursive_block, body, head, recursive, tail),
        "observe": observe_statement, "observe_base": base_statement.kind == "observe",
        "observe_body": body_statement.kind == "observe",
        "group": node,
    }
    module = ast.parse(source)
    exec(compile(module, "<ctk-pattern-right-fold>", "exec"), namespace)
    function = namespace["fold"]
    function.__ctk_source__ = ast.unparse(module)
    return function
