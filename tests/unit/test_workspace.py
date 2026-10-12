"""Key-driven workspace behavior with the actual prompt_toolkit application."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Awaitable, Callable
from pathlib import Path
from unittest.mock import Mock

import pytest
from clang_toolkit.cli.app import DispatchResult, dispatch_result
from clang_toolkit.cli.file_explorer import MAX_DIRECTORY_ENTRIES, FileExplorer
from clang_toolkit.cli.prompt import PersistentPromptHistory, create_session
from clang_toolkit.cli.runtime import Runtime
from clang_toolkit.cli.runtime.history import HistoryStore
from clang_toolkit.cli.workspace import WorkspaceConsole
from clang_toolkit.cli.workspace_output import MAX_TRANSCRIPT_CHARS
from clang_toolkit.cli.workspace_transcript import TranscriptLexer, command_block
from clang_toolkit.client import Client
from prompt_toolkit.data_structures import Size
from prompt_toolkit.document import Document
from prompt_toolkit.input import PipeInput, create_pipe_input
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.output.color_depth import ColorDepth


class SizedOutput(DummyOutput):
    def __init__(self, rows: int = 24, columns: int = 100) -> None:
        self.size = Size(rows=rows, columns=columns)

    def get_size(self) -> Size:
        return self.size


async def wait_until(predicate: Callable[[], bool]) -> None:
    async with asyncio.timeout(3):
        while not predicate():
            await asyncio.sleep(0.005)


async def interact(
    root: Path,
    drive: Callable[[WorkspaceConsole, PipeInput], Awaitable[None]],
    *,
    output: SizedOutput | None = None,
    execute: Callable[[str], Awaitable[DispatchResult]] | None = None,
    history: PersistentPromptHistory | None = None,
) -> WorkspaceConsole:
    async def echo(source: str) -> DispatchResult:
        return DispatchResult("OK " + source, True)

    with create_pipe_input() as pipe:
        screen = output or SizedOutput()
        session = create_session(input=pipe, output=screen, history=history)
        workspace = WorkspaceConsole(
            session, root, execute or echo, input=pipe, output=screen
        )
        task = asyncio.create_task(workspace.run())
        try:
            await wait_until(lambda: workspace.app.is_running)
            await drive(workspace, pipe)
            pipe.send_text("\x1b[21~")  # F10
            await asyncio.wait_for(task, 3)
        finally:
            if not task.done():
                workspace.request_exit()
                await asyncio.wait_for(task, 3)
        return workspace


def test_menu_and_files_preserve_draft_and_cursor(tmp_path: Path) -> None:
    (tmp_path / "sample.cpp").write_text("int sample();")

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        pipe.send_text('print "draft"\x1b[D')
        await wait_until(lambda: ui.buffer.text == 'print "draft"')
        cursor = ui.buffer.cursor_position
        pipe.send_text("\x1bOQ")  # F2
        await wait_until(lambda: ui.app.layout.has_focus(ui.menu.window))
        pipe.send_text("\r")  # Actions > Browse local files
        await wait_until(lambda: ui.files_visible and bool(ui.files.entries))
        assert ui.app.layout.has_focus(ui.files.window)
        pipe.send_text("\x1bOR")  # F3 closes files
        await wait_until(lambda: not ui.files_visible)
        assert ui.app.layout.has_focus(ui.editor)
        assert ui.buffer.text == 'print "draft"'
        assert ui.buffer.cursor_position == cursor

    asyncio.run(interact(tmp_path, drive))


def test_multiline_expands_and_submits_as_one_command(tmp_path: Path) -> None:
    seen: list[str] = []

    async def execute(source: str) -> DispatchResult:
        seen.append(source)
        return DispatchResult("submitted", True)

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        pipe.send_text("let inputs = [\r1,\r2")
        await wait_until(lambda: ui.buffer.document.line_count == 4)
        await wait_until(
            lambda: (
                ui.editor.render_info is not None
                and ui.editor.render_info.window_height == 4
            )
        )
        assert not seen
        assert ui.editor_height() == 4
        pipe.send_text("\r]\x1b[27;5;13~")
        await wait_until(lambda: "submitted" in ui.results.text)
        assert ui.buffer.text == ""
        assert ui.editor_height() == 1

    asyncio.run(interact(tmp_path, drive, execute=execute))
    assert seen == ["let inputs = [\n    1,\n    2\n]"]


def test_assigned_batch_progress_reaches_workspace_before_command_finishes(tmp_path, monkeypatch):
    from test_console_file_batch_runtime import _runtime
    from clang_toolkit.cli.runtime import batch_execution
    from clang_toolkit.resources import FileSet, InputDescriptor

    runtime, _ = _runtime(tmp_path)
    runtime.bindings["inputs"] = FileSet((InputDescriptor.from_path("a.cc", working_directory=tmp_path),))
    monkeypatch.setattr(batch_execution, "_PROGRESS_INTERVAL_SECONDS", 0.01)
    release = threading.Event()
    original = runtime._evaluate_statement_once

    def blocked(statement, source, *, value_context):
        if str(statement.data) == "display":
            assert release.wait(2)
        return original(statement, source, value_context=value_context)

    monkeypatch.setattr(runtime, "_evaluate_statement_once", blocked)

    async def execute(source):
        return await asyncio.to_thread(dispatch_result, runtime.client, source, runtime)

    async def drive(ui, pipe):
        try:
            pipe.send_text("let run = batch part in $inputs size 1 do { $part.index; }\x1b[27;5;13~")
            await wait_until(lambda: "running: 0/1 completed" in ui.results.text)
            assert ui.busy and not ui.command_task.done()
            release.set()
            await wait_until(lambda: not ui.busy)
            assert runtime.bindings["run"]["status"] == "completed"
        finally:
            release.set()

    try:
        asyncio.run(interact(tmp_path, drive, execute=execute))
    finally:
        runtime.close()


@pytest.mark.parametrize("columns", [48, 100])
def test_long_draft_scrolls_and_resize_keeps_cursor_visible(
    tmp_path: Path, columns: int
) -> None:
    output = SizedOutput(rows=20, columns=columns)

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        draft = "let inputs = [\n" + ",\n".join(str(i) for i in range(40))
        pipe.send_text("\x1b[200~" + draft + "\x1b[201~")
        await wait_until(lambda: ui.buffer.text == draft)
        await wait_until(
            lambda: (
                ui.editor.render_info is not None
                and ui.editor.render_info.window_height == 8
            )
        )
        assert ui.editor_height() == 8
        assert ui.editor.vertical_scroll > 0
        output.size = Size(rows=14, columns=columns)
        ui.app.invalidate()
        await wait_until(lambda: ui.editor.render_info.window_height == 5)
        assert ui.buffer.cursor_position == len(draft)
        assert ui.buffer.text == draft

    asyncio.run(interact(tmp_path, drive, output=output))


def test_wrapped_unicode_line_grows_the_editor(tmp_path: Path) -> None:
    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        text = 'print "' + "界" * 65 + '"'
        pipe.send_text(text)
        await wait_until(lambda: ui.buffer.text == text)
        assert ui.buffer.document.line_count == 1
        assert ui.editor_height() > 1

    asyncio.run(interact(tmp_path, drive, output=SizedOutput(columns=50)))


def test_explorer_lazily_opens_folder_and_prepares_escaped_path(tmp_path: Path) -> None:
    folder = tmp_path / "src"
    folder.mkdir()
    source = folder / 'a"b.cpp'
    source.write_text("int a();")
    seen: list[str] = []

    async def execute(text: str) -> DispatchResult:
        seen.append(text)
        return DispatchResult("parsed", True)

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        pipe.send_text("\x1bOR")
        await wait_until(lambda: bool(ui.files.entries))
        assert folder not in ui.files.children
        pipe.send_text("\r")
        await wait_until(lambda: len(ui.files.entries) == 2)
        pipe.send_text("\x1b[B\r")
        await wait_until(lambda: ui.buffer.text.startswith("parse "))
        assert ui.app.layout.has_focus(ui.editor)
        assert '\\"' in ui.buffer.text
        assert not seen

    asyncio.run(interact(tmp_path, drive, execute=execute))


def test_narrow_explorer_is_closable_without_hiding_the_editor(tmp_path: Path) -> None:
    (tmp_path / "sample.cpp").write_text("int sample();")

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        pipe.send_text("\x1bOR")
        await wait_until(lambda: bool(ui.files.entries))
        assert ui.narrow
        pipe.send_text("\r")
        await wait_until(lambda: ui.buffer.text.startswith("parse "))
        assert not ui.files_visible
        assert ui.app.layout.has_focus(ui.editor)

    asyncio.run(interact(tmp_path, drive, output=SizedOutput(columns=48)))


def test_busy_command_keeps_next_draft_and_exit_joins_worker(tmp_path: Path) -> None:
    release = asyncio.Event()
    seen: list[str] = []

    async def execute(source: str) -> DispatchResult:
        seen.append(source)
        await release.wait()
        print("worker progress")
        return DispatchResult("finished", True)

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        pipe.send_text('print "first"\x1b[27;5;13~')
        await wait_until(lambda: ui.busy)
        assert "Running" in ui.footer()
        pipe.send_text('print "')
        await wait_until(lambda: ui.buffer.text == 'print ""')
        assert ui.buffer.document.text_after_cursor == '"'
        pipe.send_text('next"\x1b[27;5;13~')
        await wait_until(lambda: ui.buffer.text == 'print "next"')
        assert seen == ['print "first"']
        assert ui.buffer.text == 'print "next"'
        ui.request_exit()
        assert ui.app.is_running
        release.set()

    ui = asyncio.run(interact(tmp_path, drive, execute=execute))
    assert "worker progress" in ui.results.text
    assert "finished" in ui.results.text
    assert ui.command_task is not None and ui.command_task.done()


def test_runtime_history_is_written_once_and_reverse_search_works(
    tmp_path: Path,
) -> None:
    store = HistoryStore(tmp_path / "history.jsonl")
    runtime = Runtime(Mock(spec=Client), cwd=tmp_path, environment={}, history=store)
    source = 'print "history distinctive"'

    async def execute(text: str) -> DispatchResult:
        return await asyncio.to_thread(dispatch_result, runtime.client, text, runtime)

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        pipe.send_text(source + "\x1b[27;5;13~")
        await wait_until(
            lambda: "Ready" == ui.status and not ui.busy and bool(store.read_commands())
        )
        pipe.send_text("\x12distinctive")
        await wait_until(lambda: ui.app.layout.has_focus(ui.search.control))
        pipe.send_text("\x1bOQ")
        await wait_until(lambda: ui.menu_visible)
        pipe.send_text("\x1bOQ")
        await wait_until(lambda: not ui.menu_visible)
        assert ui.app.layout.has_focus(ui.search.control)
        pipe.send_text("\r")
        await wait_until(lambda: ui.buffer.text == source)
        assert store.read_commands() == [source]

    try:
        asyncio.run(
            interact(
                tmp_path, drive, execute=execute, history=PersistentPromptHistory(store)
            )
        )
    finally:
        runtime.close()
    assert store.read_commands() == [source]


def test_transcript_is_bounded_and_failure_is_visible(tmp_path: Path) -> None:
    async def execute(source: str) -> DispatchResult:
        return DispatchResult("failure detail", False)

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        ui.write("x" * (MAX_TRANSCRIPT_CHARS + 10))
        await wait_until(lambda: "trimmed" in ui.results.text)
        assert len(ui.results.text) <= MAX_TRANSCRIPT_CHARS
        pipe.send_text('print "failed"\x1b[27;5;13~')
        await wait_until(lambda: "Command failed" == ui.status)
        assert "Command failed" in ui.footer()

    ui = asyncio.run(interact(tmp_path, drive, execute=execute))
    assert ui.exit_code == 1
    assert "failure detail" in ui.results.text


def test_directory_listing_is_bounded_and_does_not_follow_symlink(
    tmp_path: Path,
) -> None:
    for i in range(MAX_DIRECTORY_ENTRIES + 5):
        (tmp_path / f"file-{i}.cpp").touch()
    folder = tmp_path / "folder"
    folder.mkdir()
    (folder / "loop").symlink_to(tmp_path, target_is_directory=True)
    explorer = FileExplorer(tmp_path, lambda: None)
    children, truncated = explorer.scan(tmp_path)
    assert truncated
    assert len(children) <= MAX_DIRECTORY_ENTRIES
    links, _ = explorer.scan(folder)
    assert not links[0].directory


def test_actions_menu_mouse_and_page_scrolling_keep_draft(tmp_path: Path) -> None:
    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        pipe.send_text('print "kept"')
        await wait_until(lambda: ui.buffer.text == 'print "kept"')
        # Click the single toolbar button through the real terminal mouse parser.
        column = len(" CTK console | ") + 2
        pipe.send_text(f"\x1b[<0;{column};1M\x1b[<0;{column};1m")
        await wait_until(lambda: ui.menu_visible)
        await wait_until(lambda: ui.menu.window.render_info is not None)
        pipe.send_text("\x1b[<65;10;4M")
        await wait_until(lambda: ui.menu.selected == 3)
        pipe.send_text("\x1b[6~")  # Page down in the action list.
        await wait_until(lambda: ui.menu.selected == 8)
        await wait_until(lambda: ui.menu.window.vertical_scroll > 0)
        pipe.send_text("\x1b[H\x1b[B\x1b[B\x1b[B\r")
        await wait_until(lambda: not ui.menu_visible)
        assert not ui.follow
        assert ui.buffer.text == 'print "kept"'
        assert sum("local files" in action.label() for action in ui.menu.actions) == 1

    asyncio.run(interact(tmp_path, drive, output=SizedOutput(rows=12)))


def test_mouse_selects_files_and_wheel_scrolls_listing(tmp_path: Path) -> None:
    for index in range(40):
        (tmp_path / f"file-{index:02}.cpp").touch()

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        pipe.send_text("\x1bOR")
        await wait_until(lambda: bool(ui.files.entries))
        await wait_until(
            lambda: (
                ui.files.window.render_info is not None
                and ui.files.window.render_info.content_height == 40
            )
        )
        # Root label is row 3; the first file occupies row 4.
        pipe.send_text("\x1b[<0;8;7M\x1b[<0;8;7m")
        await wait_until(lambda: ui.files.selected == 3)
        assert ui.buffer.text == ""
        pipe.send_text("\x1b[<0;8;7M\x1b[<0;8;7m")
        await wait_until(lambda: ui.buffer.text.startswith("parse "))
        assert "file-03.cpp" in ui.buffer.text
        pipe.send_text("\x1b[<65;8;7M\x1b[6~")
        await wait_until(lambda: ui.files.selected > 10)
        await wait_until(lambda: ui.files.window.vertical_scroll > 0)

    asyncio.run(interact(tmp_path, drive, output=SizedOutput(rows=16)))


def test_results_mouse_and_keyboard_pause_following(tmp_path: Path) -> None:
    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        ui.write("\n".join(f"result {i}" for i in range(80)))
        await wait_until(lambda: "result 79" in ui.results.text)
        pipe.send_text("\x1b[<64;20;5M")
        await wait_until(lambda: not ui.follow)
        assert ui.app.layout.has_focus(ui.results.window)
        position = ui.results.buffer.cursor_position
        pipe.send_text("\x1b[5~")
        await wait_until(lambda: ui.results.buffer.cursor_position < position)
        paused = ui.results.buffer.cursor_position
        ui.write("new result")
        await wait_until(lambda: "new result" in ui.results.text)
        assert ui.results.buffer.cursor_position == paused
        pipe.send_text("\x1b[1;5F")  # Ctrl+End resumes following.
        await wait_until(lambda: ui.follow)

    asyncio.run(interact(tmp_path, drive))


def test_wide_command_context_reflows_editor(tmp_path: Path) -> None:
    output = SizedOutput(columns=140)

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        pipe.send_text('let tree = parse "sample.cpp"')
        await wait_until(lambda: "parse PATH" in ui.context.text)
        assert ui.show_context
        assert ui.editor.render_info.window_width == 103
        output.size = Size(rows=24, columns=90)
        ui.app.invalidate()
        await wait_until(lambda: ui.editor.render_info.window_width == 89)
        assert not ui.show_context
        assert ui.buffer.text == 'let tree = parse "sample.cpp"'

    asyncio.run(interact(tmp_path, drive, output=output))


def test_transcript_preserves_indented_colored_blocks_without_markers() -> None:
    source = "let x = functionDecl(\n    isImplicit()\n)"
    text = command_block(source) + "\nerror: failed"
    lexer = TranscriptLexer().lex_document(Document(text))
    assert "".join(fragment for _, fragment in lexer(1)) == "  2 │     isImplicit()"
    assert any("class:matcher" in style for style, _ in lexer(1))
    assert any("class:keyword" in style for style, _ in lexer(0))
    assert lexer(4)[0][0] == "class:diagnostic"
    assert "CTK command" not in text and "╭" not in text
    assert "...>" not in text and "ctk>" not in text and "```" not in text


@pytest.mark.parametrize("hide", [False, True])
def test_menu_restores_only_a_live_visible_panel(tmp_path: Path, hide: bool) -> None:
    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        pipe.send_text('print "kept"')
        await wait_until(lambda: ui.buffer.text == 'print "kept"')
        ui.toggle_panel("help")  # Close initially visible help.
        ui.toggle_panel("help")  # Open and focus help.
        original = ui.panel_window()
        pipe.send_text("\x1bOQ")
        await wait_until(lambda: ui.menu_visible)
        assert ui.previous_focus is original
        if hide:
            ui.close_panel()
        else:
            ui.toggle_panel("outline")
        # Closing Actions used to restore the replaced help Window and crash.
        pipe.send_text("\x1bOQ")
        await wait_until(lambda: not ui.menu_visible)
        assert ui.app.layout.has_focus(ui.editor if hide else ui.outline.window)
        pipe.send_text("\x1bOQ\x1b[H\r")
        await wait_until(lambda: ui.files_visible)
        assert ui.app.layout.has_focus(ui.files.window)
        assert ui.buffer.text == 'print "kept"'
        assert ui.toolbar()[0][1] == " CTK console | "
        assert ui.editor.get_line_prefix(1, 0)[0][1] == "   2 │ "

    asyncio.run(interact(tmp_path, drive, output=SizedOutput(columns=150)))


def test_workspace_explicitly_enables_color_and_mouse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("NO_COLOR", "1")
    with create_pipe_input() as pipe:
        ui = WorkspaceConsole(
            create_session(input=pipe, output=SizedOutput()),
            tmp_path,
            Mock(),
            input=pipe,
            output=SizedOutput(),
        )
        assert ui.app.color_depth == ColorDepth.DEPTH_8_BIT
        assert ui.app.mouse_support()
