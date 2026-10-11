"""Smart typing with grammar context and actual workspace keyboard bindings."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.input import PipeInput

from clang_toolkit.cli.workspace import WorkspaceConsole
from clang_toolkit.cli.app import DispatchResult
from clang_toolkit.cli.workspace_editing import insert_pair, smart_newline
from test_workspace import interact, wait_until


@pytest.mark.parametrize("sequence", ["\x1b[27;5;13~", "\x1b[13;5u", "\n"])
@pytest.mark.parametrize("source", ['print "single"', "let values = [\n    1,\n    2\n]"])
def test_control_enter_runs_whole_draft_from_middle(
    tmp_path: Path, sequence: str, source: str,
) -> None:
    seen: list[str] = []

    async def execute(text: str) -> DispatchResult:
        seen.append(text)
        return DispatchResult("executed", True)

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        ui.buffer.document = Document(source, 5)
        pipe.send_text(sequence)
        await wait_until(lambda: not ui.busy and "executed" in ui.results.text)
        assert ui.buffer.text == ""

    asyncio.run(interact(tmp_path, drive, execute=execute))
    assert seen == [source]


def test_enter_keeps_complete_draft_for_multiline_editing(tmp_path: Path) -> None:
    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        ui.buffer.document = Document('    print "first"', 17)
        pipe.send_text("\r")
        await wait_until(lambda: ui.buffer.text.endswith("\n    "))
        assert ui.buffer.text == '    print "first"\n    '
        assert not ui.busy and "OK" not in ui.results.text

    asyncio.run(interact(tmp_path, drive))


def test_control_enter_mapping_restores_plain_prompt_keys(tmp_path: Path) -> None:
    from prompt_toolkit.input.ansi_escape_sequences import ANSI_SEQUENCES

    before = dict(ANSI_SEQUENCES)

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        pipe.send_text("print 7\x1b[13;5u")
        await wait_until(lambda: "OK print 7" in ui.results.text)

    asyncio.run(interact(tmp_path, drive))
    assert ANSI_SEQUENCES == before


@pytest.mark.parametrize(
    "opener,closer", [("(", ")"), ("[", "]"), ("{", "}"), ('"', '"'), ("'", "'")]
)
def test_pairs_keep_cursor_inside_and_skip_the_existing_closer(
    opener: str, closer: str
) -> None:
    buffer = Buffer(document=Document("print ", 6))
    insert_pair(buffer, opener)
    assert buffer.text == "print " + opener + closer
    assert buffer.cursor_position == 7
    insert_pair(buffer, closer)
    assert buffer.text == "print " + opener + closer
    assert buffer.cursor_position == 8


@pytest.mark.parametrize(
    "source,char,expected",
    [
        ('print "text', "(", 'print "text('),
        ('print "text\\', '"', 'print "text\\"'),
        ('print "text', "'", "print \"text'"),
        ("# comment", '"', '# comment"'),
        ("# comment", "[", "# comment["),
    ],
)
def test_literals_comments_and_escapes_are_not_paired(
    source: str, char: str, expected: str
) -> None:
    buffer = Buffer(document=Document(source, len(source)))
    insert_pair(buffer, char)
    assert buffer.text == expected
    assert buffer.cursor_position == len(expected)


def test_nested_indentation_and_closing_on_an_empty_line() -> None:
    buffer = Buffer(document=Document("let x = functionDecl()", 21))
    smart_newline(buffer)
    assert buffer.text == "let x = functionDecl(\n    \n)"
    assert buffer.document.current_line_before_cursor == "    "
    for char in "unless":
        buffer.insert_text(char)
    insert_pair(buffer, "(")
    smart_newline(buffer)
    assert buffer.document.current_line_before_cursor == "        "
    buffer.insert_text("isImplicit")
    insert_pair(buffer, "(")
    insert_pair(buffer, ")")
    smart_newline(buffer)
    insert_pair(buffer, ")")
    smart_newline(buffer)
    insert_pair(buffer, ")")
    assert (
        buffer.text
        == "let x = functionDecl(\n    unless(\n        isImplicit()\n    )\n)"
    )
    assert buffer.cursor_position == len(buffer.text)


def test_unclosed_pasted_bracket_gets_an_indented_newline_and_dedented_closer() -> None:
    source = "let x = [\n    1,"
    buffer = Buffer(document=Document(source, len(source)))
    smart_newline(buffer)
    assert buffer.document.current_line_before_cursor == "    "
    insert_pair(buffer, "]")
    assert buffer.text == source + "\n]"


def test_paired_typing_deletion_paste_and_submission_in_the_workspace(
    tmp_path: Path,
) -> None:
    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        pipe.send_text("let x = [")
        await wait_until(lambda: ui.buffer.text == "let x = []")
        assert ui.buffer.document.text_after_cursor == "]"
        pipe.send_text("\x7f")
        await wait_until(lambda: ui.buffer.text == "let x = ")
        pipe.send_text("[\r1,\r2\r]\x1b[27;5;13~")
        await wait_until(
            lambda: "Ready" == ui.status and not ui.busy and not ui.buffer.text
        )
        assert "  2 │     1," in ui.results.text
        assert "  3 │     2" in ui.results.text
        paste = 'print "unclosed ('
        pipe.send_text("\x1b[200~" + paste + "\x1b[201~")
        await wait_until(lambda: ui.buffer.text == paste)
        assert ui.buffer.cursor_position == len(paste)
        pipe.send_text('\x03print "hello"\x1b[27;5;13~')
        await wait_until(lambda: 'OK print "hello"' in ui.results.text)
        assert not ui.buffer.text

    asyncio.run(interact(tmp_path, drive))


def test_blank_lines_keep_the_existing_indent() -> None:
    buffer = Buffer(document=Document("let x = []", 9))
    smart_newline(buffer)
    smart_newline(buffer)
    assert buffer.text == "let x = [\n    \n    \n]"
    assert buffer.document.current_line_before_cursor == "    "


def test_inserting_a_pair_is_one_undo_step(tmp_path: Path) -> None:
    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        ui.buffer.document = Document("let x = ", 8)
        pipe.send_text("(")
        await wait_until(lambda: ui.buffer.text == "let x = ()")
        pipe.send_text("\x1f")
        await wait_until(lambda: ui.buffer.text == "let x = ")
        assert ui.buffer.cursor_position == 8

    asyncio.run(interact(tmp_path, drive))


@pytest.mark.parametrize("suffix", ["\n    )\n)", "))"])
@pytest.mark.parametrize("method", ["tab", "select", "apply", "mouse"])
def test_completing_a_nested_matcher_inserts_its_own_closer(
    tmp_path: Path, method: str, suffix: str
) -> None:
    from prompt_toolkit.completion import Completion
    from prompt_toolkit.application.current import set_app
    from prompt_toolkit.layout.menus import CompletionsMenuControl
    from prompt_toolkit.mouse_events import MouseButton, MouseEvent, MouseEventType
    from prompt_toolkit.data_structures import Point

    prefix = "let x = functionDecl(\n    unless(\n        isImp"

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        ui.buffer.document = Document(prefix + suffix, len(prefix))
        if method == "tab":
            pipe.send_text("\t")
        elif method == "apply":
            ui.buffer.apply_completion(Completion("isImplicit(", start_position=-5))
        else:
            ui.buffer.start_completion()
            await wait_until(
                lambda: ui.buffer.complete_state is not None
                and bool(ui.buffer.complete_state.completions)
            )
            state = ui.buffer.complete_state
            index = next(
                i
                for i, item in enumerate(state.completions)
                if item.text == "isImplicit("
            )
            if method == "select":
                ui.buffer.go_to_completion(index)
            else:
                with set_app(ui.app):
                    CompletionsMenuControl().mouse_handler(
                        MouseEvent(
                            Point(0, index),
                            MouseEventType.MOUSE_UP,
                            MouseButton.LEFT,
                            frozenset(),
                        )
                    )
        expected = prefix[:-5] + "isImplicit()" + suffix
        await wait_until(lambda: ui.buffer.text == expected)
        assert ui.buffer.document.text_after_cursor == ")" + suffix
        pipe.send_text(")")
        await wait_until(lambda: ui.buffer.document.text_after_cursor == suffix)
        assert ui.buffer.text == expected

    asyncio.run(interact(tmp_path, drive))


@pytest.mark.parametrize("opener,closer", [("(", ")"), ('"', '"'), ("'", "'")])
def test_typed_pairs_in_the_middle_of_a_nested_multiline_draft(
    tmp_path: Path, opener: str, closer: str
) -> None:
    prefix = "let x = functionDecl(\n    unless(\n        hasName"
    suffix = "\n    )\n)"

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        ui.buffer.document = Document(prefix + suffix, len(prefix))
        pipe.send_text(opener)
        await wait_until(lambda: ui.buffer.text == prefix + opener + closer + suffix)
        assert ui.buffer.document.text_after_cursor == closer + suffix
        assert ui.buffer.cursor_position == len(prefix) + 1

    asyncio.run(interact(tmp_path, drive))


def test_completion_cycling_and_cancellation_keep_outer_closers(tmp_path: Path) -> None:
    prefix = "let x = functionDecl(\n    unless(\n        isExp"
    suffix = "\n    )\n)"
    source = prefix + suffix

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        ui.buffer.document = Document(source, len(prefix))
        ui.buffer.start_completion()
        await wait_until(
            lambda: ui.buffer.complete_state is not None
            and len(ui.buffer.complete_state.completions) > 1
        )
        state = ui.buffer.complete_state
        for index in range(len(state.completions)):
            choice = state.completions[index]
            ui.buffer.go_to_completion(index)
            assert ui.buffer.text == prefix[:-5] + choice.text + ")" + suffix
            assert ui.buffer.document.text_after_cursor == ")" + suffix
        pipe.send_text("\x1b")
        await wait_until(lambda: ui.buffer.complete_state is None)
        assert ui.buffer.text == source
        assert ui.buffer.cursor_position == len(prefix)

    asyncio.run(interact(tmp_path, drive))


def test_paste_is_not_paired_even_when_it_matches_a_completion(tmp_path: Path) -> None:
    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        ui.buffer.document = Document("let x = functionDecl(isImp", 26)
        ui.buffer.start_completion()
        await wait_until(
            lambda: ui.buffer.complete_state is not None
            and bool(ui.buffer.complete_state.completions)
        )
        pipe.send_text("\x1b[200~licit(\x1b[201~")
        await wait_until(lambda: ui.buffer.text == "let x = functionDecl(isImplicit(")
        assert not ui.buffer.document.text_after_cursor

    asyncio.run(interact(tmp_path, drive))


def test_tab_completion_and_its_closer_are_one_undo_step(tmp_path: Path) -> None:
    prefix = "let x = functionDecl(isImp"
    suffix = ")"

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        ui.buffer.document = Document(prefix + suffix, len(prefix))
        pipe.send_text("\t")
        await wait_until(lambda: ui.buffer.text == "let x = functionDecl(isImplicit())")
        pipe.send_text("\x1f")
        await wait_until(lambda: ui.buffer.text == prefix + suffix)
        assert ui.buffer.cursor_position == len(prefix)

    asyncio.run(interact(tmp_path, drive))
