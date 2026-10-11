"""Horizontal source scrolling without moving the selected AST range."""

from __future__ import annotations

from collections.abc import Callable

from prompt_toolkit.application import get_app
from prompt_toolkit.data_structures import Point
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.layout import ConditionalContainer, Dimension, HSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl, UIContent
from prompt_toolkit.lexers import DynamicLexer
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.utils import get_cwidth
from prompt_toolkit.widgets import TextArea


class PanningSourceControl(BufferControl):
    def __init__(self, code: TextArea, offset: Callable[[int], int | None]) -> None:
        super().__init__(buffer=code.buffer, lexer=DynamicLexer(lambda: code.lexer), focus_on_click=True)
        self.offset = offset

    def create_content(self, width: int, height: int, preview_search: bool = False) -> UIContent:
        content = super().create_content(width, height, preview_search)
        offset = self.offset(width)
        if offset is None:
            return content
        # Window keeps its rendering cursor visible. A virtual cursor permits
        # panning even when the actual cursor is on a shorter source line.
        row = content.cursor_position.y
        text = self.buffer.document.lines[row]
        cells, column = 0, 0
        for column, character in enumerate(text):
            if cells >= offset:
                break
            cells += get_cwidth(character)
        else:
            column = len(text) + max(0, offset - cells)
        get_line = content.get_line
        padding = " " * max(0, offset - get_cwidth(text))
        content.get_line = lambda index: get_line(index) + ([("", padding)] if index == row else [])
        content.cursor_position = Point(column, row)
        content.show_cursor = False
        return content


class SourceScrollbar:
    def __init__(self, code: TextArea, invalidate: Callable[[], None]) -> None:
        self.code = code
        self.invalidate = invalidate
        self.manual_offset: int | None = None
        self.content_width = 0
        self.gutter_width = 4
        self.cursor_row = 0
        self.render_width: int | None = None
        code.control = PanningSourceControl(code, self.panning_offset)
        code.window.content = code.control
        code.window.get_horizontal_scroll = self.preferred_scroll
        code.buffer.on_cursor_position_changed += self.follow_cursor
        self.control = FormattedTextControl(self.fragments)
        self.control.mouse_handler = self.mouse  # type: ignore[method-assign, assignment]
        self.window = Window(self.control, height=1)
        self.container = HSplit([
            code,
            ConditionalContainer(self.window, Condition(lambda: self.maximum_offset > 0)),
        ], width=Dimension(min=10, weight=3))

    def reset(self, document: Document) -> None:
        self.content_width = max((get_cwidth(line) for line in document.lines), default=0)
        self.gutter_width = len(str(document.line_count)) + 3
        self.manual_offset = None
        self.code.window.horizontal_scroll = 0
        self.cursor_row = document.cursor_position_row

    @property
    def viewport_width(self) -> int:
        info = self.code.window.render_info
        width = self.render_width if self.render_width is not None else info.window_width if info else 44
        return max(1, width - self.gutter_width)

    def panning_offset(self, width: int) -> int | None:
        if self.render_width != width:
            self.render_width = width
            self.invalidate()  # Re-evaluate scrollbar visibility after a resize.
        if self.manual_offset is not None:
            self.manual_offset = max(0, min(self.maximum_offset, self.manual_offset))
        return self.manual_offset

    @property
    def maximum_offset(self) -> int:
        return max(0, self.content_width - self.viewport_width)

    def preferred_scroll(self, window: Window) -> int:
        offset = window.horizontal_scroll if self.manual_offset is None else self.manual_offset
        offset = max(0, min(self.maximum_offset, offset))
        if self.manual_offset is not None:
            self.manual_offset = offset
        return offset

    def follow_cursor(self, _: object) -> None:
        row = self.code.buffer.document.cursor_position_row
        if row == self.cursor_row:
            self.manual_offset = None
        self.cursor_row = row

    def scroll(self, amount: int) -> None:
        self.manual_offset = max(0, min(self.maximum_offset, self.preferred_scroll(self.code.window) + amount))
        self.invalidate()

    def fragments(self) -> StyleAndTextTuples:
        width = self.viewport_width
        track = max(1, width - 2)
        thumb = min(track, max(1, track * width // max(width, self.content_width)))
        offset = self.preferred_scroll(self.code.window)
        start = (track - thumb) * offset // max(1, self.maximum_offset)
        return [
            ("", " " * self.gutter_width),
            ("class:scrollbar.arrow", "‹"),
            ("class:scrollbar.background", "─" * start),
            ("class:scrollbar.button", "━" * thumb),
            ("class:scrollbar.background", "─" * (track - thumb - start)),
            ("class:scrollbar.arrow", "›"),
        ]

    def mouse(self, event: MouseEvent) -> None:
        if event.event_type != MouseEventType.MOUSE_UP:
            return
        position = event.position.x - self.gutter_width
        if position < 0:
            return
        get_app().layout.focus(self.code.window)
        if position == 0 or position >= self.viewport_width - 1:
            self.scroll(-8 if position == 0 else 8)
        else:
            self.manual_offset = round(self.maximum_offset * (position - 1) / max(1, self.viewport_width - 3))
            self.invalidate()
