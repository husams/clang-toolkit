"""Evaluate the formal cursor commands without embedding another parser."""

from __future__ import annotations

from typing import TYPE_CHECKING

from google.protobuf.json_format import MessageToJson
from lark import Tree

from clang_toolkit._generated.match.v1 import match_result_pb2, match_service_pb2

from .values import MatcherExpr, matcher_text

if TYPE_CHECKING:
    from .evaluator import Runtime


def execute_cursor(runtime: Runtime, statement: Tree) -> str:
    from .evaluator import EvaluationError

    kind = str(statement.data)
    identifier = runtime._string(str(statement.children[2]))
    if kind == "cursor_close":
        runtime.client.close_match(identifier)
        return ""
    matcher_index = 4 if kind == "cursor_continue" else 3
    matcher = runtime._evaluate(statement.children[matcher_index])
    if not isinstance(matcher, MatcherExpr):
        raise EvaluationError("cursor command requires a matcher expression")
    query = matcher_text(matcher)
    options: dict[str, int] = {}
    scope_names = {
        "root_only": match_result_pb2.BINDING_MATCH_SCOPE_ROOT_ONLY,
        "subtree": match_result_pb2.BINDING_MATCH_SCOPE_SUBTREE,
    }
    for option in statement.children[matcher_index + 1:]:
        if not isinstance(option, Tree):
            continue
        option_kind = str(option.data)
        text = str(option.children[1])
        key = {
            "cursor_row": "match_index", "cursor_scope": "scope",
            "cursor_revision": "expected_result_revision",
        }[option_kind]
        if key in options:
            raise EvaluationError(f"duplicate cursor option {key}")
        if key == "scope":
            if text not in scope_names:
                raise EvaluationError("scope must be root_only or subtree")
            value = scope_names[text]
        else:
            if not text.isdigit() or int(text) > 2**64 - 1:
                raise EvaluationError("cursor row/revision must be an unsigned integer")
            value = int(text)
            if key == "expected_result_revision" and value == 0:
                raise EvaluationError("cursor revision must be positive")
        options[key] = value
    if kind != "cursor_continue" and any(key in options for key in ("scope", "match_index")):
        raise EvaluationError("row and scope require cursor continue")
    traversal = runtime.config_store.effective.get("traversal", "as_is")
    options["traversal_mode"] = (
        match_service_pb2.MATCH_TRAVERSAL_MODE_IGNORE_UNLESS_SPELLED_IN_SOURCE
        if traversal in {"ignore_unless_spelled_in_source", "IgnoreUnlessSpelledInSource"}
        else match_service_pb2.MATCH_TRAVERSAL_MODE_AS_IS
    )
    if kind == "cursor_open":
        if "expected_result_revision" in options:
            raise EvaluationError("revision requires an existing cursor")
        response = runtime.client.match_file(
            identifier, query, working_directory=runtime.cwd,
            compile_arguments=runtime.config_store.effective["extra_args"], **options,
        )
    elif kind == "cursor_continue":
        bind = runtime._string(str(statement.children[3]))
        response = runtime.client.continue_match(identifier, bind, query, **options)
    else:
        response = runtime.client.restart_match(identifier, query, **options)
    return MessageToJson(response, preserving_proto_field_name=True)
