"""Compact numbered C++ with red line markers and precise inline underlines."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.lexers import Lexer, PygmentsLexer
from pygments.lexers import CppLexer

from clang_toolkit.cli.workspace_source_data import SourceTarget


def byte_column(text: str, column: int) -> int:
    """Clang columns count UTF-8 bytes; display columns count expanded characters."""
    return len(text.encode("utf-8")[:max(0, column - 1)].decode("utf-8", errors="ignore").expandtabs(4))


class SourcePresentation(Lexer):
    def __init__(self, text: str, target: SourceTarget, matches: Iterable[SourceTarget] = ()) -> None:
        original = Document(text)
        expanded = Document("\n".join(line.expandtabs(4) for line in original.lines))
        self.syntax = PygmentsLexer(CppLexer).lex_document(expanded)
        self.document = expanded
        self.digits = len(str(original.line_count))
        self.code_rows = list(range(original.line_count))
        self.marked: set[int] = set()
        self.selected: set[int] = set()
        self.spans: dict[int, list[tuple[int, int]]] = {}
        seen: set[tuple[int, int, int, int | None]] = set()
        for match in (target, *matches):
            coordinates = (match.line, match.column, match.end_line, match.end_column)
            if coordinates in seen:
                continue
            seen.add(coordinates)
            for row in range(max(0, match.line - 1), min(original.line_count, match.end_line)):
                text_line = original.lines[row]
                line = expanded.lines[row]
                start = byte_column(text_line, match.column) if row + 1 == match.line else 0
                end = byte_column(text_line, match.end_column) if row + 1 == match.end_line and match.end_column is not None else len(line)
                start = max(start, len(line) - len(line.lstrip()))
                end = min(end, len(line.rstrip()))
                if end > start or (not line.strip() and row + 1 < match.end_line):
                    self.marked.add(row)
                    if match is target:
                        self.selected.add(row)
                if end > start:
                    self.spans.setdefault(row, []).append((start, end))
        # Union overlapping/nested AST ranges, retaining gaps between expressions.
        for row, spans in self.spans.items():
            merged: list[tuple[int, int]] = []
            for start, end in sorted(spans):
                if merged and start <= merged[-1][1]:
                    merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
                else:
                    merged.append((start, end))
            self.spans[row] = merged

    def lex_document(self, document: Document) -> Callable[[int], StyleAndTextTuples]:
        def line(row: int) -> StyleAndTextTuples:
            if not 0 <= row < self.document.line_count:
                return []
            fragments = self.syntax(row)
            if row not in self.spans:
                return fragments
            marked: StyleAndTextTuples = []
            offset = 0
            span_index = 0
            spans = self.spans[row]
            for fragment in fragments:
                style, text = fragment[0], fragment[1]
                position = 0
                while position < len(text):
                    while span_index < len(spans) and spans[span_index][1] <= offset + position:
                        span_index += 1
                    if span_index == len(spans):
                        marked.append((style, text[position:]))
                        break
                    start, end = spans[span_index]
                    inside = start <= offset + position
                    stop = min(len(text), (end if inside else start) - offset)
                    marked.append((style + " underline" if inside else style, text[position:stop]))
                    position = stop
                offset += len(text)
            return marked
        return line

    def gutter(self, row: int, wrap: int) -> StyleAndTextTuples:
        if not 0 <= row < self.document.line_count:
            return []
        marker = "▶" if row in self.selected else "▷" if row in self.marked else " "
        return [("class:source-marker", marker), ("class:line-number", f"{row + 1:>{self.digits}}│ ")]
