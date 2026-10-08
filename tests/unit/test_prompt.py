from __future__ import annotations

import asyncio

import pytest
from prompt_toolkit.document import Document
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.validation import ValidationError

from clang_toolkit.cli.prompt import InputValidator, create_session


@pytest.mark.parametrize(
    ("text", "expected", "position"),
    [
        ("match functionDecl([)]", "expected `]`", len("match functionDecl([")),
        ("match functionDecl(]", "expected `)`", len("match functionDecl(")),
        ("match functionDecl())", "unexpected `)`", len("match functionDecl()")),
        ("match functionDecl(@)", "unexpected character", len("match functionDecl(")),
    ],
)
def test_invalid_delimiters_are_reported_with_syntax_details(text, expected, position):
    with pytest.raises(ValidationError) as raised:
        InputValidator().validate(Document(text))

    assert expected.lower() in raised.value.message.lower()
    assert "syntax error at line 1, column" in raised.value.message
    assert raised.value.cursor_position == position
    assert "\n" not in raised.value.message


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("match functionDecl(", "expected `)`"),
        ('match functionDecl(hasName("open', "unterminated quoted string"),
        ('match functionDecl() in ["file.cc"', "expected `]`"),
        ('in parse "file.cc" {', "expected `}`"),
        ('foreach $x in $items do\n"${x}"', "expected `done`"),
    ],
)
def test_forced_submission_cannot_bypass_incomplete_input(text, expected):
    with pytest.raises(ValidationError) as raised:
        InputValidator().validate(Document(text))

    assert expected in raised.value.message
    assert "syntax error at line" in raised.value.message
    assert raised.value.cursor_position == len(text)


def test_enter_continues_then_submits_balanced_matcher():
    async def run():
        with create_pipe_input() as pipe:
            session = create_session(input=pipe, output=DummyOutput())
            task = asyncio.create_task(session.prompt_async("ctk> "))
            pipe.send_text('match functionDecl(\rhasName("a[()]")\r')
            # Synchronize with the actual input buffer instead of sleep timing.
            for _ in range(100):
                if session.default_buffer.text.endswith("\n"):
                    break
                await asyncio.sleep(0.01)
            assert not task.done()
            assert (
                session.default_buffer.text == 'match functionDecl(\nhasName("a[()]")\n'
            )
            pipe.send_text(")\r")
            return await asyncio.wait_for(task, 2)

    assert asyncio.run(run()) == 'match functionDecl(\nhasName("a[()]")\n)'


def test_balanced_single_line_submits_on_enter():
    async def run():
        with create_pipe_input() as pipe:
            session = create_session(input=pipe, output=DummyOutput())
            pipe.send_text('match hasName("[({")\r')
            return await asyncio.wait_for(session.prompt_async("ctk> "), 2)

    assert asyncio.run(run()) == 'match hasName("[({")'


def test_bracketed_paste_preserves_multiline_command():
    text = 'match functionDecl(\n    hasName("f")\n)'

    async def run():
        with create_pipe_input() as pipe:
            session = create_session(input=pipe, output=DummyOutput())
            pipe.send_text("\x1b[200~" + text + "\x1b[201~\r")
            return await asyncio.wait_for(session.prompt_async("ctk> "), 2)

    assert asyncio.run(run()) == text


@pytest.mark.parametrize("opening,closing", [("(", ")"), ("[", "]"), ("{", "}")])
def test_each_delimiter_activates_continuation(opening, closing):
    async def run():
        with create_pipe_input() as pipe:
            session = create_session(input=pipe, output=DummyOutput())
            pipe.send_text(opening + "\r" + closing + "\r")
            return await asyncio.wait_for(session.prompt_async("ctk> "), 2)

    assert asyncio.run(run()) == opening + "\n" + closing


def test_mismatched_closer_can_be_corrected_before_submit():
    async def run():
        with create_pipe_input() as pipe:
            session = create_session(input=pipe, output=DummyOutput())
            task = asyncio.create_task(session.prompt_async("ctk> "))
            pipe.send_text("match foo(]\r")
            for _ in range(100):
                if session.default_buffer.validation_error:
                    break
                await asyncio.sleep(0.01)
            assert session.default_buffer.validation_error is not None
            assert not task.done()
            pipe.send_text("\x05\x7f)\r")
            return await asyncio.wait_for(task, 2)

    assert asyncio.run(run()) == "match foo()"


def test_enter_continues_multiline_foreach_until_done():
    async def run():
        with create_pipe_input() as pipe:
            session = create_session(input=pipe, output=DummyOutput())
            task = asyncio.create_task(session.prompt_async("ctk> "))
            pipe.send_text('foreach $x in $items do\r"${x}"\r')
            for _ in range(100):
                if session.default_buffer.text.endswith('"${x}"\n'):
                    break
                await asyncio.sleep(0.01)
            assert not task.done()
            pipe.send_text("done\r")
            return await asyncio.wait_for(task, 2)

    assert asyncio.run(run()) == 'foreach $x in $items do\n"${x}"\ndone'
