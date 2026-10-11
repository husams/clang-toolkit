"""Compact numbered C++ with red line markers and precise inline underlines."""

from __future__ import annotations

from collections.abc import Callable

from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.lexers import Lexer, PygmentsLexer
from pygments.lexers import CppLexer

from clang_toolkit.cli.workspace_source_data import SourceTarget


def byte_column(text: str, column: int) -> int:
    """Clang columns count UTF-8 bytes; display columns count expanded characters."""
    return len(text.encode("utf-8")[:max(0, column - 1)].decode("utf-8", errors="ignore").expandtabs(4))


class SourcePresentation(Lexer):
    def __init__(self, text: str, target: SourceTarget) -> None:
        original = Document(text)
        expanded = Document("\n".join(line.expandtabs(4) for line in original.lines))
        self.syntax = PygmentsLexer(CppLexer).lex_document(expanded)
        self.document = expanded
        self.digits = len(str(original.line_count))
        self.code_rows = list(range(original.line_count))
        self.marked: set[int] = set()
        self.spans: dict[int, tuple[int, int]] = {}
        for row, text_line in enumerate(original.lines):
            line = text_line.expandtabs(4)
            if target.line <= row + 1 <= target.end_line:
                start = byte_column(text_line, target.column) if row + 1 == target.line else 0
                end = byte_column(text_line, target.end_column) if row + 1 == target.end_line and target.end_column is not None else len(line)
                start = max(start, len(line) - len(line.lstrip()))
                end = min(end, len(line.rstrip()))
                if end > start or (not line.strip() and row + 1 < target.end_line):
                    self.marked.add(row)
                if end > start:
                    self.spans[row] = (start, end)

    def lex_document(self, document: Document) -> Callable[[int], StyleAndTextTuples]:
        def line(row: int) -> StyleAndTextTuples:
            if not 0 <= row < self.document.line_count:
                return []
            fragments = self.syntax(row)
            if row not in self.spans:
                return fragments
            start, end = self.spans[row]
            marked: StyleAndTextTuples = []
            offset = 0
            for fragment in fragments:
                style, text = fragment[0], fragment[1]
                first, last = max(0, start - offset), min(len(text), end - offset)
                if first < last:
                    if first:
                        marked.append((style, text[:first]))
                    marked.append((style + " underline", text[first:last]))
                    if last < len(text):
                        marked.append((style, text[last:]))
                else:
                    marked.append(fragment)
                offset += len(text)
            return marked
        return line

    def gutter(self, row: int, wrap: int) -> StyleAndTextTuples:
        if not 0 <= row < self.document.line_count:
            return []
        marker = "▶" if row in self.marked else " "
        return [("class:source-marker", marker), ("class:line-number", f"{row + 1:>{self.digits}}│ ")]
