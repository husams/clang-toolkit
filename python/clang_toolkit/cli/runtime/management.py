"""Console controls for live server resources and local lexical bindings."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from google.protobuf.timestamp_pb2 import Timestamp
from lark import Token, Tree

from clang_toolkit._generated.match.v1 import match_service_pb2 as pb
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


def _bytes(value: int) -> str:
    """Format byte counters with binary units and readable precision."""
    if value < 1024**2:
        amount, unit = value / 1024, "KiB"
    elif value < 1024**3:
        amount, unit = value / 1024**2, "MiB"
    else:
        amount, unit = value / 1024**3, "GiB"
    return f"{amount:.2f} {unit}"


def _duration(milliseconds: int) -> str:
    seconds, millis = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    if days:
        return f"{days}d {hours:02}:{minutes:02}:{seconds:02}"
    if hours:
        return f"{hours}:{minutes:02}:{seconds:02}"
    return f"{minutes}:{seconds:02}.{millis:03}"


def _timestamp(value: Timestamp, *, present: bool) -> str:
    return value.ToJsonString() if present else "Unavailable"


def _table(rows: list[tuple[str, str]]) -> str:
    width = max((len(label) for label, _ in rows), default=0)
    return "\n".join(f"{label:<{width}}  {value}" for label, value in rows)


def _cache_rows(cache: pb.CacheResources) -> list[tuple[str, str]]:
    return [
        ("Memory cache", "Available" if cache.memory_available else "Unavailable"),
        ("Reusable snapshots", str(cache.reusable_snapshots) if cache.memory_available else "Unavailable"),
        ("Reusable memory", _bytes(cache.reusable_memory_bytes) if cache.memory_available else "Unavailable"),
        ("Pending builds", str(cache.pending_builds) if cache.memory_available else "Unavailable"),
        ("Storage", "Available" if cache.storage_available else "Unavailable"),
        ("Artifact disk", _bytes(cache.artifact_disk_bytes) if cache.storage_available else "Unavailable"),
        ("Ready snapshots", str(cache.ready_snapshots) if cache.storage_available else "Unavailable"),
        ("Stale snapshots", str(cache.stale_snapshots) if cache.storage_available else "Unavailable"),
        ("Leased snapshots", str(cache.leased_snapshots) if cache.storage_available else "Unavailable"),
        ("Storage root", (cache.storage_root or "Unavailable") if cache.storage_available else "Unavailable"),
    ]


def _render_status(status: pb.ServerStatusResponse) -> str:
    rss = (_bytes(status.resident_memory_bytes)
           if status.HasField("resident_memory_bytes") else "Unavailable")
    rows = [
        ("Uptime", _duration(status.uptime_ms)),
        ("Resident memory", rss),
        ("Active sessions", str(status.active_sessions)),
        ("Retained memory", _bytes(status.retained_memory_bytes)),
        ("Session limit", str(status.max_sessions)),
        ("Retained memory limit", _bytes(status.max_retained_memory_bytes)),
    ]
    return "Server status\n" + _table(rows) + "\n\nCache resources\n" + _table(_cache_rows(status.cache))


def _render_sessions(response: pb.ListSessionsResponse) -> str:
    if not response.sessions:
        return "No active sessions."
    sections = []
    for index, session in enumerate(response.sessions, start=1):
        bindings = ", ".join(session.binding_names) if session.binding_names else "None"
        sections.append(f"Session {index}\n" + _table([
            ("ID", session.session_id or "Unavailable"),
            ("File", session.file_path or "Unavailable"),
            ("Revision", str(session.result_revision)),
            ("Rows", str(session.row_count)),
            ("Bindings", bindings),
            ("Expires", _timestamp(session.expires_at, present=session.HasField("expires_at"))),
        ]))
    return "\n\n".join(sections)


def _render_prune(response: pb.PruneCachesResponse) -> str:
    return ("Cache prune results\nBefore\n" + _table(_cache_rows(response.before)) +
            "\n\nAfter\n" + _table(_cache_rows(response.after)))


def execute_management(runtime: Runtime, statement: Tree) -> str:
    from .evaluator import EvaluationError
    kind = str(statement.data)
    if kind == "bindings_list":
        rows: list[tuple[str, str]] = []
        for name, value in sorted(runtime.bindings.items()):
            details = type(value).__name__
            if isinstance(value, (ParsedTree, MatchValue, BindingSelection)):
                details += f" | session {value._owner.session_id} | " + ("closed" if value._owner.closed else "open")
            rows.append((f"${name}", details))
        return "No bindings." if not rows else "Bindings\n" + _table(rows)
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
    if kind == "server_status":
        return _render_status(response)
    if kind == "cache_status":
        return "Cache status\n" + _table(_cache_rows(response))
    if kind == "session_list":
        return _render_sessions(response)
    return _render_prune(response)
