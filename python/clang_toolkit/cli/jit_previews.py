"""Render native command data with the existing console's presentation rules."""

from __future__ import annotations

from typing import Any

from .jit_workspace import projected, wire_message
from .runtime.cursors import render_cursor
from .runtime.file_commands import render_file_command
from .runtime.graph_options import render_graph
from .runtime.management import (
    _cache_rows,
    _render_prune,
    _render_sessions,
    _render_status,
    _table,
)
from .runtime.scripting import render_script_response
from .runtime.semantic import view
from .runtime.values import render, render_inspection
from .jit_workspace_state import ProjectedCollection


def _materialize(value: Any) -> Any:
    if not isinstance(value, ProjectedCollection):
        return value
    if value.kind == "record":
        return {key: _materialize(item) for key, item in value.children}
    items = [_materialize(item) for item in value.children]
    if len(items) < value.count:
        items.append("… <truncated>")
    return tuple(items) if value.kind == "tuple" else items


def render_preview(kind: str, wire: Any) -> str:
    if kind in {"render", "inspect", "batch_statement"}:
        value = _materialize(projected(wire))
        if kind == "inspect":
            return render_inspection(value)
        if kind == "batch_statement":
            from .runtime.batch_execution import render_batch_report

            return render_batch_report(value)
        return render(value)
    if kind == "files_expression":
        return render(projected(wire))
    message = wire_message(wire)
    if kind == "server_status":
        return _render_status(message)
    if kind == "cache_status":
        return "Cache status\n" + _table(_cache_rows(message))
    if kind == "cache_prune":
        return _render_prune(message)
    if kind == "session_list":
        return _render_sessions(message)
    if kind == "file_list":
        value = tuple(message.files) if hasattr(message, "files") else projected(wire)
        return render_file_command(kind, value)
    if kind in {"file_info", "file_close", "resource_status"}:
        return render_file_command(kind, view(message))
    if kind == "script":
        return render_script_response(message)
    if kind.startswith("cursor_"):
        return render_cursor(message)
    if kind == "step":
        return render(view(message))
    return render_graph(view(message))
