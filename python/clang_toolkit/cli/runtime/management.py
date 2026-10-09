"""Console controls for live server resources and local lexical bindings."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
import json

from google.protobuf.json_format import MessageToDict
from lark import Token, Tree

from clang_toolkit.match_values import BindingSelection, MatchValue, ParsedTree

if TYPE_CHECKING:
    from .evaluator import Runtime


def variable_name(node: Any) -> str:
    from .evaluator import EvaluationError
    if (not isinstance(node, Tree) or node.data != "reference" or
            len(node.children) != 2):
        raise EvaluationError("binding target must be a simple $variable")
    return str(node.children[1])


def _session_id(runtime: Runtime, node: Any) -> str:
    from .evaluator import EvaluationError
    value = runtime._evaluate(node)
    if isinstance(value, (ParsedTree, MatchValue, BindingSelection)):
        return value._owner.session_id
    if isinstance(value, str):
        return value
    raise EvaluationError("session requires a UUID string or retained tree/match binding")


def execute_management(runtime: Runtime, statement: Tree) -> str:
    from .evaluator import EvaluationError
    kind = str(statement.data)
    if kind == "bindings_list":
        rows = []
        for name, value in sorted(runtime.bindings.items()):
            row = {"name": name, "type": type(value).__name__}
            if isinstance(value, (ParsedTree, MatchValue, BindingSelection)):
                row.update(session_id=value._owner.session_id, closed=value._owner.closed)
            rows.append(row)
        return json.dumps(rows, ensure_ascii=False, indent=2)
    if kind in {"binding_drop", "binding_rename"}:
        name = variable_name(statement.children[2])
        if name not in runtime.bindings:
            raise EvaluationError(f"undefined binding: ${name}")
        if kind == "binding_rename":
            target = variable_name(statement.children[4])
            if target == name:
                return ""
            if target in runtime.bindings:
                raise EvaluationError(f"binding already exists: ${target}")
            runtime.bindings[target] = runtime.bindings[name]
        del runtime.bindings[name]
        return ""
    if kind == "session_close_retained":
        identity = _session_id(runtime, statement.children[2])
        runtime.client.close_match(identity)
        # Mark aliases closed after RPC success; independent derived cursors survive.
        for value in runtime.bindings.values():
            if isinstance(value, (ParsedTree, MatchValue, BindingSelection)) and value._owner.session_id == identity:
                value._owner.closed = True
        return ""
    if kind == "session_attach":
        name = variable_name(statement.children[4])
        identity = _session_id(runtime, statement.children[2])
        runtime.bindings[name] = runtime.client.attach_session(identity)
        return ""
    if kind == "session_list":
        response = runtime.client.list_sessions()
    elif kind in {"server_status", "cache_status"}:
        response = runtime.client.server_status()
        if kind == "cache_status":
            response = response.cache
    elif kind == "cache_prune":
        selection = next((str(child) for child in statement.children
                          if isinstance(child, Token) and child.type == "NAME"), "memory")
        if selection not in {"memory", "disk", "all"}:
            raise EvaluationError("cache prune requires memory, disk or all (default memory)")
        response = runtime.client.prune_caches(memory=selection in {"memory", "all"},
                                              disk=selection in {"disk", "all"})
    else:
        raise EvaluationError(f"unknown management command: {kind}")
    return json.dumps(MessageToDict(response, preserving_proto_field_name=True,
                                    always_print_fields_with_no_presence=True),
                      ensure_ascii=False, indent=2)
