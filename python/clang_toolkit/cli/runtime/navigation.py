"""Direct navigation from retained references, with no implicit current node."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any
from google.protobuf.json_format import MessageToJson
from lark import Tree, Token
from clang_toolkit.match_values import BindingSelection
from .values import MatcherExpr, matcher_text

if TYPE_CHECKING:
    from .evaluator import Runtime


def execute_navigation(runtime: Runtime, statement: Tree) -> Any:
    from .evaluator import EvaluationError

    axis = str(statement.children[1])
    if axis not in {"children", "parents"}:
        raise EvaluationError("navigation axis must be children or parents")
    target = None
    query = None
    at = None
    max_nodes = 10000
    seen_limit = False
    for index, child in enumerate(statement.children[2:], start=2):
        if isinstance(child, Tree):
            if child.data == "reference":
                target = runtime._evaluate(child)
            elif child.data == "navigation_nodes":
                if seen_limit:
                    raise EvaluationError("duplicate navigation nodes option")
                seen_limit = True
                raw = str(child.children[1])
                if not raw.isdigit() or not 1 <= int(raw) <= 100000:
                    raise EvaluationError("navigation nodes must be 1..100000")
                max_nodes = int(raw)
            else:
                matcher = runtime._evaluate(child)
                if not isinstance(matcher, MatcherExpr):
                    raise EvaluationError("navigation requires a matcher expression")
                query = matcher_text(matcher)
        elif isinstance(child, Token) and child.type == "AT":
            raw = str(statement.children[index + 1])
            if not raw.isdigit():
                raise EvaluationError("navigation index must be a zero-based integer")
            at = int(raw)
    if not isinstance(target, BindingSelection):
        raise EvaluationError("navigation requires a retained native binding")
    options = dict(axis=axis, query=query, max_nodes=max_nodes)
    if runtime._active_resource_scope is not None:
        options["scope"] = runtime._active_resource_scope
    if statement.data == "step":
        return runtime.client.step(target, at=at, **options)

    def emit(row):
        text = runtime._emit_output(
            MessageToJson(row, preserving_proto_field_name=True))
        if text:
            print(text, flush=True)

    return runtime.client.peek(
        target, **options,
        **({"on_row": emit} if not runtime._value_context_depth else {}))
