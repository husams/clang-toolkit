"""Bounded, read-only snapshots for workspace panels; no RPCs during rendering."""

from __future__ import annotations

import json
import posixpath
from pathlib import PurePosixPath
from collections.abc import Mapping
from dataclasses import dataclass, field as dataclass_field
from itertools import islice
from typing import Any
from google.protobuf.message import Message

from clang_toolkit.cli.runtime.references import (
    field_names,
    index_value,
    property_value,
)
from clang_toolkit.cli.runtime.semantic import (
    BindingMapView, MapView, MessageView, RepeatedView, field_sources, view,
)
from clang_toolkit.cli.runtime.values import MatchSet
from clang_toolkit.match_values import (
    BindingSelection,
    MatchValue,
    MatchRow,
    NativeBindingCollection,
    NativeMatchCollection,
)
from clang_toolkit.resources import FileSet, InputDescriptor
from clang_toolkit.cli.workspace_source_data import SourceTarget, source_target, binding_label

MAX_OUTLINE_ROWS = 300
MAX_CHILDREN = 50
MAX_DEPTH = 8


@dataclass(frozen=True)
class PanelEntry:
    identity: str
    label: str
    depth: int = 0
    expandable: bool = False
    commands: tuple[tuple[str, str], ...] = ()
    page: tuple[str, int] | None = None
    source: SourceTarget | None = None


@dataclass(frozen=True)
class FileInventory:
    files: tuple[Any, ...]

    def __len__(self) -> int:
        return len(self.files)


@dataclass(frozen=True)
class SessionInventory:
    sessions: RepeatedView

    def __len__(self) -> int:
        return len(self.sessions)


@dataclass
class _FileBranch:
    folders: dict[str, _FileBranch] = dataclass_field(default_factory=dict)
    leaves: list[tuple[int, str]] = dataclass_field(default_factory=list)


def display_snapshot(
    kind: str, value: Any, expanded: frozenset[str], pages: Mapping[str, int]
) -> list[PanelEntry] | None:
    """Recognize typed result displays; never infer structure from printed JSON."""
    if kind == "bindings_list":
        return outline_snapshot(value, expanded, pages)
    if kind == "file_list" and isinstance(value, tuple):
        value = FileInventory(value)
    if kind == "session_list" and isinstance(value, MessageView):
        value = SessionInventory(property_value(value, "sessions"))
    if isinstance(value, FileSet | FileInventory):
        title = "Files"
    elif isinstance(value, SessionInventory):
        title = "Sessions"
    elif isinstance(value, MatchValue | MatchSet | NativeMatchCollection | NativeBindingCollection | MatchRow | BindingSelection):
        title = "Matches"
    elif isinstance(value, list | tuple | RepeatedView):
        title = "List"
    elif isinstance(value, dict | MapView | BindingMapView):
        title = "Dictionary"
    else:
        return None
    return outline_snapshot({title: value}, expanded, pages)


def compact(value: str, width: int = 110) -> str:
    cleaned = "".join(char if char.isprintable() else " " for char in value)
    return cleaned[:width] + ("…" if len(cleaned) > width else "")


