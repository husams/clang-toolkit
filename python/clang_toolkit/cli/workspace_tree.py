"""Keyboard and mouse selection for outline and resource snapshots."""

from __future__ import annotations

from collections.abc import Callable

from prompt_toolkit.application import get_app
from prompt_toolkit.data_structures import Point
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.layout import HSplit, Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.utils import get_cwidth

from clang_toolkit.cli.workspace_state import PanelEntry


class WorkspaceTree:
    def __init__(
        self, refresh: Callable[[], None], prepare: Callable[[str], None]
    ) -> None:
        self.refresh = refresh
        self.prepare = prepare
        self.entries: list[PanelEntry] = []
        self.selected = 0
        self.expanded: set[str] = set()
        self.pages: dict[str, int] = {}
        self.horizontal_offset = 0
        self.notice = "Loading…"
        bindings = KeyBindings()

        @bindings.add("up")
        @bindings.add("down")
        @bindings.add("pageup")
        @bindings.add("pagedown")
        @bindings.add("home")
        @bindings.add("end")
        def move(event: KeyPressEvent) -> None:
            key = event.key_sequence[0].key
            if key == "home":
                self.selected = 0
            elif key == "end":
                self.selected = max(0, len(self.entries) - 1)
            else:
                self.move({"up": -1, "down": 1, "pageup": -8, "pagedown": 8}[key])

        @bindings.add("enter")
        def expand(event: KeyPressEvent) -> None:
            current = self.current
            if current is None:
                return
            if current.page is not None:
                reference, page = current.page
                self.pages[reference] = page
                self.refresh()
                return
            if not current.expandable:
                return
            if current.identity in self.expanded:
                self.expanded.discard(current.identity)
            else:
                self.expanded.add(current.identity)
            self.refresh()

        @bindings.add("c-left")
        @bindings.add("c-right")
        @bindings.add("left")
        @bindings.add("right")
        def horizontal(event: KeyPressEvent) -> None:
            self.scroll_horizontal(-8 if event.key_sequence[0].key in {"left", "c-left"} else 8)

        @bindings.add("a")
        @bindings.add("c")
        @bindings.add("p")
        def action(event: KeyPressEvent) -> None:
            self.command(str(event.key_sequence[0].key))

        self.control = FormattedTextControl(
            self.fragments,
            focusable=True,
            key_bindings=bindings,
            get_cursor_position=lambda: Point(self.cursor_column, self.selected),
        )
        self.control.mouse_handler = self.mouse  # type: ignore[method-assign, assignment]
        self.window = Window(
            self.control,
            wrap_lines=False,
            get_horizontal_scroll=lambda _: self.horizontal_offset,
            right_margins=[ScrollbarMargin(display_arrows=True)],
        )
        self.scrollbar_control = FormattedTextControl(self.scrollbar)
        self.scrollbar_control.mouse_handler = self.scrollbar_mouse  # type: ignore[method-assign, assignment]
        self.scrollbar_window = Window(self.scrollbar_control, height=1)
        self.container = HSplit([self.window, self.scrollbar_window])

    @property
    def viewport_width(self) -> int:
        return max(
            1, self.window.render_info.window_width if self.window.render_info else 44
        )

    @property
    def cursor_column(self) -> int:
        text = self.entry_text(self.current) if self.current else ""
        cells = 0
        for index, character in enumerate(text):
            if cells >= self.horizontal_offset:
                return index
            cells += get_cwidth(character)
        return len(text) + max(0, self.horizontal_offset - cells)

    @property
    def content_width(self) -> int:
        return max(
            (get_cwidth(self.entry_text(item)) for item in self.entries), default=0
        )

    @property
    def maximum_offset(self) -> int:
        return max(0, self.content_width - self.viewport_width)

    def scroll_horizontal(self, amount: int) -> None:
        self.horizontal_offset = max(
            0, min(self.maximum_offset, self.horizontal_offset + amount)
        )
        get_app().invalidate()

    def scrollbar(self) -> StyleAndTextTuples:
        width = self.viewport_width
        track = max(1, width - 2)
        thumb = min(track, max(1, track * width // max(width, self.content_width)))
        self.horizontal_offset = min(self.horizontal_offset, self.maximum_offset)
        start = (track - thumb) * self.horizontal_offset // max(1, self.maximum_offset)
        return [
            ("class:scrollbar.arrow", "‹"),
            ("class:scrollbar.background", "─" * start),
            ("class:scrollbar.button", "━" * thumb),
            ("class:scrollbar.background", "─" * (track - thumb - start)),
            ("class:scrollbar.arrow", "›"),
        ]

    def scrollbar_mouse(self, event: MouseEvent) -> None:
        if event.event_type != MouseEventType.MOUSE_UP:
            return
        get_app().layout.focus(self.window)
        position = event.position.x
        if position == 0 or position >= self.viewport_width - 1:
            self.scroll_horizontal(-8 if position == 0 else 8)
        else:
            self.horizontal_offset = round(
                self.maximum_offset * (position - 1) / max(1, self.viewport_width - 3)
            )
            get_app().invalidate()

    @property
    def current(self) -> PanelEntry | None:
        return self.entries[self.selected] if self.entries else None

    def update(self, entries: list[PanelEntry]) -> None:
        identity = self.current.identity if self.current else None
        self.entries = entries
        self.selected = next(
            (i for i, item in enumerate(entries) if item.identity == identity),
            min(self.selected, max(0, len(entries) - 1)),
        )
        self.notice = "No bindings. Assign a result with let." if not entries else ""
        self.horizontal_offset = min(self.horizontal_offset, self.maximum_offset)

    def move(self, amount: int) -> None:
        self.selected = max(
            0, min(max(0, len(self.entries) - 1), self.selected + amount)
        )

    def command(self, key: str) -> None:
        if self.current is not None:
            source = dict(self.current.commands).get(key)
            if source:
                self.prepare(source)

    def mouse(self, event: MouseEvent) -> None:
        get_app().layout.focus(self.window)
        if event.event_type in {MouseEventType.SCROLL_UP, MouseEventType.SCROLL_DOWN}:
            self.move(-3 if event.event_type == MouseEventType.SCROLL_UP else 3)
        elif 0 <= event.position.y < len(self.entries):
            previous = self.selected
            self.selected = event.position.y
            if (
                event.event_type == MouseEventType.MOUSE_UP
                and previous == self.selected
            ):
                current = self.current
                if current is not None and current.page is not None:
                    reference, page = current.page
                    self.pages[reference] = page
                    self.refresh()
                elif current is not None and current.expandable:
                    if current.identity in self.expanded:
                        self.expanded.remove(current.identity)
                    else:
                        self.expanded.add(current.identity)
                    self.refresh()

    def fragments(self) -> StyleAndTextTuples:
        if not self.entries:
            return [("class:muted", self.notice)]
        texts = [self.entry_text(item) for item in self.entries]
        width = max(map(get_cwidth, texts), default=0)
        # The toolkit constrains scrolling to the cursor's selected line.
        # Pad to the full tree width so selecting a short parent does not
        # prevent panning longer descendants; offsets remain display cells.
        return [
            (
                "class:tree-selected" if i == self.selected else "class:tree",
                text + " " * (width - get_cwidth(text)) + "\n",
            )
            for i, text in enumerate(texts)
        ]

    def entry_text(self, item: PanelEntry) -> str:
        return (
            "  " * item.depth
            + (
                "▾ "
                if item.identity in self.expanded
                else "▸ "
                if item.expandable
                else "  "
            )
            + item.label
        )
