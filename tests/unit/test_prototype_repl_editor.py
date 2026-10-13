"""Compiled-prototype prompt and workspace editing behavior."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from prompt_toolkit.document import Document
from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.input import PipeInput, create_pipe_input
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.validation import ValidationError

from clang_toolkit.cli.app import DispatchResult
from clang_toolkit.cli.prompt import create_session
from clang_toolkit.cli.runtime.prototype.repl_editor import (
    PrototypeCompleter,
    PrototypeInputValidator,
    PrototypeReplLexer,
    input_state,
    lex,
)
from clang_toolkit.cli.workspace import WorkspaceConsole


def _kind(token) -> str:
    return token.type.removeprefix("LEGACY_").removeprefix("PROTO_")


@pytest.mark.parametrize(
    "source",
    [
        "let total = (1 +\n2)",
        "if true do\n    print 1\nelse\n    print 2",
        "if true {\n    print 1\n} else {\n    print 2\n}",
        'let text = "(not a delimiter)" # } ignored in comment',
    ],
)
def test_compiled_editor_lexer_preserves_valid_tokens_without_false_errors(
    source: str,
) -> None:
    tokens = lex(source)
    assert "".join(str(token) for token in tokens) == source
    assert "ERROR" not in {_kind(token) for token in tokens}
    assert not input_state(source).needs_more


@pytest.mark.parametrize(
    "source",
    ["let total = 1 +", "if true do", "if true do 1 else", "let xs = [1, 2"],
)
def test_operator_condition_and_delimiter_prefixes_request_more_input(
    source: str,
) -> None:
    assert input_state(source).needs_more


def test_complete_unbraced_conditional_does_not_require_a_done_token() -> None:
    assert not input_state("if true do print 1").needs_more


def test_mismatched_delimiter_is_an_error_instead_of_a_continuation() -> None:
    state = input_state("let xs = [1, 2)")
    assert state.error_at == len("let xs = [1, 2")
    assert not state.needs_more


def test_validator_reports_syntax_error_without_changing_the_source() -> None:
    source = "let total = 1 @ 2"
    document = Document(source)
    with pytest.raises(ValidationError, match="syntax error"):
        PrototypeInputValidator().validate(document)
    assert document.text == source


def test_compiled_prompt_uses_the_prototype_lexer_and_validator() -> None:
    session = create_session(output=DummyOutput(), script_engine="compiled")
    assert isinstance(session.lexer, PrototypeReplLexer)
    assert callable(session.input_state_fn)
    assert session.input_state_fn("if true do").needs_more


async def _wait_until(predicate) -> None:
    async with asyncio.timeout(3):
        while not predicate():
            await asyncio.sleep(0.005)


async def _interact_compiled(
    root: Path,
    drive,
    execute,
) -> WorkspaceConsole:
    with create_pipe_input() as pipe:
        screen = DummyOutput()
        session = create_session(input=pipe, output=screen, script_engine="compiled")
        workspace = WorkspaceConsole(session, root, execute, input=pipe, output=screen)
        task = asyncio.create_task(workspace.run())
        try:
            await _wait_until(lambda: workspace.app.is_running)
            await drive(workspace, pipe)
            pipe.send_text("\x1b[21~")
            await asyncio.wait_for(task, 3)
        finally:
            if not task.done():
                workspace.request_exit()
                await asyncio.wait_for(task, 3)
        return workspace


def test_workspace_enter_uses_active_compiled_completeness_and_keeps_bad_source(
    tmp_path: Path,
) -> None:
    submitted: list[str] = []

    async def execute(source: str) -> DispatchResult:
        submitted.append(source)
        return DispatchResult("submitted", True)

    async def drive(ui: WorkspaceConsole, pipe: PipeInput) -> None:
        source = "let total = 1 +"
        ui.buffer.document = Document(source, len(source))
        pipe.send_text("\r")
        await _wait_until(lambda: ui.buffer.document.line_count == 2)
        assert not submitted

        complete = source + "\n2"
        ui.buffer.document = Document(complete, len(complete))
        pipe.send_text("\x1b[27;5;13~")
        await _wait_until(lambda: submitted == [complete])

        invalid = "let total = 1 @ 2"
        ui.buffer.document = Document(invalid, len(invalid))
        pipe.send_text("\x1b[27;5;13~")
        await _wait_until(lambda: ui.buffer.validation_error is not None)
        assert ui.buffer.text == invalid
        assert submitted == [complete]

    asyncio.run(_interact_compiled(tmp_path, drive, execute))


def test_then_is_valid_highlighted_and_completed_for_conditionals():
    source = "let value = if true then 2 else 1"
    tokens = lex(source)
    assert "ERROR" not in {_kind(token) for token in tokens}
    assert not input_state(source).needs_more
    lexer = PrototypeReplLexer()
    then_parts = lexer.lex_document(Document(source))(0)
    assert ("class:keyword", "then") in then_parts

    base = create_session(output=DummyOutput()).completer
    completions = list(PrototypeCompleter(base).get_completions(Document("the"), CompleteEvent()))
    assert any(item.text == "then" for item in completions)


def test_predicate_syntax_is_lexed_highlighted_and_completed():
    source = '$row does not have "name" and 2 not in $items and $node is CXXRecord'
    tokens = lex(source)
    assert "ERROR" not in {_kind(token) for token in tokens}
    assert not input_state(source).needs_more
    parts = PrototypeReplLexer().lex_document(Document(source))(0)
    highlighted = {text for style, text in parts if style == "class:keyword"}
    assert {"does", "not", "have", "and", "in", "is"} <= highlighted

    base = create_session(output=DummyOutput()).completer
    completions = list(PrototypeCompleter(base).get_completions(Document("doe"), CompleteEvent()))
    assert any(item.text == "does" for item in completions)


@pytest.mark.parametrize("source", ['$row has "a"', "$row has 'a'"])
def test_quoted_predicate_keys_keep_string_highlighting(source: str):
    tokens = lex(source)
    assert "ERROR" not in {_kind(token) for token in tokens}
    parts = PrototypeReplLexer().lex_document(Document(source))(0)
    assert ("class:string", source[source.index("has") + 4 :]) in parts
