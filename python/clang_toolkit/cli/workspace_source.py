"""A separate, closable C++ source window with a paged match outline."""

from __future__ import annotations

from collections.abc import Callable

from prompt_toolkit.document import Document
from prompt_toolkit.filters import has_focus
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent, merge_key_bindings
from prompt_toolkit.layout import HSplit, VSplit, Window, Dimension
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.widgets import Frame, TextArea

from clang_toolkit.cli.workspace_source_data import SourceSnapshot, SourceTarget
from clang_toolkit.cli.workspace_state import PanelEntry, compact
from clang_toolkit.cli.workspace_tree import WorkspaceTree
from clang_toolkit.cli.workspace_source_render import SourcePresentation, byte_column

PAGE_SIZE = 50


class SourceWindow:
    def __init__(self, close: Callable[[], None], invalidate: Callable[[], None],
                 interrupt: Callable[[], None] | None = None, quit: Callable[[], None] | None = None) -> None:
        self.visible = False
        self.close = close
        self.invalidate = invalidate
        self.snapshot: SourceSnapshot | None = None
        self.target: SourceTarget | None = None
        self.notice = "Loading source…"
        self.page = 0
        self.code = TextArea(
            read_only=True, scrollbar=True,
            wrap_lines=False, focus_on_click=True, name="workspace-source",
            width=Dimension(min=10, weight=3),
        )
        self.code.window.get_line_prefix = lambda line, wrap: [("class:line-number", f"{line + 1:>5} │ ")]
        self.tree = WorkspaceTree(self.refresh, lambda _: None, self.jump)
        self.tree.toggle = self.activate  # type: ignore[method-assign]
        toolbar = FormattedTextControl(self.toolbar)
        keys = KeyBindings()

        @keys.add("escape", eager=True)
        def dismiss(event: KeyPressEvent) -> None:
            self.close()

        @keys.add("c-c")
        @keys.add("<sigint>")
        def cancel(event: KeyPressEvent) -> None:
            (interrupt or self.close)()

        @keys.add("f10")
        def exit_console(event: KeyPressEvent) -> None:
            (quit or self.close)()

        @keys.add("tab")
        @keys.add("f6")
        @keys.add("s-tab")
        def focus(event: KeyPressEvent) -> None:
            event.app.layout.focus(self.tree.window if event.app.layout.has_focus(self.code.window) else self.code.window)

        @keys.add("n")
        @keys.add("p")
        def match(event: KeyPressEvent) -> None:
            self.next_match(1 if event.key_sequence[0].key == "n" else -1)

        @keys.add("enter", filter=has_focus(self.tree.window))
        def activate(event: KeyPressEvent) -> None:
            self.activate()

        self.tree.control.key_bindings = merge_key_bindings([self.tree.control.key_bindings or KeyBindings(), keys])

        self.container = Frame(
            HSplit([
                Window(toolbar, height=1, style="class:toolbar"),
                VSplit([
                    self.code,
                    Frame(self.tree.container, title="Matches in file", width=Dimension(min=20, weight=1)),
                ]),
                Window(FormattedTextControl(lambda: compact(self.notice, 4096)), height=1, style="class:toolbar"),
            ], key_bindings=keys),
            title=lambda: compact(str(self.snapshot.path) if self.snapshot else "Source code", 4096),
            style="class:code",
        )

    def toolbar(self) -> list[tuple]:
        def click(action: Callable[[], None]):
            def handler(event):
                from prompt_toolkit.mouse_events import MouseEventType
                if event.event_type == MouseEventType.MOUSE_UP:
                    action()
            return handler

        return [
            ("class:action", " ‹ Previous [P] ", click(lambda: self.next_match(-1))),
            ("class:action", " Next [N] › ", click(lambda: self.next_match(1))),
            ("class:muted", " Tab/F6: code ↔ outline "),
            ("class:panel-close", " Close [Esc] ", click(self.close)),
        ]

    def show(self, snapshot: SourceSnapshot, target: SourceTarget) -> None:
        self.snapshot = snapshot
        self.tree.expanded.clear()
        self.tree.pages.clear()
        self.page = 0
        self.code.buffer.set_document(Document(snapshot.text), bypass_readonly=True)
        self.refresh()
        self.jump(target)
        index = next((i for i, match in enumerate(snapshot.matches) if self.same_location(match.target, target) or any(self.same_location(link, target) for link in match.bindings)), 0)
        self.page = index // PAGE_SIZE
        self.tree.pages["source"] = self.page
        self.refresh()
        self.tree.selected = next((i for i, row in enumerate(self.tree.entries) if row.identity == f"source:{index}"), 0)

    def jump(self, target: SourceTarget) -> None:
        self.target = target
        if self.snapshot is None:
            return
        presentation = SourcePresentation(self.snapshot.text, target)
        self.code.lexer = presentation
        self.code.window.get_line_prefix = presentation.gutter
        self.code.buffer.set_document(presentation.document, bypass_readonly=True)
        lines = Document(self.snapshot.text).lines
        original_row = min(max(0, target.line - 1), len(lines) - 1)
        row = presentation.code_rows[original_row]
        column = byte_column(lines[original_row], target.column)
        self.code.buffer.cursor_position = self.code.buffer.document.translate_row_col_to_index(row, column)
        self.code.window.vertical_scroll = max(0, row - 3)
        self.notice = f"{target.label or 'Match'} · {target.location} · lines {target.line}–{target.end_line}"
        if self.snapshot and self.snapshot.notice:
            self.notice += " · " + self.snapshot.notice
        self.invalidate()

    def refresh(self) -> None:
        if self.snapshot is None:
            return
        matches = self.snapshot.matches
        last_page = max(0, (len(matches) - 1) // PAGE_SIZE)
        self.page = min(last_page, max(0, self.tree.pages.get("source", self.page)))
        start, stop = self.page * PAGE_SIZE, min(len(matches), (self.page + 1) * PAGE_SIZE)
        rows = [PanelEntry(":source-count", f"Matches [{len(matches)}] · {start + 1 if matches else 0}–{stop}")]
        if self.page:
            rows.append(PanelEntry(":previous", "‹ Previous page", page=("source", self.page - 1)))
        for index in range(start, stop):
            match = matches[index]
            identity = f"source:{index}"
            rows.append(PanelEntry(identity, f"[{index}] {match.target.location}", expandable=True, source=match.target))
            if identity in self.tree.expanded:
                for binding, link in enumerate(match.bindings):
                    rows.append(PanelEntry(f"{identity}:{binding}", compact(f"{link.label} · {link.location}", 4096), depth=1, source=link))
        if self.page < last_page:
            rows.append(PanelEntry(":next", "Next page ›", page=("source", self.page + 1)))
        self.tree.update(rows)
        self.invalidate()

    def activate(self) -> None:
        current = self.tree.current
        if current is None:
            return
        if current.page is not None:
            reference, page = current.page
            self.tree.pages[reference] = page
            self.refresh()
        elif current.source is not None:
            if current.expandable:
                if current.identity in self.tree.expanded:
                    self.tree.expanded.remove(current.identity)
                else:
                    self.tree.expanded.add(current.identity)
                self.refresh()
            self.jump(current.source)

    def next_match(self, step: int) -> None:
        if self.snapshot is None or not self.snapshot.matches:
            return
        current = self.tree.current
        index = int(current.identity.split(":")[1]) if current and current.identity.startswith("source:") else next((i for i, match in enumerate(self.snapshot.matches) if self.same_location(match.target, self.target)), -1)
        index = (index + step) % len(self.snapshot.matches)
        self.page = index // PAGE_SIZE
        self.tree.pages["source"] = self.page
        self.refresh()
        self.tree.selected = next(i for i, row in enumerate(self.tree.entries) if row.identity == f"source:{index}")
        self.jump(self.snapshot.matches[index].target)

    @staticmethod
    def same_location(first: SourceTarget, second: SourceTarget | None) -> bool:
        return second is not None and (first.path, first.line, first.column, first.end_line, first.end_column) == (second.path, second.line, second.column, second.end_line, second.end_column)
