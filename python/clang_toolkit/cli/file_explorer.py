"""Bounded, lazily expanded client-side filesystem browser."""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from itertools import islice
from pathlib import Path

from prompt_toolkit.application import get_app
from prompt_toolkit.data_structures import Point
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.layout import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType

MAX_DIRECTORY_ENTRIES = 500
MAX_VISIBLE_ENTRIES = 1_000
_HIDDEN_DIRECTORIES = {".git", ".venv", "__pycache__", "node_modules", "build"}


@dataclass(frozen=True)
class ExplorerEntry:
    path: Path
    directory: bool
    depth: int = 0


class FileExplorer:
    def __init__(
        self,
        root: Path,
        activate: Callable[[], None],
    ) -> None:
        self.root = root.resolve()
        self.children: dict[Path, tuple[ExplorerEntry, ...]] = {}
        self.expanded: set[Path] = {self.root}
        self.entries: list[ExplorerEntry] = []
        self.selected = 0
        self.notice = "Enter folder to expand; file to prepare parse"
        self.show_hidden = False
        self.activate = activate
        bindings = KeyBindings()

        @bindings.add("up")
        def previous(event: KeyPressEvent) -> None:
            self.selected = max(0, self.selected - 1)

        @bindings.add("down")
        def following(event: KeyPressEvent) -> None:
            self.selected = min(max(0, len(self.entries) - 1), self.selected + 1)

        @bindings.add("enter")
        def open_entry(event: KeyPressEvent) -> None:
            activate()

        @bindings.add("right")
        def expand(event: KeyPressEvent) -> None:
            item = self.current
            if item is None or not item.directory:
                return
            if item.path not in self.expanded:
                activate()
            elif self.selected + 1 < len(self.entries) and self.entries[self.selected + 1].depth > item.depth:
                self.move(1)

        @bindings.add("left")
        def collapse(event: KeyPressEvent) -> None:
            item = self.current
            if item is None:
                return
            if item.directory and item.path in self.expanded:
                activate()
            else:
                self.selected = next(
                    (index for index in range(self.selected - 1, -1, -1) if self.entries[index].depth < item.depth),
                    self.selected,
                )

        @bindings.add("pageup")
        @bindings.add("pagedown")
        def page(event: KeyPressEvent) -> None:
            height = (
                self.window.render_info.window_height if self.window.render_info else 10
            )
            self.move(-height if event.key_sequence[0].key == "pageup" else height)

        self.control = FormattedTextControl(
            self.fragments,
            focusable=True,
            key_bindings=bindings,
            get_cursor_position=lambda: Point(x=0, y=self.selected),
        )
        self.window = Window(
            self.control,
            right_margins=[ScrollbarMargin(display_arrows=True)],
            wrap_lines=False,
        )
        self.control.mouse_handler = self.mouse_handler  # type: ignore[method-assign, assignment]

    def move(self, amount: int) -> None:
        self.selected = max(
            0, min(max(0, len(self.entries) - 1), self.selected + amount)
        )

    def mouse_handler(self, event: MouseEvent) -> None:
        get_app().layout.focus(self.window)
        if event.event_type in {MouseEventType.SCROLL_UP, MouseEventType.SCROLL_DOWN}:
            self.move(-3 if event.event_type == MouseEventType.SCROLL_UP else 3)
        elif 0 <= event.position.y < len(self.entries):
            was_selected = self.selected == event.position.y
            if event.event_type == MouseEventType.MOUSE_UP:
                self.selected = event.position.y
                item = self.current
                on_arrow = item is not None and item.directory and 2 * item.depth <= event.position.x < 2 * item.depth + 2
                if was_selected or on_arrow:
                    self.activate()
            elif event.event_type == MouseEventType.MOUSE_DOWN:
                # Selection is committed on release; a second click activates.
                return

    @property
    def current(self) -> ExplorerEntry | None:
        return self.entries[self.selected] if self.entries else None

    def scan(self, path: Path) -> tuple[tuple[ExplorerEntry, ...], bool]:
        """Run in a worker; never enumerate directories during rendering."""
        found: list[ExplorerEntry] = []
        scanned = 0
        with os.scandir(path) as stream:
            for entry in islice(stream, MAX_DIRECTORY_ENTRIES + 1):
                scanned += 1
                if not self.show_hidden and (
                    entry.name.startswith(".") or entry.name in _HIDDEN_DIRECTORIES
                ):
                    continue
                # Symlink directories are listed as leaves to avoid traversal loops.
                found.append(
                    ExplorerEntry(
                        path=Path(entry.path),
                        directory=entry.is_dir(follow_symlinks=False),
                    )
                )
        truncated = scanned > MAX_DIRECTORY_ENTRIES
        found.sort(key=lambda item: (not item.directory, item.path.name.casefold()))
        return tuple(found[:MAX_DIRECTORY_ENTRIES]), truncated

    def rebuild(self) -> None:
        selected_path = self.current.path if self.current else None
        rows: list[ExplorerEntry] = []

        def visit(parent: Path, depth: int) -> None:
            for item in self.children.get(parent, ()):
                if len(rows) >= MAX_VISIBLE_ENTRIES:
                    return
                rows.append(ExplorerEntry(item.path, item.directory, depth))
                if item.path in self.expanded:
                    visit(item.path, depth + 1)

        visit(self.root, 0)
        self.entries = rows
        self.selected = next(
            (i for i, item in enumerate(rows) if item.path == selected_path),
            min(self.selected, max(0, len(rows) - 1)),
        )
        if len(rows) >= MAX_VISIBLE_ENTRIES:
            self.notice = f"Showing at most {MAX_VISIBLE_ENTRIES} rows"

    def fragments(self) -> StyleAndTextTuples:
        if not self.entries:
            return [("class:muted", "No visible files")]
        result: StyleAndTextTuples = []
        for index, item in enumerate(self.entries):
            icon = "▾" if item.path in self.expanded else "▸"
            if not item.directory:
                icon = " "
            # Filesystem names must not introduce extra rows/control characters.
            name = "".join(c if c.isprintable() else "?" for c in item.path.name)
            label = "  " * item.depth + icon + " " + name
            style = (
                "class:file-selected"
                if index == self.selected
                else "class:file-folder"
                if item.directory
                else ""
            )
            result.append(
                (style, label + ("\n" if index + 1 < len(self.entries) else ""))
            )
        return result
