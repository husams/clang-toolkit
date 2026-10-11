"""Source links and detached navigation summaries from actual match metadata."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from clang_toolkit._generated.match.v1 import match_result_pb2 as pb
from clang_toolkit.cli.runtime.semantic import MessageView
from clang_toolkit.cli.runtime.values import MatchSet
from clang_toolkit.match_values import (
    BindingSelection, MatchRow, MatchValue, NativeBindingCollection, NativeMatchCollection,
)
from clang_toolkit.batches import DetachedMatchRow

MAX_SOURCE_BYTES = 8_000_000


@dataclass(frozen=True)
class SourceTarget:
    path: str
    line: int
    column: int
    end_line: int
    label: str = ""

    @property
    def location(self) -> str:
        name = "".join(char if char.isprintable() else " " for char in Path(self.path).name)
        return f"{name}:{self.line}:{self.column}"


@dataclass(frozen=True)
class SourceMatch:
    label: str
    target: SourceTarget
    bindings: tuple[SourceTarget, ...]


@dataclass(frozen=True)
class SourceSnapshot:
    path: Path
    text: str
    matches: tuple[SourceMatch, ...]
    notice: str = ""


def source_target(value: Any, label: str = "") -> SourceTarget | None:
    """Only valid physical coordinates become links; no path/line guessing."""
    if isinstance(value, BindingSelection):
        if value._binding_data is None:
            return None
        value = value.value
    if isinstance(value, MessageView):
        value = value._message()
    if isinstance(value, MatchRow | DetachedMatchRow):
        value = value._message()
    if isinstance(value, pb.MatchResult):
        bindings = value.bindings
        for name in ["root", *sorted(key for key in bindings if key != "root")]:
            if name in bindings and (target := source_target(bindings[name], label)):
                return target
        return None
    if isinstance(value, pb.MatchBinding):
        begin = value.range.expansion_begin
        if not begin.valid or not begin.file or not begin.line:
            begin = value.location
        end = value.range.expansion_end
        if not begin.valid or not begin.file or not begin.line:
            return None
        end_line = end.line if end.valid and end.file == begin.file and end.line >= begin.line else begin.line
        return SourceTarget(begin.file, begin.line, max(1, begin.column), end_line, label)
    if isinstance(value, pb.MatchSourcePoint):
        if value.valid and value.file and value.line:
            return SourceTarget(value.file, value.line, max(1, value.column), value.line, label)
    if isinstance(value, pb.MatchSourceRange):
        begin, end = value.expansion_begin, value.expansion_end
        if begin.valid and begin.file and begin.line:
            end_line = end.line if end.valid and end.file == begin.file and end.line >= begin.line else begin.line
            return SourceTarget(begin.file, begin.line, max(1, begin.column), end_line, label)
    return None


def binding_label(name: str, value: pb.MatchBinding) -> str:
    # Semantic helpers traverse the immediate declaration projection only.
    from clang_toolkit.match_values import _binding_decl_name, _binding_decl_type

    declaration = _binding_decl_name(value)
    type_name = _binding_decl_type(value)
    return name + (f" — {declaration}" if declaration else "") + (f" · {type_name}" if type_name else "")


def source_snapshot(target: SourceTarget, values: Iterable[Any], cwd: Path) -> SourceSnapshot:
    """Read on a worker; rendering and navigation never touch disk or RPCs."""
    path = Path(target.path)
    path = (cwd / path).resolve() if not path.is_absolute() else path.resolve()
    with path.open("rb") as stream:
        data = stream.read(MAX_SOURCE_BYTES + 1)
    if len(data) > MAX_SOURCE_BYTES:
        raise ValueError("Source file exceeds the 8 MB viewer limit")
    text = data.decode("utf-8", errors="replace")
    # Never interpret source-file control sequences as terminal instructions.
    text = "".join(char if char in "\n\t" or char.isprintable() else " " for char in text.replace("\r\n", "\n"))
    matches: list[SourceMatch] = []
    seen: set[int] = set()
    file_cache: dict[str, bool] = {}

    def same_file(link: SourceTarget) -> bool:
        if link.path not in file_cache:
            candidate = Path(link.path)
            file_cache[link.path] = (cwd / candidate).resolve() == path if not candidate.is_absolute() else candidate.resolve() == path
        return file_cache[link.path]

    def visit(value: Any, label: str) -> None:
        if id(value) in seen:
            return
        seen.add(id(value))
        if isinstance(value, MatchValue):
            for index, row in enumerate(value.iter_rows()):
                row_summary(row._message(), f"{label}[{index}]")
        elif isinstance(value, NativeMatchCollection):
            for index, match in enumerate(value.matches):
                visit(match, f"{label}[file {index}]")
        elif isinstance(value, NativeBindingCollection):
            for index, match in enumerate(value.matches):
                visit(match, f"{label}[file {index}]")
        elif isinstance(value, MatchRow | DetachedMatchRow):
            row_summary(value._message(), label)
        elif isinstance(value, BindingSelection):
            link = source_target(value, value.name)
            if link and same_file(link):
                matches.append(SourceMatch(label, link, (link,)))
        elif isinstance(value, MessageView):
            message = value._message()
            if isinstance(message, pb.MatchResult):
                row_summary(message, label)
            elif isinstance(message, pb.MatchBinding):
                link = source_target(message, label)
                if link and same_file(link):
                    matches.append(SourceMatch(label, link, (link,)))
        elif isinstance(value, MatchSet):
            for index, row in enumerate(value.rows):
                visit(row, f"{label}[{index}]")
        elif isinstance(value, Mapping):
            for name, child in value.items():
                visit(child, f"{label}.{name}")
        elif isinstance(value, list | tuple):
            for index, child in enumerate(value):
                visit(child, f"{label}[{index}]")

    def row_summary(row: pb.MatchResult, label: str) -> None:
        links = tuple(
            link for name, binding in sorted(row.bindings.items())
            if (link := source_target(binding, binding_label(name, binding))) and same_file(link)
        )
        if links:
            primary = source_target(row, label)
            primary = primary if primary and same_file(primary) else links[0]
            matches.append(SourceMatch(label, primary, links))

    unavailable = 0
    for index, value in enumerate(values):
        try:
            visit(value, f"Results {index + 1}")
        except Exception:  # noqa: BLE001 - one expired preview must not block source viewing
            unavailable += 1
    notice = f"{unavailable} result preview(s) unavailable; print fresh results to include them" if unavailable else ""
    return SourceSnapshot(path, text, tuple(matches), notice)
