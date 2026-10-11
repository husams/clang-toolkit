"""Optional prompt_toolkit workspace, sharing the existing console buffer."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from time import monotonic
from threading import Lock
from typing import Any, Protocol, TextIO, cast
from dataclasses import replace

from prompt_toolkit import Application, PromptSession
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import ConditionalCompleter
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition, has_focus, is_searching
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.input import Input
from prompt_toolkit.key_binding import (
    ConditionalKeyBindings,
    KeyBindings,
    KeyPressEvent,
    merge_key_bindings,
)
from prompt_toolkit.layout import (
    ConditionalContainer,
    Dimension,
    DynamicContainer,
    Float,
    FloatContainer,
    HSplit,
    Layout,
    VSplit,
    Window,
)
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.containers import AnyContainer
from prompt_toolkit.layout.margins import ScrollbarMargin
from prompt_toolkit.layout.menus import CompletionsMenu
from prompt_toolkit.mouse_events import MouseEvent, MouseEventType
from prompt_toolkit.output import Output
from prompt_toolkit.output.color_depth import ColorDepth
from prompt_toolkit.styles import Style, merge_styles
from prompt_toolkit.utils import get_cwidth
from prompt_toolkit.widgets import (
    Frame,
    Label,
    SearchToolbar,
    TextArea,
    ValidationToolbar,
)

from clang_toolkit.cli.file_explorer import FileExplorer
from clang_toolkit._generated.match.v1 import match_service_pb2 as pb
from clang_toolkit.cli.runtime.management import _render_status
from clang_toolkit.cli.highlight import STYLE, WORKSPACE_SYNTAX, ReplLexer
from clang_toolkit.cli.workspace_context import CommandContext
from clang_toolkit.cli.workspace_menu import ActionMenu, WorkspaceAction
from clang_toolkit.cli.workspace_output import MAX_TRANSCRIPT_CHARS, WorkspaceOutput
from clang_toolkit.cli.workspace_transcript import (
    CodeRows,
    StyledBlock,
    TranscriptControl,
    TranscriptLexer,
    command_block,
    error_span,
)
from clang_toolkit.cli.workspace_markdown import MarkdownPanel, output_markdown, render_markdown
from clang_toolkit.cli.workspace_editing import control_enter_keys, editing_bindings
from clang_toolkit.cli.workspace_state import PanelEntry, display_snapshot
from clang_toolkit.cli.workspace_result_tree import ResultTrees, SnapshotReader, TreeSelection
from clang_toolkit.cli.workspace_tree import WorkspaceTree
from clang_toolkit.cli.runtime.progress import BatchProgress
from clang_toolkit.cli.workspace_source import SourceWindow
from clang_toolkit.cli.workspace_source_data import SourceSnapshot, SourceTarget, source_snapshot


class CommandOutcome(Protocol):
    output: str | None
    success: bool
    markdown: str | None


class WorkspaceConsole:
    def __init__(
        self,
        session: PromptSession[str],
        cwd: Path,
        execute: Callable[[str], Awaitable[CommandOutcome]],
        *,
        cancel: Callable[[], Awaitable[str]] | None = None,
        server_status: Callable[[], Awaitable[pb.ServerStatusResponse]] | None = None,
        outline: Callable[[frozenset[str], dict[str, int]], Awaitable[list[PanelEntry]]]
        | None = None,
        resources: Callable[[], Awaitable[list[PanelEntry]]] | None = None,
        result_outline: SnapshotReader | None = None,
        source_reader: Callable[[SourceTarget, tuple[Any, ...]], Awaitable[SourceSnapshot]] | None = None,
        batch_status: Callable[[str], Awaitable[BatchProgress]] | None = None,
        batch_cancel: Callable[[str], Awaitable[BatchProgress]] | None = None,
        input: Input | None = None,
        output: Output | None = None,
    ) -> None:
        self.session = session
        self.execute = execute
        self.cancel = cancel
        self.read_server_status = server_status
        self.read_outline = outline
        self.read_resources = resources
        self.read_source = source_reader
        self.read_batch_status = batch_status
        self.cancel_batch = batch_cancel
        self.batch_monitors: dict[str, asyncio.Task[None]] = {}
        self.progress_lock = Lock()
        self.pending_progress: dict[str, BatchProgress] = {}
        self.progress_states: dict[str, BatchProgress] = {}
        self.source_origin: Window | None = None
        self.source_task: asyncio.Task[None] | None = None
        self.source_tasks: set[asyncio.Task[None]] = set()
        self.source_generation = 0
        self.source = SourceWindow(self.close_source, lambda: self.app.invalidate(), self.interrupt_source, self.request_exit)
        self.server_snapshot: pb.ServerStatusResponse | None = None
        self.server_sampled: float | None = None
        self.server_error = (
            "Checking server…" if server_status else "Server status unavailable"
        )
        self.monitor_task: asyncio.Task[None] | None = None
        self.panel_refresh_task: asyncio.Task[None] | None = None
        self.panels_dirty = False
        self.busy = False
        self.closing = False
        self.files_visible = False
        self.loading_files = False
        self.follow = True
        self.connection = "Session open"
        self.status = "Ready"
        self.started: float | None = None
        self.last_elapsed: float | None = None
        self.exit_code = 0
        self.command_task: asyncio.Task[None] | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self.previous_focus: Window | None = None
        self.menu_visible = False
        self.context_visible = True
        self.panel_requested = False
        self.panel_kind = "help"
        self.wrap_results = True
        self.last_source = ""
        self.command_position: int | None = None
        self.context = CommandContext()
        self.server_panel = MarkdownPanel()
        self.server_panel.set_markdown("## Server status\n\nChecking server…")
        self.outline = WorkspaceTree(self.refresh_panels, self.prepare, self.open_source)
        self.resources = WorkspaceTree(self.refresh_panels, self.prepare)
        self.right_panel = Frame(
            HSplit(
                [
                    DynamicContainer(self.panel_content),
                    Window(
                        FormattedTextControl(self.panel_actions),
                        height=1,
                        style="class:toolbar",
                    ),
                ]
            ),
            title=self.panel_title,
            width=lambda: self.panel_width,
        )
        self.search = SearchToolbar()
        self.transcript_lexer = TranscriptLexer()
        self.results = TextArea(
            text="CTK console\n",
            lexer=self.transcript_lexer,
            focus_on_click=True,
            wrap_lines=Condition(lambda: self.wrap_results),
            read_only=True,
            scrollbar=True,
            height=Dimension(min=3, weight=1),
            search_field=self.search,
            name="workspace-results",
        )
        self.results.control = TranscriptControl(
            buffer=self.results.buffer,
            lexer=self.transcript_lexer,
            input_processors=[
                CodeRows(lambda: self.wrap_results),
                TreeSelection(lambda line: self.app.layout.has_focus(self.results.window) and self.result_trees.at(line) is not None),
            ],
            focus_on_click=True,
            search_buffer_control=self.search.control,
        )
        self.results.window.content = self.results.control
        async def local_result_outline(kind: str, value: Any, expanded: frozenset[str], pages: dict[str, int]) -> list[PanelEntry] | None:
            return await asyncio.to_thread(display_snapshot, kind, value, expanded, pages)

        self.result_trees = ResultTrees(
            self.results, self.transcript_lexer, self._append,
            result_outline or local_result_outline, self.result_text_replaced,
        )
        self.result_tree_tasks: set[asyncio.Task[None]] = set()
        self._original_result_mouse = self.results.control.mouse_handler
        self.results.control.mouse_handler = self.results_mouse  # type: ignore[method-assign, assignment]
        self.buffer = session.default_buffer
        self.buffer.accept_handler = self._accept
        if self.buffer.completer is not None:
            self.buffer.completer = ConditionalCompleter(
                self.buffer.completer, Condition(lambda: not self.busy)
            )
        self.editor_control = BufferControl(
            buffer=self.buffer,
            lexer=ReplLexer(semantic_matchers=True),
            focus_on_click=True,
            search_buffer_control=self.search.control,
        )
        self.editor = Window(
            self.editor_control,
            height=lambda: Dimension.exact(self.editor_height()),
            wrap_lines=True,
            get_line_prefix=lambda line, wrap: [
                ("class:line-number", f"{line + 1:>4} │ " if not wrap else "     │ "),
            ],
            right_margins=[ScrollbarMargin(display_arrows=True)],
        )
        self.files = FileExplorer(cwd, self.activate_file)
        self.file_panel = Frame(
            HSplit(
                [
                    Label(lambda: str(self.files.root), wrap_lines=False),
                    self.files.window,
                    Label(lambda: self.files.notice, wrap_lines=False),
                ]
            ),
            title="Local files",
            width=30,
        )
        divider = Window(
            FormattedTextControl(self.editor_title), height=1, style="class:divider"
        )
        body = HSplit(
            [
                VSplit(
                    [
                        ConditionalContainer(
                            self.file_panel,
                            Condition(lambda: self.files_visible and not self.narrow),
                        ),
                        HSplit(
                            [self.results, divider, self.editor, ValidationToolbar()]
                        ),
                        ConditionalContainer(
                            self.right_panel,
                            Condition(lambda: self.show_context),
                        ),
                    ]
                ),
                self.search,
                Window(
                    FormattedTextControl(self.footer),
                    height=1,
                    style="class:status",
                ),
            ]
        )
        self.menu = ActionMenu(
            [
                WorkspaceAction(
                    lambda: (
                        "Close local files  F3"
                        if self.files_visible
                        else "Browse local files  F3"
                    ),
                    self.toggle_files,
                ),
                WorkspaceAction(lambda: "Refresh files  F5", self.refresh_files),
                WorkspaceAction(
                    lambda: (
                        "Hide hidden files"
                        if self.files.show_hidden
                        else "Show hidden files"
                    ),
                    self.toggle_hidden,
                ),
                WorkspaceAction(
                    lambda: (
                        "Pause following results"
                        if self.follow
                        else "Resume following results"
                    ),
                    self.toggle_follow,
                ),
                WorkspaceAction(lambda: "Show latest results", self.show_latest),
                WorkspaceAction(lambda: "Search results  Ctrl+R", self.search_results),
                WorkspaceAction(
                    lambda: (
                        "Disable result wrapping"
                        if self.wrap_results
                        else "Enable result wrapping"
                    ),
                    self.toggle_wrap,
                ),
                WorkspaceAction(lambda: "Clear displayed results", self.clear_results),
                WorkspaceAction(
                    lambda: (
                        "Hide command help"
                        if self.context_visible
                        else "Show command help"
                    ),
                    self.toggle_context,
                ),
                WorkspaceAction(lambda: "Workspace shortcuts  F1", self.show_help),
                WorkspaceAction(
                    lambda: "Prepare console help", lambda: self.prepare("help")
                ),
                WorkspaceAction(
                    lambda: "Binding outline  F7", lambda: self.toggle_panel("outline")
                ),
                WorkspaceAction(
                    lambda: "Open files and sessions  F8",
                    lambda: self.toggle_panel("resources"),
                ),
                WorkspaceAction(
                    lambda: "Live server status  F9",
                    lambda: self.toggle_panel("server"),
                ),
                WorkspaceAction(
                    lambda: "List open files", lambda: self.prepare("file list")
                ),
                WorkspaceAction(
                    lambda: "List retained sessions",
                    lambda: self.prepare("session list"),
                ),
                WorkspaceAction(
                    lambda: "List bindings", lambda: self.prepare("bindings")
                ),
                WorkspaceAction(
                    lambda: "Show server status", lambda: self.prepare("server status")
                ),
                WorkspaceAction(lambda: "Run command  Ctrl+J", self.run_draft),
                WorkspaceAction(lambda: "Quit  F10", self.request_exit),
            ],
            self.close_menu,
        )
        toolbar = Window(
            FormattedTextControl(self.toolbar), height=1, style="class:toolbar"
        )
        self.root = FloatContainer(
            HSplit([toolbar, body]),
            floats=[
                Float(
                    xcursor=True,
                    ycursor=True,
                    content=CompletionsMenu(max_height=8, scroll_offset=1),
                ),
                Float(
                    left=0,
                    top=1,
                    height=lambda: max(3, self.app.output.get_size().rows - 4),
                    content=ConditionalContainer(
                        self.file_panel,
                        Condition(lambda: self.files_visible and self.narrow),
                    ),
                ),
                Float(
                    left=1, right=1, top=1, bottom=1,
                    content=ConditionalContainer(self.source.container, Condition(lambda: self.source.visible)),
                ),
                Float(
                    right=0,
                    top=1,
                    width=lambda: min(
                        self.panel_width, self.app.output.get_size().columns
                    ),
                    height=lambda: max(3, self.app.output.get_size().rows - 4),
                    content=ConditionalContainer(
                        self.right_panel, Condition(lambda: self.panel_overlay)
                    ),
                ),
                Float(
                    left=0,
                    top=1,
                    width=lambda: min(54, self.app.output.get_size().columns),
                    height=lambda: min(
                        len(self.menu.actions) + 2,
                        max(3, self.app.output.get_size().rows - 3),
                    ),
                    content=ConditionalContainer(
                        Frame(self.menu.window, title="Actions · scroll or use arrows"),
                        Condition(lambda: self.menu_visible),
                    ),
                ),
            ],
        )
        self.app: Application[None] = Application(
            layout=Layout(self.root, focused_element=self.editor),
            key_bindings=merge_key_bindings(
                [
                    ConditionalKeyBindings(
                        session.key_bindings or KeyBindings(), has_focus(self.buffer)
                    ),
                    editing_bindings(
                        self.buffer,
                        has_focus(self.buffer)
                        & ~is_searching
                        & Condition(lambda: not self.closing),
                    ),
                    ConditionalKeyBindings(self._bindings(), Condition(lambda: not self.source.visible)),
                ]
            ),
            style=merge_styles(
                [
                    STYLE,
                    Style.from_dict(
                        {
                            "": "bg:#101820 #d8dee9",
                            **WORKSPACE_SYNTAX,
                            "diagnostic": "#ff8080",
                            "status": "bg:ansiblue ansiwhite",
                            "divider": "bg:ansibrightblack ansiwhite",
                            "prompt": "bold ansicyan",
                            "line-number": "#90a4b4",
                            "scrollbar.background": "#44596a bg:#182a38",
                            "scrollbar.button": "#62b3ff bg:#182a38",
                            "scrollbar.arrow": "#90a4b4 bg:#182a38",
                            "code": "bg:#182a38",
                            "code-border": "#62b3ff",
                            "muted": "ansibrightblack",
                            "file-selected": "bg:#315d80 #ffffff bold",
                            "file-folder": "#62b3ff",
                            "toolbar": "bg:#243746 #d8dee9",
                            "action": "#d8dee9",
                            "action-selected": "bg:#315d80 #ffffff bold",
                            "actions": "bg:#182a38 #d8dee9",
                            "tree": "#d8dee9",
                            "tree-selected": "bg:#315d80 #ffffff bold",
                            "source-link": "underline #62b3ff",
                            "source-range": "bg:#315d80",
                            "pygments.keyword": WORKSPACE_SYNTAX["keyword"],
                            "pygments.literal.string": WORKSPACE_SYNTAX["string"],
                            "pygments.literal.number": WORKSPACE_SYNTAX["number"],
                            "pygments.comment": WORKSPACE_SYNTAX["comment"],
                            "pygments.operator": WORKSPACE_SYNTAX["operator"],
                            "pygments.punctuation": WORKSPACE_SYNTAX["punctuation"],
                            "panel-close": "bold #ff8080",
                            "completion-menu": "bg:#182a38 #d8dee9",
                            "completion-menu.completion": "bg:#182a38 #d8dee9",
                            "completion-menu.completion.current": "bg:#315d80 #ffffff noreverse",
                            "completion-menu.meta.completion": "bg:#182a38 #90a4b4",
                            "completion-menu.meta.completion.current": "bg:#315d80 #d8dee9",
                            "completion-menu.scrollbar.background": "bg:#243746",
                            "completion-menu.scrollbar.button": "bg:#62b3ff",
                        }
                    ),
                ]
            ),
            full_screen=True,
            mouse_support=True,
            color_depth=ColorDepth.DEPTH_8_BIT,
            before_render=lambda app: self.context.update(
                self.buffer.text or self.last_source, str(self.files.root)
            ),
            refresh_interval=0.25,
            input=input,
            output=output,
        )
        self.stream = WorkspaceOutput(self.write_output)

    @property
    def narrow(self) -> bool:
        return self.app.output.get_size().columns < 80

    @property
    def panel_width(self) -> int:
        return 36 if self.panel_kind == "help" else 48

    @property
    def panel_overlay(self) -> bool:
        return self.context_visible and self.panel_requested and not self.show_context

    def panel_content(self) -> AnyContainer:
        panels: dict[str, AnyContainer] = {
            "help": self.context,
            "outline": self.outline.container,
            "resources": self.resources.container,
            "server": self.server_panel,
        }
        return panels[self.panel_kind]

    def panel_window(self) -> Window:
        return {
            "help": self.context.window,
            "outline": self.outline.window,
            "resources": self.resources.window,
            "server": self.server_panel.window,
        }[self.panel_kind]

    def panel_title(self) -> StyleAndTextTuples:
        name = {
            "help": "Command help · F4",
            "outline": "Bindings · F7",
            "resources": "Resources · F8",
            "server": "Server · F9",
        }[self.panel_kind]

        def close(event: MouseEvent) -> None:
            if event.event_type == MouseEventType.MOUSE_UP:
                self.close_panel()

        return [("", name + " "), ("class:panel-close", "[×]", close)]

    def panel_actions(self) -> StyleAndTextTuples:
        if self.panel_kind not in {"outline", "resources"}:
            return [("class:muted", " Scroll · F6 focus · × close")]
        tree = self.outline if self.panel_kind == "outline" else self.resources
        fragments: StyleAndTextTuples = (
            [("class:muted", " Enter expand/collapse · ←/→ scroll ")]
            if self.panel_kind == "outline"
            else []
        )
        labels = {"p": "Print [p]", "a": "Attach [a]", "c": "Close [c]"}
        for key, _ in tree.current.commands if tree.current else ():

            def choose(event: MouseEvent, selected: str = key) -> None:
                if event.event_type == MouseEventType.MOUSE_UP:
                    tree.command(selected)

            fragments.append(("class:action", " " + labels[key] + " ", choose))
        return fragments

    def close_panel(self) -> None:
        self.context_visible = False
        self.app.layout.focus(self.editor)

    def toggle_panel(self, kind: str) -> None:
        if self.panel_kind == kind and (self.show_context or self.panel_overlay):
            self.close_panel()
        else:
            self.panel_kind = kind
            self.context_visible = True
            self.panel_requested = True
            if self.show_context or self.panel_overlay:
                self.app.layout.focus(self.panel_window())
            self.refresh_panels()

    def refresh_panels(self) -> None:
        if not self.app.is_running:
            return
        self.panels_dirty = True
        if self.panel_refresh_task is None or self.panel_refresh_task.done():
            self.panel_refresh_task = self.app.create_background_task(
                self._refresh_panels()
            )

    async def _refresh_panels(self) -> None:
        while self.panels_dirty:
            self.panels_dirty = False
            await self._refresh_panel_once()

    async def _refresh_panel_once(self) -> None:
        tree = self.outline if self.panel_kind == "outline" else self.resources
        try:
            if self.panel_kind == "outline" and self.read_outline is not None:
                tree.update(
                    await self.read_outline(frozenset(tree.expanded), dict(tree.pages))
                )
            elif self.panel_kind == "resources" and self.read_resources is not None:
                async with asyncio.timeout(5):
                    tree.update(await self.read_resources())
            elif self.panel_kind in {"outline", "resources"}:
                tree.notice = "Inventory unavailable in this session"
        except Exception as exc:  # noqa: BLE001 - optional panel boundary
            tree.update([])
            tree.notice = f"Cannot refresh: {exc}"
        self.app.invalidate()

    async def _monitor_server(self) -> None:
        if self.read_server_status is None:
            return
        while not self.closing:
            try:
                async with asyncio.timeout(3):
                    self.server_snapshot = await self.read_server_status()
                self.server_sampled = monotonic()
                self.server_error = ""
                raw = _render_status(self.server_snapshot)
                markdown = "## Live server status\n\nRefreshed every **2 seconds**.\n\n"
                for section in raw.split("\n\n"):
                    lines = section.splitlines()
                    markdown += "### " + lines[0] + "\n\n"
                    for line in lines[1:]:
                        label, _, value = line.rpartition("  ")
                        markdown += (
                            "- **" + label.strip() + "**: " + value.strip() + "\n"
                        )
                    markdown += "\n"
                self.server_panel.set_markdown(markdown, 44)
            except Exception as exc:  # noqa: BLE001 - periodic read boundary
                self.server_error = "Server unavailable: " + str(exc)[:70]
                self.server_panel.set_markdown(
                    "## Server status\n\n**Refresh failed.** Last sample is stale.\n\n"
                    + self.server_error,
                    44,
                )
            if self.context_visible and self.panel_kind == "resources":
                self.refresh_panels()
            self.app.invalidate()
            await asyncio.sleep(2)

    @property
    def show_context(self) -> bool:
        required = (
            64
            + self.panel_width
            + (30 if self.files_visible and not self.narrow else 0)
        )
        return self.context_visible and self.app.output.get_size().columns >= required

    def editor_height(self) -> int:
        size = self.app.output.get_size()
        width = size.columns - (30 if self.files_visible and not self.narrow else 0)
        if self.show_context:
            width -= self.panel_width
        content_width = max(1, width - 8)
        rows = sum(
            max(1, (get_cwidth(line) + content_width - 1) // content_width)
            for line in self.buffer.text.split("\n")
        )
        cap = max(1, (size.rows - 3) // 2)
        return min(rows, cap)

    def editor_title(self) -> str:
        lines = self.buffer.document.line_count
        return f" Command · {lines} line{'s' if lines != 1 else ''} · Ctrl+Enter / Ctrl+J run · Enter completes"

    def footer(self) -> str:
        active = next((progress for progress in reversed(self.progress_states.values()) if progress.active), None)
        if active is not None:
            # Reuse the existing status row so live progress stays visible even
            # when the batch body itself produces long output.
            filled = 12 * min(active.total, active.done) // max(1, active.total)
            return f" {self.status} · Batch [{('━' * filled).ljust(12, '─')}] {active.done}/{active.total} files"
        elapsed = (
            monotonic() - self.started
            if self.started is not None
            else self.last_elapsed
        )
        fields = [self.connection, self.status]
        if elapsed is not None:
            fields.append(f"{elapsed:.1f}s")
        doc = self.buffer.document
        location = f"Input {doc.cursor_position_row + 1}:{doc.cursor_position_col + 1}"
        text = " | ".join(
            [*fields, location, "Follow" if self.follow else "Scroll paused"]
        )
        if self.server_snapshot is not None:
            status = self.server_snapshot
            rss = (
                f"{status.resident_memory_bytes / 1024**2:.0f}M"
                if status.HasField("resident_memory_bytes")
                else "unavailable"
            )
            live = f"RSS {rss} · Sessions {status.active_sessions}"
            if self.server_error:
                live += " · stale"
            if len(text) + len(live) + 4 > self.app.output.get_size().columns:
                text = " | ".join([self.status, live])
            else:
                text += " | " + live
        elif self.read_server_status is not None:
            text += " | " + self.server_error
        return " " + text

    def toolbar(self) -> StyleAndTextTuples:
        fragments: StyleAndTextTuples = [
            ("class:toolbar", " CTK console | "),
            ("class:toolbar", "Actions [F2] ", self.toolbar_mouse),
        ]
        for kind, label in [
            ("help", "Help"),
            ("outline", "Outline"),
            ("resources", "Resources"),
            ("server", "Server"),
        ]:

            def click(event: MouseEvent, selected: str = kind) -> None:
                if event.event_type == MouseEventType.MOUSE_UP:
                    self.toggle_panel(selected)

            fragments.append(("class:toolbar", " | " + label, click))
        return fragments

    def toolbar_mouse(self, event: MouseEvent) -> None:
        if event.event_type == MouseEventType.MOUSE_UP:
            self.toggle_menu()

    def toggle_menu(self) -> None:
        if self.menu_visible:
            self.close_menu()
        else:
            self.previous_focus = self.app.layout.current_window
            self.menu_visible = True
            self.app.layout.focus(self.menu.window)

    def close_menu(self) -> None:
        self.menu_visible = False
        # A dynamic panel may have been replaced or hidden while Actions was open.
        available = {self.editor, self.results.window}
        available.update(
            window
            for window in self.app.layout.find_all_windows()
            if window.content is self.search.control
        )
        if self.files_visible:
            available.add(self.files.window)
        if self.show_context or self.panel_overlay:
            available.add(self.panel_window())
        current = self.app.layout.current_window
        target = self.previous_focus if self.previous_focus in available else current
        self.app.layout.focus(target if target in available else self.editor)
        self.previous_focus = None

    def results_mouse(self, event: MouseEvent) -> object:
        if event.event_type in {
            MouseEventType.MOUSE_DOWN,
            MouseEventType.SCROLL_UP,
            MouseEventType.SCROLL_DOWN,
        }:
            self.follow = False
            self.app.layout.focus(self.results.window)
        if event.event_type in {MouseEventType.SCROLL_UP, MouseEventType.SCROLL_DOWN}:
            if event.event_type == MouseEventType.SCROLL_UP:
                self.results.buffer.cursor_up(3)
            else:
                self.results.buffer.cursor_down(3)
            return None
        if event.event_type == MouseEventType.MOUSE_UP:
            found = self.result_trees.at(event.position.y)
            if found is not None:
                _, index = found
                item = found[0].entries[index]
                if item.source is not None and event.position.x >= 2 * item.depth + 2:
                    self._original_result_mouse(event)
                    self.open_source(item.source)
                    return None
                if found[0].kind == "batch_progress" and found[0].value.active and event.position.x >= len(found[0].text) - len("[Cancel]"):
                    self._original_result_mouse(event)
                    self.cancel_progress(found[0].value)
                    return None
                if item.page is not None or (item.expandable and 2 * item.depth <= event.position.x < 2 * item.depth + 2):
                    self._original_result_mouse(event)
                    self.navigate_result_tree("enter")
                    return None
        return self._original_result_mouse(event)

    def open_source(self, target: SourceTarget) -> None:
        self.source_generation += 1
        generation = self.source_generation
        self.source_origin = self.app.layout.current_window
        self.source.visible = True
        self.source.snapshot = None
        self.source.target = None
        self.source.code.buffer.set_document(Document(""), bypass_readonly=True)
        self.source.tree.update([])
        self.source.notice = "Loading source…"
        self.app.layout.focus(self.source.code.window)
        self.app.invalidate()
        values = tuple(tree.value for tree in self.result_trees.trees if tree.kind != "batch_progress")

        async def load() -> None:
            try:
                snapshot = await self.read_source(target, values) if self.read_source else await asyncio.to_thread(source_snapshot, target, values, self.files.root)
                if self.source.visible and generation == self.source_generation:
                    self.source.show(snapshot, target)
            except Exception as exc:  # noqa: BLE001 - optional source viewer boundary
                if self.source.visible and generation == self.source_generation:
                    self.source.notice = f"Cannot open source: {exc}"
                    self.app.invalidate()

        self.source_task = self.app.create_background_task(load())
        self.source_tasks.add(self.source_task)
        self.source_task.add_done_callback(self.source_tasks.discard)

    def close_source(self) -> None:
        self.source.visible = False
        # Keep the originating tree selection and the unsent editor draft.
        origin = self.source_origin
        self.source_origin = None
        try:
            self.app.layout.focus(origin or self.editor)
        except ValueError:
            self.app.layout.focus(self.editor)
        self.app.invalidate()

    def interrupt_source(self) -> None:
        if self.busy:
            self.app.create_background_task(self._cancel())
        else:
            self.close_source()

    def show_batch_progress(self, progress: BatchProgress) -> None:
        """Coalesce worker notifications before touching prompt_toolkit state."""
        if self.loop is not None and self.app.is_running:
            with self.progress_lock:
                schedule = not self.pending_progress
                self.pending_progress[progress.run_id] = progress
            if schedule:
                self.loop.call_soon_threadsafe(self.flush_progress)
        else:
            self.result_trees.progress(progress)

    def flush_progress(self) -> None:
        with self.progress_lock:
            pending, self.pending_progress = self.pending_progress, {}
        for progress in pending.values():
            previous = self.progress_states.get(progress.run_id)
            if previous and progress.durable and previous.revision > progress.revision:
                continue
            self.progress_states.pop(progress.run_id, None)
            self.progress_states[progress.run_id] = progress
            if len(self.progress_states) > 20:
                self.progress_states.pop(next(iter(self.progress_states)))
            self.result_trees.progress(progress)
            if progress.durable and progress.active and self.read_batch_status and progress.run_id not in self.batch_monitors:
                if len(self.batch_monitors) >= 20:
                    oldest = self.batch_monitors.pop(next(iter(self.batch_monitors)))
                    oldest.cancel()
                self.batch_monitors[progress.run_id] = self.app.create_background_task(self.monitor_batch(progress))
        self.app.invalidate()

    async def monitor_batch(self, progress: BatchProgress) -> None:
        try:
            while progress.active and not self.closing:
                await asyncio.sleep(1)
                assert self.read_batch_status is not None
                progress = await self.read_batch_status(progress.run_id)
                self.show_batch_progress(progress)
        except Exception as exc:  # noqa: BLE001 - keep the console usable after disconnects
            self.show_batch_progress(replace(progress, state="status unavailable"))
            self.write_output(f"Batch {progress.run_id}: status unavailable: {exc}")
        finally:
            if self.batch_monitors.get(progress.run_id) is asyncio.current_task():
                self.batch_monitors.pop(progress.run_id, None)

    def cancel_progress(self, progress: BatchProgress) -> None:
        async def cancel() -> None:
            try:
                if progress.durable and self.cancel_batch:
                    self.show_batch_progress(await self.cancel_batch(progress.run_id))
                elif self.busy:
                    await self._cancel()
            except Exception as exc:  # noqa: BLE001 - cancellation boundary
                self.write_output(f"Batch cancellation was not confirmed: {exc}")
        self.app.create_background_task(cancel())

    def result_text_replaced(self, start: int, end: int, length: int) -> None:
        if self.command_position is not None:
            if self.command_position >= end:
                self.command_position += length - (end - start)
            elif self.command_position >= start:
                self.command_position = None

    def navigate_result_tree(self, direction: str) -> None:
        self.follow = False
        async def navigate() -> None:
            await self.result_trees.navigate(direction)
            self.app.invalidate()

        task = self.app.create_background_task(navigate())
        self.result_tree_tasks.add(task)
        task.add_done_callback(self.result_tree_tasks.discard)

    def write(self, text: str) -> None:
        if self.loop is not None and self.app.is_running:
            self.loop.call_soon_threadsafe(self._append, text)
        else:
            self._append(text)

    def write_output(self, text: str) -> None:
        markdown = output_markdown(text)
        if self.loop is not None and self.app.is_running:
            self.loop.call_soon_threadsafe(self.write_markdown, markdown)
        else:
            self.write_markdown(markdown)

    def _append(
        self, text: str, styled: list[StyleAndTextTuples] | None = None
    ) -> None:
        old = self.results.text
        if styled is not None:
            self.transcript_lexer.blocks.append(StyledBlock(len(old), text, styled))
        combined = old + text + "\n"
        removed = max(0, len(combined) - MAX_TRANSCRIPT_CHARS)
        if removed:
            marker = "[Earlier display output trimmed; use save for full results]\n"
            cut = len(combined) - (MAX_TRANSCRIPT_CHARS - len(marker))
            self.transcript_lexer.trim(cut, removed)
            self.result_trees.trim(cut, removed)
            if self.command_position is not None:
                self.command_position = (
                    self.command_position - removed
                    if self.command_position >= cut
                    else None
                )
            combined = marker + combined[-(MAX_TRANSCRIPT_CHARS - len(marker)) :]
        position = (
            len(combined)
            if self.follow
            else max(0, self.results.buffer.cursor_position - removed)
        )
        self.results.buffer.set_document(
            Document(combined, cursor_position=min(position, len(combined))),
            bypass_readonly=True,
        )
        self.app.invalidate()

    def _accept(self, buffer: Buffer) -> bool:
        if self.busy or self.closing:
            return True
        if not buffer.text.strip():
            return False
        self.busy = True
        self.status = "Running"
        self.started = monotonic()
        self.command_task = asyncio.create_task(self._execute(buffer.text))
        return False

    def run_draft(self) -> None:
        self.app.layout.focus(self.editor)
        if self.busy or self.closing:
            self.write("A command is running; your next draft is kept.")
        else:
            self.buffer.validate_and_handle()

    async def _execute(self, source: str) -> None:
        self.last_source = source
        self.command_position = len(self.results.text)
        self._append(command_block(source))
        try:
            outcome = await self.execute(source)
            self.flush_progress()
            if not outcome.success:
                self.exit_code = 1
            self.status = "Ready" if outcome.success else "Command failed"
            if outcome.output is None:
                self.closing = True
            elif outcome.output or getattr(outcome, "outline_value", None) is not None:
                output = (
                    self.mark_command_error(source, outcome.output)
                    if not outcome.success
                    else outcome.output
                )
                outline_value = getattr(outcome, "outline_value", None)
                if outcome.success and outline_value is not None and await self.result_trees.show(*outline_value):
                    pass
                elif outcome.success and outcome.markdown is not None:
                    self.write_markdown(outcome.markdown)
                else:
                    self.write_markdown(output_markdown(output))
                if not outcome.success:
                    self.explain_match_error(outcome.output)
        except Exception as exc:  # noqa: BLE001 - background CLI error boundary
            # Command task is the CLI error boundary; keep the draft/UI recoverable.
            self.exit_code = 1
            self.status = "Command failed"
            self.write_markdown(output_markdown(self.mark_command_error(source, f"error: {exc}")))
            self.explain_match_error(str(exc))
        finally:
            self.last_elapsed = monotonic() - self.started if self.started else None
            self.started = None
            self.busy = False
            self.command_position = None
            self.refresh_panels()
            self.app.invalidate()
            if self.closing and self.app.is_running:
                self.app.exit()

    def mark_command_error(self, source: str, message: str) -> str:
        span = error_span(source, message)
        start = self.command_position
        original = command_block(source)
        if (
            span is None
            or start is None
            or not self.results.text.startswith(original, start)
        ):
            return message
        marked = command_block(source, span)
        document = self.results.buffer.document
        cursor = document.cursor_position
        insertion = start + sum(
            len(line) for line in original.splitlines(keepends=True)[: span.line]
        )
        if cursor >= insertion:
            cursor += len(marked) - len(original)
        text = document.text[:start] + marked + document.text[start + len(original) :]
        self.transcript_lexer.replace(start, start + len(original), len(marked))
        self.result_trees.shift(start, start + len(original), len(marked))
        self.results.buffer.set_document(Document(text, cursor), bypass_readonly=True)
        # Parser diagnostics already contain a plain duplicate source/caret.
        # Keep the explanation and any suggested repair below the marked block.
        lines = message.splitlines()
        source_line = source.split("\n")[span.line - 1].expandtabs(4)
        for index in range(1, len(lines) - 1):
            if lines[index] == source_line and lines[index + 1].strip() == "^":
                del lines[index : index + 2]
                break
        return "\n".join(lines)

    def explain_match_error(self, message: str) -> None:
        if "match row limit exceeded" in message:
            self.write(
                "The query exceeded the server's row budget. Header declarations also count; narrow the matcher and retry. For main-file functions:"
            )
            self.write(
                command_block(
                    "functionDecl(isExpansionInMainFile(), unless(isImplicit()))"
                )
            )
        elif "cursor unavailable" in message or "cursor expired or closed" in message:
            self.write(
                "The native cursor expired or was closed. Parse the file again, or select a live session in Resources [F8]."
            )

    def prepare(self, source: str) -> None:
        if self.buffer.text.strip():
            self.write(
                "Draft kept. Clear it with Ctrl+C before preparing another command."
            )
        else:
            self.buffer.document = Document(source, cursor_position=len(source))
        self.app.layout.focus(self.editor)

    def activate_file(self) -> None:
        item = self.files.current
        if item is None or self.loading_files:
            return
        if item.directory:
            if item.path in self.files.expanded:
                self.files.expanded.remove(item.path)
                self.files.rebuild()
            else:
                self.app.create_background_task(self._load_files(item.path))
        else:
            self.prepare("parse " + json.dumps(str(item.path), ensure_ascii=False))
            if self.narrow:
                self.files_visible = False

    async def _load_files(self, path: Path) -> None:
        self.loading_files = True
        self.files.notice = "Loading local files…"
        self.app.invalidate()
        try:
            children, truncated = await asyncio.to_thread(self.files.scan, path)
            self.files.children[path] = children
            self.files.expanded.add(path)
            self.files.notice = (
                "Listing limited to 500 entries"
                if truncated
                else "Enter opens · F5 refresh · F3 close"
            )
            self.files.rebuild()
        except OSError as exc:
            self.files.notice = f"Cannot read directory: {exc}"
        finally:
            self.loading_files = False
            self.app.invalidate()

    def toggle_files(self) -> None:
        self.files_visible = not self.files_visible
        self.app.layout.focus(self.files.window if self.files_visible else self.editor)
        if self.files_visible and not self.files.children:
            self.app.create_background_task(self._load_files(self.files.root))
        self.app.invalidate()

    def refresh_files(self) -> None:
        if self.loading_files:
            return
        self.files.children.clear()
        self.files.expanded = {self.files.root}
        self.app.create_background_task(self._load_files(self.files.root))

    def toggle_follow(self) -> None:
        self.follow = not self.follow
        self.app.layout.focus(self.editor)
        if self.follow:
            self.results.buffer.cursor_position = len(self.results.text)
        self.status = "Following results" if self.follow else "Results follow paused"

    def show_latest(self) -> None:
        self.follow = True
        self.results.buffer.cursor_position = len(self.results.text)

    def clear_results(self) -> None:
        self.command_position = None
        self.transcript_lexer.blocks.clear()
        self.result_trees.trees.clear()
        self.results.buffer.set_document(Document(""), bypass_readonly=True)

    def toggle_wrap(self) -> None:
        self.wrap_results = not self.wrap_results

    def toggle_context(self) -> None:
        self.toggle_panel("help")

    def toggle_hidden(self) -> None:
        self.files.show_hidden = not self.files.show_hidden
        self.refresh_files()

    def search_results(self) -> None:
        from prompt_toolkit.search import start_search

        self.follow = False
        self.app.layout.focus(self.results.window)
        start_search(self.results.control)

    def write_markdown(self, markdown: str) -> None:
        info = self.results.window.render_info
        width = info.window_width if info else self.app.output.get_size().columns - 2
        text, lines = render_markdown(markdown, max(12, width - 1))
        self._append(text, lines)

    def show_help(self) -> None:
        self.write_markdown(
            "## Workspace shortcuts\n\n"
            "**F1** Shortcuts · **F2** Actions · **F3** Files · **F4** Help · **F5** Refresh · **F6** Focus\n\n"
            "**F7** Outline · **F8** Resources · **F9** Server · **F10** Quit\n\n"
            "- **Ctrl+Enter** or **Ctrl+J** runs the whole draft. **Enter** runs complete input at its end; otherwise it adds an indented line. **Actions → Run command** also executes. Paired brackets and quotes keep the cursor inside.\n"
            "- **Ctrl+R** searches history or results; **Ctrl+C** clears a draft or requests cancellation.\n"
            "- **Escape** closes the focused panel or menu. Files are local; selecting a file prepares `parse`.\n"
            "- Outline: **Enter** expands/collapses; **Left/Right** pans; **p** prepares `print`. Select Next/Previous page for 50 items.\n"
            "- Resources: **a** prepares attach; **c** prepares close. **Enter** in the command area runs prepared commands."
        )
        self.app.layout.focus(self.editor)

    def request_exit(self) -> None:
        self.closing = True
        if self.busy:
            self.status = "Finishing command before exit"
        elif self.app.is_running:
            self.app.exit()

    def _bindings(self) -> KeyBindings:
        bindings = KeyBindings()

        @bindings.add("f1")
        def help_key(event: KeyPressEvent) -> None:
            self.show_help()

        @bindings.add("f2")
        def menu_key(event: KeyPressEvent) -> None:
            self.toggle_menu()

        @bindings.add("f3")
        def files_key(event: KeyPressEvent) -> None:
            self.toggle_files()

        @bindings.add("f5")
        def refresh_key(event: KeyPressEvent) -> None:
            if (self.show_context or self.panel_overlay) and self.app.layout.has_focus(
                self.panel_window()
            ):
                self.refresh_panels()
            else:
                self.refresh_files()

        @bindings.add("f4")
        def context_key(event: KeyPressEvent) -> None:
            self.toggle_panel("help")

        @bindings.add("f7")
        def outline_key(event: KeyPressEvent) -> None:
            self.toggle_panel("outline")

        @bindings.add("f8")
        def resources_key(event: KeyPressEvent) -> None:
            self.toggle_panel("resources")

        @bindings.add("f9")
        def server_key(event: KeyPressEvent) -> None:
            self.toggle_panel("server")

        @bindings.add("f6")
        @bindings.add("f18")
        def focus_key(event: KeyPressEvent) -> None:
            panes = [self.editor, self.results.window]
            if self.files_visible:
                panes.append(self.files.window)
            if self.show_context or self.panel_overlay:
                panes.append(self.panel_window())
            current = self.app.layout.current_window
            index = panes.index(current) if current in panes else 0
            step = -1 if event.key_sequence[0].key == "f18" else 1
            self.app.layout.focus(panes[(index + step) % len(panes)])

        @bindings.add("f10")
        def quit_key(event: KeyPressEvent) -> None:
            self.request_exit()

        @bindings.add("pageup", filter=has_focus(self.results.buffer))
        @bindings.add("pagedown", filter=has_focus(self.results.buffer))
        def page_results(event: KeyPressEvent) -> None:
            self.follow = False
            height = (
                self.results.window.render_info.window_height
                if self.results.window.render_info
                else 10
            )
            if event.key_sequence[0].key == "pageup":
                self.results.buffer.cursor_up(max(1, height - 1))
            else:
                self.results.buffer.cursor_down(max(1, height - 1))

        @bindings.add("c-end", filter=has_focus(self.results.buffer))
        def latest_results(event: KeyPressEvent) -> None:
            self.show_latest()

        @bindings.add("enter", filter=has_focus(self.results.buffer) & ~is_searching)
        @bindings.add("left", filter=has_focus(self.results.buffer) & ~is_searching)
        @bindings.add("right", filter=has_focus(self.results.buffer) & ~is_searching)
        def result_branch(event: KeyPressEvent) -> None:
            key = event.key_sequence[0].key
            direction = "enter" if key == "c-m" else key
            if self.result_trees.at(self.results.buffer.document.cursor_position_row) is not None:
                self.navigate_result_tree(direction)
            elif direction == "left":
                self.results.buffer.cursor_left()
            elif direction == "right":
                self.results.buffer.cursor_right()

        @bindings.add("o", filter=has_focus(self.results.buffer) & ~is_searching)
        def open_result_source(event: KeyPressEvent) -> None:
            found = self.result_trees.at(self.results.buffer.document.cursor_position_row)
            if found and found[0].entries[found[1]].source:
                self.open_source(cast(SourceTarget, found[0].entries[found[1]].source))

        @bindings.add("c", filter=has_focus(self.results.buffer) & ~is_searching)
        def cancel_result_batch(event: KeyPressEvent) -> None:
            found = self.result_trees.at(self.results.buffer.document.cursor_position_row)
            if found and found[0].kind == "batch_progress" and found[0].value.active:
                self.cancel_progress(found[0].value)

        @bindings.add(
            "c-d",
            filter=has_focus(self.buffer) & Condition(lambda: not self.buffer.text),
        )
        def eof_key(event: KeyPressEvent) -> None:
            self.request_exit()

        @bindings.add(
            "enter",
            filter=has_focus(self.buffer)
            & Condition(lambda: self.busy or self.closing),
            eager=True,
        )
        @bindings.add(
            "c-j",
            filter=has_focus(self.buffer)
            & Condition(lambda: self.busy or self.closing),
            eager=True,
        )
        def busy_enter(event: KeyPressEvent) -> None:
            self.write("A command is running; your next draft is kept.")

        @bindings.add("escape", filter=~is_searching, eager=True)
        def escape(event: KeyPressEvent) -> None:
            if self.buffer.complete_state is not None:
                self.buffer.cancel_completion()
            elif self.menu_visible:
                self.close_menu()
            elif (
                self.show_context or self.panel_overlay
            ) and self.app.layout.has_focus(self.panel_window()):
                self.close_panel()
            elif self.files_visible:
                self.files_visible = False
                self.app.layout.focus(self.editor)
            else:
                self.app.layout.focus(self.editor)

        @bindings.add("c-c")
        @bindings.add("<sigint>")
        def interrupt(event: KeyPressEvent) -> None:
            if self.busy:
                self.app.create_background_task(self._cancel())
            else:
                self.buffer.reset()
                self.status = "Draft cleared"
                self.app.layout.focus(self.editor)

        return bindings

    async def _cancel(self) -> None:
        if self.cancel is None:
            self.write(
                "Cancellation is unavailable for this operation; waiting for it to finish."
            )
            return
        self.status = "Cancellation requested"
        try:
            self.write(await self.cancel())
        except Exception as exc:  # noqa: BLE001 - cancellation callback boundary
            self.write(f"Cancellation was not confirmed: {exc}")

    async def run(self) -> int:
        self.loop = asyncio.get_running_loop()
        try:
            with (
                control_enter_keys(),
                redirect_stdout(cast(TextIO, self.stream)),
                redirect_stderr(cast(TextIO, self.stream)),
            ):
                if self.read_server_status is not None:
                    self.monitor_task = asyncio.create_task(self._monitor_server())
                await self.app.run_async()
                if self.command_task is not None:
                    await asyncio.shield(self.command_task)
                self.stream.flush()
        finally:
            await asyncio.gather(*self.source_tasks, return_exceptions=True)
            for task in tuple(self.batch_monitors.values()):
                task.cancel()
            await asyncio.gather(*self.batch_monitors.values(), return_exceptions=True)
            for task in tuple(self.result_tree_tasks):
                task.cancel()
            await asyncio.gather(*self.result_tree_tasks, return_exceptions=True)
            if self.monitor_task is not None:
                self.monitor_task.cancel()
                await asyncio.gather(self.monitor_task, return_exceptions=True)
            if (
                self.panel_refresh_task is not None
                and not self.panel_refresh_task.done()
            ):
                self.panel_refresh_task.cancel()
                await asyncio.gather(self.panel_refresh_task, return_exceptions=True)
            # The worker owns Runtime stacks; its join precedes Runtime.close().
            if self.command_task is not None and not self.command_task.done():
                await asyncio.shield(self.command_task)
            self.loop = None
        return self.exit_code