def outline_snapshot(
    bindings: Mapping[str, Any],
    expanded: frozenset[str],
    pages: Mapping[str, int] | None = None,
) -> list[PanelEntry]:
    """Read only expanded local values; never enumerate a whole retained result."""
    rows: list[PanelEntry] = []

    def visit(reference: str, name: str, value: Any, depth: int) -> None:
        if len(rows) >= MAX_OUTLINE_ROWS:
            return
        if isinstance(value, Message):
            value = view(value)
        semantic_row = value._message() if isinstance(value, MessageView) and value.descriptor.full_name == "ctk.match.v1.MatchResult" else None
        if value is None or isinstance(value, (str, bool, int, float)):
            rows.append(
                PanelEntry(
                    reference,
                    compact(f"{name} = {value!r}", 4096),
                    depth,
                    commands=(("p", f"print {reference}"),),
                )
            )
            return
        mapping = type(value) is dict or isinstance(value, MapView | BindingMapView)
        sequence = isinstance(
            value,
            (
                list,
                tuple,
                RepeatedView,
                MatchValue,
                NativeMatchCollection,
                NativeBindingCollection,
                MatchSet,
                FileSet,
                FileInventory,
                SessionInventory,
            ),
        )
        count = (
            len(value.rows)
            if isinstance(value, MatchSet)
            else len(value)
            if sequence or mapping
            else None
        )
        type_name = value.descriptor.name if isinstance(value, MessageView) else type(value).__name__
        label = f"{name} · {type_name}" + (
            f" [{count}]" if count is not None else ""
        )
        if isinstance(value, InputDescriptor):
            label = f"{name} · {value.path}"
        elif isinstance(value, FileInventory):
            label = f"{name} · open files [{count}]"
        elif isinstance(value, SessionInventory):
            label = f"{name} [{count}]"
        elif isinstance(value, RepeatedView):
            label = f"{name} [{count}]"
        elif isinstance(value, BindingSelection):
            def detail(field: str) -> str | None:
                try:
                    result = property_value(value, field)
                except (ValueError, TypeError, KeyError, IndexError):
                    return None
                return str(result) if result else None

            declaration = detail("qualified_name") or detail("decl_name")
            declaration_type = detail("decl_type")
            label = f"{name} - {declaration or '(unnamed)'}"
            if declaration_type:
                label += f" · {declaration_type}"
        elif isinstance(value, MessageView) and value.descriptor.full_name == "ctk.match.v1.MatchBinding":
            label = binding_label(name, value._message())
        rows.append(
            PanelEntry(
                reference, compact(label, 4096), depth, depth < MAX_DEPTH, (("p", f"print {reference}"),),
                source=source_target(value, name),
            )
        )
        if reference not in expanded or depth >= MAX_DEPTH:
            return
        if sequence or mapping:
            total = count or 0
            last_page = max(0, (total - 1) // MAX_CHILDREN)
            page = min(last_page, max(0, (pages or {}).get(reference, 0)))
            start = page * MAX_CHILDREN
            stop = min(total, start + MAX_CHILDREN)
            if total > MAX_CHILDREN:
                rows.append(
                    PanelEntry(
                        reference + ":page",
                        f"Items {start + 1}–{stop} of {total} · Page {page + 1}/{last_page + 1}",
                        depth + 1,
                    )
                )
            if page > 0:
                rows.append(
                    PanelEntry(
                        reference + ":previous",
                        "‹ Previous page · Enter",
                        depth + 1,
                        page=(reference, page - 1),
                    )
                )
            if isinstance(value, FileSet | FileInventory):
                files = [
                    (
                        index,
                        value.inputs[index].path if isinstance(value, FileSet)
                        else value.files[index].input.file_path,
                    )
                    for index in range(start, stop)
                ]
                if files:
                    parents = [str(PurePosixPath(path).parent) for _, path in files]
                    base = posixpath.commonpath(parents) if len({path.startswith('/') for path in parents}) == 1 else ""
                    groups = _FileBranch()
                    for index, path in files:
                        parent = groups
                        relative = PurePosixPath(path).relative_to(base) if base else PurePosixPath(path)
                        for part in relative.parts[:-1]:
                            parent = parent.folders.setdefault(part, _FileBranch())
                        parent.leaves.append((index, path))

                    def directory(children: _FileBranch, path: str, level: int) -> None:
                        if len(rows) >= MAX_OUTLINE_ROWS:
                            return
                        identity = reference + ":dir:" + path
                        rows.append(PanelEntry(identity, compact(path if level == depth + 1 else PurePosixPath(path).name, 4096), level, level < MAX_DEPTH))
                        if identity not in expanded or level >= MAX_DEPTH:
                            return
                        for folder, nested in sorted(children.folders.items()):
                            directory(nested, posixpath.join(path, folder), level + 1)
                        for index, path in children.leaves:
                            child = value.inputs[index] if isinstance(value, FileSet) else value.files[index]
                            child_reference = f"{reference}.inputs[{index}]" if isinstance(value, FileSet) else f"{reference}[{index}]"
                            visit(child_reference, f"[{index}] · {PurePosixPath(path).name}", child, level + 1)

                    directory(groups, base or ".", depth + 1)
            elif mapping:
                for field in islice(value, start, stop):
                    key = json.dumps(field, ensure_ascii=False)
                    visit(f"{reference}[{key}]", field, index_value(value, field), depth + 1)
            else:
                for index in range(start, stop):
                    if isinstance(value, SessionInventory):
                        child = index_value(value.sessions, index)
                    elif isinstance(value, tuple):
                        child = value[index]
                    else:
                        child = index_value(value, index)
                    name = f"[{index}]"
                    if isinstance(value, SessionInventory):
                        name += f" · {property_value(child, 'session_id')} · {PurePosixPath(property_value(child, 'file_path')).name}"
                    visit(f"{reference}[{index}]", name, child, depth + 1)
            if page < last_page:
                rows.append(
                    PanelEntry(
                        reference + ":next",
                        "Next page › · Enter",
                        depth + 1,
                        page=(reference, page + 1),
                    )
                )
            return
        if isinstance(value, BindingSelection):
            names = tuple(property_value(value, "keys"))
        elif isinstance(value, MatchRow):
            names = tuple(sorted(value.bindings))
        elif semantic_row is not None:
            names = tuple(sorted(semantic_row.bindings))
        elif isinstance(value, MapView | BindingMapView) or type(value) is dict:
            names = tuple(value)
        elif isinstance(value, MessageView):
            ast_fields = field_sources(value)
            names = tuple(name for name in field_names(value) if name in ast_fields)
        else:
            names = field_names(value)
        if isinstance(value, BindingSelection):
            preferred = (
                "decl_name",
                "decl_type",
                "qualified_name",
                "name",
                "kind",
                "location",
                "range",
                "return_type",
                "parameters",
                "documentation",
            )
            names = tuple(name for name in preferred if name in names) + tuple(
                name for name in names if name not in preferred
            )
        semantic = view(value.value) if isinstance(value, BindingSelection) else None
        ast_names = field_sources(semantic) if semantic is not None else {}
        if semantic is not None:
            names = tuple(
                name for name in names
                if name not in {"parameter_name", "record_name", "type_name"} or name in ast_names
            )
        for field in names[:MAX_CHILDREN]:
            # Collection methods are actions, not properties. Dictionary keys
            # may legitimately use the same name as one of those methods.
            if field in {
                "hasField",
                "fieldState",
                "fieldOr",
                "unique",
                "sort",
                "filter",
                "push",
                "pop",
                "insert",
                "remove",
                "clear",
                "joinWith",
                "get",
                "set",
                "delete",
                "hasKey",
            } and not (type(value) is dict or isinstance(value, BindingSelection | MatchRow | MapView | BindingMapView | MessageView)):
                continue
            key = (
                f"[{json.dumps(field, ensure_ascii=False)}]"
                if isinstance(value, MapView | BindingMapView) or type(value) is dict
                else f".{field}"
            )
            # Selector properties such as name/value belong to the Python
            # carrier too. Use its semantic projection for real AST fields.
            ast_field = semantic is not None and field in ast_names
            if ast_field and field in {"name", "value", "scope", "source_file"}:
                key = ".value" + key
            if isinstance(value, MatchRow) and field in {"bindings", "source_file", "source_match_index"}:
                key = f".bindings[{json.dumps(field, ensure_ascii=False)}]"
            if semantic_row is not None:
                key = f".bindings[{json.dumps(field, ensure_ascii=False)}]"
            try:
                if isinstance(value, MatchRow):
                    child = value.binding(field)
                elif semantic_row is not None:
                    child = view(semantic_row.bindings[field])
                elif ast_field:
                    child = property_value(semantic, field)
                elif isinstance(value, MapView | BindingMapView) or type(value) is dict:
                    child = index_value(value, field)
                else:
                    child = property_value(value, field)
            except (ValueError, TypeError, KeyError, IndexError) as exc:
                rows.append(
                    PanelEntry(
                        reference + key,
                        compact(f"{field} · unavailable: {exc}"),
                        depth + 1,
                    )
                )
            else:
                visit(reference + key, field, child, depth + 1)
        if len(names) > MAX_CHILDREN:
            rows.append(
                PanelEntry(
                    reference + ":more", "… more properties; use inspect", depth + 1
                )
            )

    for name, value in sorted(bindings.items())[:100]:
        try:
            visit("$" + name, "$" + name, value, 0)
        except (ValueError, TypeError, KeyError, IndexError) as exc:
            rows.append(
                PanelEntry("$" + name, compact(f"${name} · unavailable: {exc}"))
            )
    if len(rows) >= MAX_OUTLINE_ROWS:
        rows = rows[:MAX_OUTLINE_ROWS]
        rows[-1] = PanelEntry(
            ":limit", "Outline limited to 300 rows; collapse a branch"
        )
    return rows


def resource_snapshot(
    files: tuple[Any, ...], sessions: Any, attach_name: str,
    expanded: frozenset[str] | None = None,
) -> list[PanelEntry]:
    """Commands preserve the server's explicit lease/cursor identity."""
    rows = [PanelEntry(":files", f"Open files · file list [{len(files)}]", expandable=True)]
    for item in files[:100]:
        quoted = json.dumps(item.lease_id)
        commands = (("c", f"file close {quoted}"),) if item.lease_id else ()
        rows.append(
            PanelEntry(
                "file:" + (item.lease_id or item.snapshot_id),
                compact(
                    f"{PurePosixPath(item.input.file_path).name} · leases {item.explicit_leases} · cursors {item.cursor_count}"
                ),
                1,
                True,
                commands,
            )
        )
        rows.append(
            PanelEntry(
                ":file-detail:" + item.snapshot_id,
                f"work {item.active_work} · native {item.accounted_native_bytes / 1024**2:.1f} MiB",
                2,
            )
        )
    if not files:
        rows.append(PanelEntry(":no-files", "No open files", 1))
    rows.append(PanelEntry(":sessions", f"Retained sessions · session list [{len(sessions.sessions)}]", expandable=True))
    for item in sessions.sessions[:100]:
        quoted = json.dumps(item.session_id)
        rows.append(
            PanelEntry(
                "session:" + item.session_id,
                compact(
                    f"{item.session_id[:12]} · {item.row_count} rows · {', '.join(item.binding_names)}"
                ),
                1,
                True,
                (
                    ("a", f"session attach {quoted} into ${attach_name}"),
                    ("c", f"session close {quoted}"),
                ),
            )
        )
        rows.append(
            PanelEntry(
                ":session-detail:" + item.session_id,
                compact(
                    f"{PurePosixPath(item.file_path).name} · revision {item.result_revision}"
                ),
                2,
            )
        )
    if not sessions.sessions:
        rows.append(PanelEntry(":no-sessions", "No retained sessions", 1))
    if len(files) > 100 or len(sessions.sessions) > 100:
        rows.append(
            PanelEntry(":limit", "Inventory limited to 100 of each; use list commands")
        )
    if expanded is None:
        return rows
    visible: list[PanelEntry] = []
    hidden_depth: int | None = None
    for row in rows:
        if hidden_depth is not None and row.depth > hidden_depth:
            continue
        hidden_depth = None
        visible.append(row)
        if row.expandable and row.identity not in expanded:
            hidden_depth = row.depth
    return visible
