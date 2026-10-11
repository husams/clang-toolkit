"""Source-only syntax colors with separate gutter and range annotation rows."""

from __future__ import annotations

from collections.abc import Callable

from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.lexers import Lexer, PygmentsLexer
from prompt_toolkit.utils import get_cwidth
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
        self.rows: list[tuple[int, bool, str]] = []
        self.code_rows: list[int] = []
        display: list[str] = []
        marked: list[int] = []
        for row, text_line in enumerate(original.lines):
            line = text_line.expandtabs(4)
            self.code_rows.append(len(display))
            self.rows.append((row, False, " "))
            display.append(line)
            if target.line <= row + 1 <= target.end_line:
                start = byte_column(text_line, target.column) if row + 1 == target.line else 0
                end = byte_column(text_line, target.end_column) if row + 1 == target.end_line and target.end_column is not None else len(line)
                start = max(start, len(line) - len(line.lstrip()))
                end = min(end, len(line.rstrip()))
                if end > start or (not line.strip() and row + 1 < target.end_line):
                    marked.append(self.code_rows[-1])
                if end > start:
                    self.rows.append((row, True, " "))
                    display.append(" " * get_cwidth(line[:start]) + "─" * get_cwidth(line[start:end]))
        for index, display_row in enumerate(marked):
            marker = "▶" if len(marked) == 1 else "┌" if index == 0 else "└" if index == len(marked) - 1 else "│"
            row, underline, _ = self.rows[display_row]
            self.rows[display_row] = (row, underline, marker)
        self.document = Document("\n".join(display))

    def lex_document(self, document: Document) -> Callable[[int], StyleAndTextTuples]:
        def line(row: int) -> StyleAndTextTuples:
            if not 0 <= row < len(self.rows):
                return []
            original, underline, _ = self.rows[row]
            return [("class:source-marker", document.lines[row])] if underline else self.syntax(original)
        return line

    def gutter(self, row: int, wrap: int) -> StyleAndTextTuples:
        if not 0 <= row < len(self.rows):
            return []
        original, underline, marker = self.rows[row]
        if underline:
            return [("class:line-number", "        │ ")]
        return [("class:source-marker", f"{marker} "), ("class:line-number", f"{original + 1:>5} │ ")]
