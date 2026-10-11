"""Numbered source blocks, source-local diagnostics and responsive dark code rows."""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Callable
from dataclasses import dataclass
import re

from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.layout.controls import BufferControl, UIContent
from prompt_toolkit.layout.utils import explode_text_fragments
from prompt_toolkit.layout.processors import (
    Processor,
    Transformation,
    TransformationInput,
)
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.utils import get_cwidth

from clang_toolkit.cli.highlight import ReplLexer
from clang_toolkit.cli.language import lex

NUMBERED = re.compile(r"^(\s*\d+ │ )(.*)$")
MARKER = re.compile(r"^\s+│ [ \^~]+$")


@dataclass(frozen=True)
class ErrorSpan:
    line: int
    column: int
    length: int = 1


def error_span(source: str, message: str) -> ErrorSpan | None:
    """Use reported script coordinates, or a unique grammar-token reference.

    Native diagnostics can refer to a C++ file or a matcher subexpression; do
    not treat their coordinates as positions in the submitted script.
    """
    reported = re.search(r"\bline (\d+), column (\d+)", message.partition("\n")[0])
    if reported:
        line, column = map(int, reported.groups())
        lines = source.split("\n")
        if 1 <= line <= len(lines) and 1 <= column <= len(lines[line - 1]) + 1:
            return ErrorSpan(line, column)
        return None
    unknown = re.fullmatch(r"error: unknown variable: (\w+)", message.strip())
    if unknown:
        tokens = [token for token in lex(source) if token.type != "WS"]
        names = [
            token
            for previous, token in zip(tokens, tokens[1:])
            if previous.type == "DOLLAR" and str(token) == unknown.group(1)
        ]
        if len(names) == 1:
            token = names[0]
            return ErrorSpan(
                int(token.line or 1), int(token.column or 2) - 1, len(str(token)) + 1
            )
    return None


def command_block(source: str, error: ErrorSpan | None = None) -> str:
    """Plain numbered source; syntax and dark-row rendering remain responsive."""
    lines = source.split("\n")
    digits = max(3, len(str(len(lines))))
    numbered: list[str] = []
    for index, line in enumerate(lines, 1):
        numbered.append(f"{index:>{digits}} │ {line.expandtabs(4)}")
        if error is not None and error.line == index:
            offset = get_cwidth(line[: error.column - 1].expandtabs(4))
            length = max(
                1, get_cwidth(line[error.column - 1 : error.column - 1 + error.length])
            )
            numbered.append(
                " " * digits + " │ " + " " * offset + "^" + "~" * (length - 1)
            )
    return "\n".join(numbered) + "\n"


@dataclass
class StyledBlock:
    start: int
    text: str
    lines: list[StyleAndTextTuples]


