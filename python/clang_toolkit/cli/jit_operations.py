"""Lower shared CTK resource and cursor commands to the local native controller."""

from __future__ import annotations

import json

from lark import Token, Tree

from .jit_analysis import LowerValue
from .jit_language import LanguageIR
from .runtime.prototype.syntax import Node

INDEX_COMMANDS = {
    "index_list",
    "index_start",
    "index_status",
    "index_rename",
    "index_pause",
    "index_resume",
    "index_cancel",
    "index_find",
    "index_lookup",
}
SESSION_COMMANDS = {
    "session_label",
    "session_start",
    "session_add",
    "session_match",
    "session_pause",
    "session_resume",
    "session_close",
    "background",
}
BATCH_COMMANDS = {
    "durable_batch",
    "batch_statement",
    "batch_status",
    "batch_cancel",
    "batch_resume",
    "batch_retry",
    "batch_promote",
}
LOCAL_COMMANDS = (
    INDEX_COMMANDS
    | SESSION_COMMANDS
    | BATCH_COMMANDS
    | {
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
)


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


def _uint32(raw: str, option: str) -> int:
    if not raw.isdecimal() or not 0 < int(raw) < (1 << 32):
        raise ValueError(f"{option} must be a positive uint32 integer")
    return int(raw)


def _batch(
    ir: LanguageIR, tree: Tree, lower: LowerValue, source: str
) -> tuple[list[str], str]:
    durable = tree.data == "durable_batch"
    parts = tree.children
    name = str(parts[2 if durable else 1])
    manifest = parts[4 if durable else 3]
    options: dict[str, object] = {}
    memory = request_id = "null"
    body = None
    seen = set()
    for item in parts:
        if not isinstance(item, Tree) or item.data == "reference":
            continue
        option = str(item.data)
        if option in seen:
            raise ValueError(f"batch option repeated: {option.removeprefix('batch_')}")
        seen.add(option)
        if option in {"batch_size", "batch_count", "batch_jobs"}:
            label = option.removeprefix("batch_")
            options[label] = _uint32(str(item.children[1]), label)
        elif option == "batch_memory":
            memory = lower(ir, item.children[1])
        elif option == "batch_request_id":
            request_id = lower(ir, item.children[1])
        elif option == "batch_error_mode":
            options["continue_on_error"] = item.children[-1] == "continue"
        elif option == "batch_progress":
            options["progress"] = item.children[-1] == "on"
        elif option == "statement_block":
            body = item
    if body is None:
        raise ValueError("batch requires a body")
    operands = [lower(ir, manifest), memory]
    if durable:
        options["group_variable"] = name
        options["body_source"] = source[body.meta.start_pos + 1 : body.meta.end_pos - 1]
        operands.append(request_id)
    else:
        block = body.children[0]
        if not isinstance(block, Node) or block.kind != "block":
            raise ValueError("batch requires a compiled CTK block")
        operands.append(ir.runnable(Node("inline_runnable", ("", (name,)), (block,))))
    return operands, json.dumps(options, separators=(",", ":"))


def lower_operation(
    ir: LanguageIR, tree: Tree, mode: str, lower: LowerValue, source: str
) -> str:
    kind = str(tree.data)
    parts = tree.children
    operands = []
    compiled_operands: list[str] = []
    destination = None
    options = ""
    if kind in {"durable_batch", "batch_statement"}:
        compiled_operands, options = _batch(ir, tree, lower, source)
    elif kind in BATCH_COMMANDS:
        operands = parts[2:3]
    elif kind in INDEX_COMMANDS:
        operands = [
            part for part in parts if isinstance(part, Token) and part.type == "STRING"
        ]
        if kind == "index_find":
            from .index_kinds import INDEX_SYMBOL_KINDS

            symbol_kind = next(
                (
                    str(part)
                    for part in parts
                    if isinstance(part, Token) and part.type == "NAME"
                ),
                "",
            )
            if symbol_kind and symbol_kind not in INDEX_SYMBOL_KINDS:
                raise ValueError("kind must be function, class, variable, or alias")
            options = json.dumps(
                {
                    "kind": "KIND_" + (symbol_kind.upper() or "ANY"),
                    "match_mode": "MATCH_MODE_EXACT"
                    if "exact" in parts
                    else "MATCH_MODE_PREFIX",
                    "unique_symbols": True,
                }
            )
    elif kind in SESSION_COMMANDS:
        operands = parts[1::2] if kind == "background" else parts[2:3]
    elif kind == "script":
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
    for value in [*compiled_operands, *(lower(ir, item) for item in operands)]:
        if value == "null":
            value = ir.literal(None)
        ir.value("add", arguments, "null", value)
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
