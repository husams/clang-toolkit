"""Lower shared CTK resource and cursor commands to the local native controller."""

from __future__ import annotations

import json

from lark import Tree

from .jit_analysis import LowerValue
from .jit_language import LanguageIR

LOCAL_COMMANDS = {
    "files_expression",
    "file_open",
    "file_list",
    "file_info",
    "file_close",
    "file_refresh",
    "resource_status",
    "cursor_open",
    "cursor_continue",
    "cursor_restart",
    "cursor_close",
    "session_list",
    "session_attach",
    "session_close_retained",
    "server_status",
    "cache_status",
    "cache_prune",
    "script",
}


def _cursor_options(kind: str, items: list[Tree]) -> str:
    options: dict[str, str | int] = {}
    scopes = {"root_only": 1, "subtree": 2, "children": 3}
    for item in items:
        raw = str(item.children[1])
        key = {
            "cursor_row": "match_index",
            "cursor_scope": "scope",
            "cursor_revision": "expected_result_revision",
        }[str(item.data)]
        if key in options:
            raise ValueError(f"duplicate cursor option {key}")
        if key == "scope":
            if raw not in scopes:
                raise ValueError("scope must be root_only, subtree or children")
            options[key] = scopes[raw]
        else:
            if not raw.isdigit() or int(raw) >= 1 << 64:
                raise ValueError("cursor row/revision must be an unsigned integer")
            if key == "expected_result_revision" and int(raw) == 0:
                raise ValueError("cursor revision must be positive")
            options[key] = raw
    if kind != "cursor_continue" and options.keys() & {"scope", "match_index"}:
        raise ValueError("row and scope require cursor continue")
    if kind == "cursor_open" and "expected_result_revision" in options:
        raise ValueError("revision requires an existing cursor")
    return json.dumps(options, separators=(",", ":"))


def lower_operation(ir: LanguageIR, tree: Tree, mode: str, lower: LowerValue) -> str:
    kind = str(tree.data)
    parts = tree.children
    operands = []
    destination = None
    options = ""
    if kind == "script":
        operands = parts[1::2]
    elif kind == "files_expression":
        operands = parts[1:2]
    elif kind == "file_list" and len(parts) > 2:
        operands = parts[-1:]
    elif kind in {"file_open", "file_refresh", "session_attach"}:
        operands = parts[2:3]
        if len(parts) == 5:
            destination = parts[4]
    elif kind in {"file_info", "session_close_retained", "cursor_close"}:
        operands = parts[2:3]
    elif kind == "file_close" and parts[2] != "all":
        operands = parts[2:3]
    elif kind == "cache_prune":
        options = str(parts[2]) if len(parts) > 2 else "memory"
        if options not in {"memory", "disk", "all"}:
            raise ValueError(
                "cache prune requires memory, disk or all (default memory)"
            )
    elif kind in {"cursor_open", "cursor_continue", "cursor_restart"}:
        end = 5 if kind == "cursor_continue" else 4
        operands = parts[2:end]
        options = _cursor_options(kind, parts[end:])

    arguments = ir.collection(0)
    for item in operands:
        ir.value("add", arguments, "null", lower(ir, item))
    value = ir.call(
        "ctk_jit_local_operation_v1",
        "ptr",
        ("ptr", "%context"),
        ("ptr", ir.string(kind)),
        ("ptr", arguments),
        ("ptr", ir.string(options)),
        ("i32", int(mode == "statement")),
    )
    if destination is not None:
        if destination.data != "reference" or len(destination.children) != 2:
            raise ValueError("target must be a simple variable such as $source")
        ir.define(str(destination.children[1]), value)
    return value
