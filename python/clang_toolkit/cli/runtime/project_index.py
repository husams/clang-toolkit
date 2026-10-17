"""Background project index controls; no native AST work happens in this client."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from lark import Token, Tree

from clang_toolkit._generated.index.v1 import index_service_pb2 as pb

if TYPE_CHECKING:
    from .evaluator import Runtime


def execute_project_index(runtime: Runtime, node: Tree) -> tuple[Any, str]:
    from .semantic import view

    strings = [runtime._string(str(child)) for child in node.children
               if isinstance(child, Token) and child.type == "STRING"]
    root = Path(strings[-1]).expanduser()
    project = str(root if root.is_absolute() else runtime.cwd / root)
    # Normalize local console paths lexically without requiring them to exist.
    project = os.path.normpath(project)
    kind = str(node.data)
    if kind in {"index_find", "index_lookup"}:
        operation = (runtime.client.find_symbols if kind == "index_find"
                     else runtime.client.lookup_symbol)
        result = operation(project, strings[0])
        lines = [f"Symbol index revision {result.revision}" +
                 (" (stale)" if result.stale else "")]
        lines.extend(f"{symbol.qualified_name}  {symbol.file_path}:{symbol.line}:{symbol.column}"
                     for symbol in result.symbols)
        if not result.symbols:
            lines.append("No symbols in the indexed coverage.")
    else:
        method = {
            "index_start": "start_project_index", "index_status": "project_index_status",
            "index_pause": "pause_project_index", "index_resume": "resume_project_index",
            "index_cancel": "cancel_project_index",
        }[kind]
        commands = runtime.config_store.effective.get("compile_commands", "")
        if kind == "index_start" and commands:
            result = runtime.client.start_project_index(project, compile_commands=commands)
        else:
            result = getattr(runtime.client, method)(project)
        state = pb.IndexState.Name(result.state).removeprefix("INDEX_STATE_")
        lines = [f"Project index {state}", f"Project  {result.project_root}",
                 f"Indexed  {result.translation_units_indexed}/{result.translation_units_total}",
                 f"Pending  {result.translation_units_pending}",
                 f"Failed   {result.translation_units_failed}",
                 f"Revision {result.revision}"]
        if result.current_translation_unit:
            lines.append(f"Current  {result.current_translation_unit}")
        if result.paused_reason:
            lines.append(result.paused_reason)
        if result.error:
            lines.append(result.error)
    return view(result), "\n".join(lines)
