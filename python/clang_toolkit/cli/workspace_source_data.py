"""Source links and detached navigation summaries from actual match metadata."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from clang_toolkit._generated.match.v1 import match_result_pb2 as pb
from clang_toolkit.cli.runtime.semantic import MessageView
from clang_toolkit.match_values import BindingSelection, MatchRow
from clang_toolkit.batches import DetachedMatchRow

MAX_SOURCE_BYTES = 8_000_000


@dataclass(frozen=True)
class SourceTarget:
    path: str
    line: int
    column: int
    end_line: int
    label: str = ""
    end_column: int | None = None

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
    display_path: str = ""


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
        end = value.range.expansion_end_exclusive
        exclusive = end.valid and end.file == begin.file and end.line >= begin.line and end.column > 0
        if not exclusive:
            end = value.range.expansion_end
        if not begin.valid or not begin.file or not begin.line:
            return None
        end_line = end.line if end.valid and end.file == begin.file and end.line >= begin.line else begin.line
        return SourceTarget(begin.file, begin.line, max(1, begin.column), end_line, label, end.column if exclusive else None)
    if isinstance(value, pb.MatchSourcePoint):
        if value.valid and value.file and value.line:
            return SourceTarget(value.file, value.line, max(1, value.column), value.line, label)
    if isinstance(value, pb.MatchSourceRange):
        begin, end = value.expansion_begin, value.expansion_end_exclusive
        exclusive = end.valid and end.file == begin.file and end.line >= begin.line and end.column > 0
        if not exclusive:
            end = value.expansion_end
        if begin.valid and begin.file and begin.line:
            end_line = end.line if end.valid and end.file == begin.file and end.line >= begin.line else begin.line
            return SourceTarget(begin.file, begin.line, max(1, begin.column), end_line, label, end.column if exclusive else None)
    return None


def binding_label(name: str, value: pb.MatchBinding) -> str:
    # Semantic helpers traverse the immediate declaration projection only.
    from clang_toolkit.match_values import _binding_decl_name, _binding_decl_type

    declaration = _binding_decl_name(value)
    type_name = _binding_decl_type(value)
    return name + (f" — {declaration}" if declaration else "") + (f" · {type_name}" if type_name else "")


def source_snapshot(target: SourceTarget, cwd: Path) -> SourceSnapshot:
    """Read local code on a worker and mark only the selected link's range."""
    path = Path(target.path)
    path = (cwd / path).resolve() if not path.is_absolute() else path.resolve()
    with path.open("rb") as stream:
        data = stream.read(MAX_SOURCE_BYTES + 1)
    if len(data) > MAX_SOURCE_BYTES:
        raise ValueError("Source file exceeds the 8 MB viewer limit")
    text = data.decode("utf-8", errors="replace")
    # Never interpret source-file control sequences as terminal instructions.
    text = "".join(char if char in "\n\t" or char.isprintable() else " " for char in text.replace("\r\n", "\n"))
    matches = (SourceMatch(target.label, target, ()),)
    try:
        display_path = str(path.relative_to(cwd.resolve()))
    except ValueError:
        display_path = str(path)
    return SourceSnapshot(path, text, matches, display_path=display_path)
