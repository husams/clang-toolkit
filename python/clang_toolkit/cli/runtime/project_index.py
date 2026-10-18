"""Background project index controls; no native AST work happens in this client."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING, Any

from lark import Token, Tree

from clang_toolkit._generated.index.v1 import index_service_pb2 as pb

if TYPE_CHECKING:
    from .evaluator import Runtime


def _symbol_lines(result: pb.FindSymbolsResponse) -> list[str]:
    lines = [f"Symbol index revision {result.revision}" +
             (" (stale)" if result.stale else "")]
    lines.extend(f"{symbol.qualified_name}  {symbol.file_path}:{symbol.line}:{symbol.column}"
                 for symbol in result.symbols)
    if not result.symbols:
        lines.append("No symbols in the indexed coverage.")
    if result.truncated:
        lines.append("Results truncated at 100 matches; narrow the name prefix.")
    return lines


def execute_project_index(runtime: Runtime, node: Tree) -> tuple[Any, str]:
    from .semantic import view

    if str(node.data) == "index_list":
        result = runtime.client.list_project_indexes()
        lines = ["Indexed projects"]
        rows = [("Project", "Path", "State", "Indexed", "Reused", "Newly indexed", "Indexing")]
        for project in result.projects:
            state = pb.IndexState.Name(project.state).removeprefix("INDEX_STATE_")
            rows.append((Path(project.project_root).name or project.project_root,
                         project.project_root, state,
                         f"{project.translation_units_indexed}/{project.translation_units_total} indexed",
                         str(project.translation_units_skipped),
                         str(max(0, project.translation_units_completed - project.translation_units_skipped)),
                         str(project.translation_units_indexing)))
        widths = [max(len(row[column]) for row in rows) for column in range(len(rows[0]))]
        lines.extend("  ".join(value.ljust(width) for value, width in zip(row, widths)).rstrip()
                     for row in rows)
        if not result.projects:
            lines.append("No indexed projects.")
        lines.append(f"Total projects: {result.total_count}")
        return view(result), "\n".join(lines)

    strings = [runtime._string(str(child)) for child in node.children
               if isinstance(child, Token) and child.type == "STRING"]
    kind = str(node.data)
    if kind == "index_find":
        query = strings[0]
        exact = any(isinstance(child, Token) and child.type == "EXACT" for child in node.children)
        if not exact:
            query = query.removesuffix("*")
            if not query or any(char in query for char in "*?[]"):
                raise ValueError("Use a nonempty name prefix with an optional trailing *; "
                                 "other wildcard patterns are not supported. Use exact for literal names.")
        if len(strings) == 1 or strings[1] == "*":
            from clang_toolkit.cursors import CursorError

            roots = sorted({item.project_root for item in runtime.client.list_project_indexes().projects})
            values = []
            lines = [f"Symbol search across {len(roots)} projects"]
            for root in roots:
                lines.append(f"Project  {root}")
                try:
                    result = runtime.client.find_symbols(root, query, prefix=not exact)
                except CursorError as error:
                    values.append({"project_root": root, "result": None, "error": str(error)})
                    lines.append(f"Search failed: {error}")
                    continue
                values.append({"project_root": root, "result": view(result), "error": ""})
                lines.extend(_symbol_lines(result))
            if not roots:
                lines.append("No indexed projects.")
            return values, "\n".join(lines)
    target = strings[-1]
    if (str(node.data) in {"index_status", "index_find"} and target not in {"", ".", "..", "~"}
            and "/" not in target and not target.startswith("~")):
        projects = runtime.client.list_project_indexes().projects
        matches = sorted({item.project_root for item in projects
                          if Path(item.project_root).name == target})
        if len(matches) > 1:
            raise ValueError(
                f"Ambiguous project name {target!r}; use a full path: " + ", ".join(matches))
        if not matches:
            raise ValueError(
                f"No indexed project named {target!r}; use index list or an explicit path.")
        target = matches[0]
    root = Path(target).expanduser()
    project = str(root if root.is_absolute() else runtime.cwd / root)
    # Normalize local console paths lexically without requiring them to exist.
    project = os.path.normpath(project)
    kind = str(node.data)
    if kind in {"index_find", "index_lookup"}:
        operation = (runtime.client.find_symbols if kind == "index_find"
                     else runtime.client.lookup_symbol)
        result = (operation(project, query, prefix=not exact) if kind == "index_find"
                  else operation(project, strings[0]))
        lines = _symbol_lines(result)
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
                 f"Reused   {result.translation_units_skipped}",
                 f"Newly indexed {max(0, result.translation_units_completed - result.translation_units_skipped)}",
                 f"Indexing {result.translation_units_indexing}",
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