class TranscriptLexer(Lexer):
    def __init__(self) -> None:
        self.blocks: list[StyledBlock] = []

    def trim(self, cut: int, shift: int) -> None:
        self.blocks = [block for block in self.blocks if block.start >= cut]
        for block in self.blocks:
            block.start -= shift

    def replace(self, start: int, end: int, length: int) -> None:
        self.blocks = [
            block
            for block in self.blocks
            if block.start + len(block.text) <= start or block.start >= end
        ]
        for block in self.blocks:
            if block.start >= end:
                block.start += length - (end - start)

    def lex_document(self, document: Document) -> Callable[[int], StyleAndTextTuples]:
        source = document.lines
        lines: list[StyleAndTextTuples] = [[] for _ in source]
        index = 0
        while index < len(source):
            match = NUMBERED.match(source[index])
            if match:
                end = index
                code: list[tuple[int, re.Match[str]]] = []
                while end < len(source):
                    candidate = NUMBERED.match(source[end])
                    if candidate:
                        if code and int(candidate.group(1).split()[0]) == 1:
                            break
                        code.append((end, candidate))
                    elif MARKER.match(source[end]):
                        lines[end] = [("class:code class:diagnostic", source[end])]
                    else:
                        break
                    end += 1
                highlighted = ReplLexer(semantic_matchers=True).lex_document(
                    Document("\n".join(item.group(2) for _, item in code))
                )
                for offset, (number, item) in enumerate(code):
                    lines[number] = [
                        ("class:code class:line-number", item.group(1)),
                        *[
                            ("class:code " + fragment[0], fragment[1])
                            for fragment in highlighted(offset)
                        ],
                    ]
                    # Underline the failing token as well as its caret marker.
                    if number + 1 < len(source) and MARKER.match(source[number + 1]):
                        marker = source[number + 1]
                        start, stop = marker.index("^"), len(marker)
                        fragments = explode_text_fragments(lines[number])
                        cell = 0
                        marked: StyleAndTextTuples = []
                        for fragment in fragments:
                            style, text = fragment[0], fragment[1]
                            width = get_cwidth(text)
                            if cell < stop and cell + width > start:
                                style += " class:diagnostic underline"
                            marked.append((style, text))
                            cell += width
                        lines[number] = marked
                index = end
            else:
                style = (
                    "class:diagnostic"
                    if source[index].startswith(
                        ("error:", "syntax error", "unknown command:")
                    )
                    else ""
                )
                lines[index] = [(style, source[index])]
                index += 1
        for block in self.blocks:
            if document.text.startswith(block.text, block.start):
                first, _ = document.translate_index_to_position(block.start)
                for offset, styled_line in enumerate(block.lines):
                    if first + offset < len(lines):
                        lines[first + offset] = styled_line
        return lambda line: lines[line] if 0 <= line < len(lines) else []


class CodeRows(Processor):
    """Fill every code row and keep a blank number gutter on wrapped rows.

    Transform display cells only, leaving retained source/search text intact;
    mappings preserve mouse selection and cursor movement across inserted space.
    """

    def __init__(self, wraps: Callable[[], bool]) -> None:
        self.wraps = wraps

    def apply_transformation(self, ti: TransformationInput) -> Transformation:
        if not ti.fragments or "class:code" not in ti.fragments[0][0]:
            return Transformation(ti.fragments)
        width = max(1, ti.width)
        prefix = NUMBERED.match(ti.document.lines[ti.lineno])
        gutter = " " * (len(prefix.group(1)) - 2) + "│ " if prefix else ""
        if get_cwidth(gutter) >= width:
            gutter = ""
        fragments: StyleAndTextTuples = []
        positions: list[int] = []
        display = 0
        column = 0

        def insert(text: str) -> None:
            nonlocal display, column
            if text:
                fragments.append(("class:code class:line-number", text))
                display += len(text)
                column += get_cwidth(text)

        for fragment in explode_text_fragments(ti.fragments):
            style, text = fragment[0], fragment[1]
            cells = get_cwidth(text)
            if self.wraps() and column and column + cells > width:
                insert(" " * (width - column))
                column = 0
                insert(gutter)
            positions.append(display)
            fragments.append((style, text))
            display += len(text)
            column += cells
        positions.append(display)
        if column == width and self.wraps():
            # Retain a selectable end-of-line cursor cell only when needed.
            column = 0
            insert(gutter)
            positions[-1] = display
        if column < width:
            insert(" " * (width - column))
        return Transformation(
            fragments,
            source_to_display=lambda i: positions[min(i, len(positions) - 1)],
            display_to_source=lambda i: max(0, bisect_right(positions, i) - 1),
        )


class TranscriptControl(BufferControl):
    def create_content(
        self, width: int, height: int, preview_search: bool = False
    ) -> UIContent:
        content = super().create_content(width, height, preview_search)
        original = content.get_line

        def get_line(number: int) -> StyleAndTextTuples:
            fragments = original(number)
            # BufferControl appends an extra plain cursor space to every line.
            # CodeRows already reserves that cell and fills the whole row;
            # leaving the extra space creates a spurious wrapped blank row.
            if fragments and "class:code" in fragments[0][0]:
                return fragments[:-1]
            return fragments

        content.get_line = get_line
        return content
