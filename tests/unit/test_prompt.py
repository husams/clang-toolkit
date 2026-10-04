from __future__ import annotations

import asyncio

import pytest
from prompt_toolkit.document import Document
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.validation import ValidationError

from clang_toolkit.cli.prompt import InputValidator, create_session


@pytest.mark.parametrize("text", ["([)]", "foo(]", ")", "foo(@)"])
def test_invalid_delimiters_are_reported(text):
    with pytest.raises(ValidationError, match="mismatched"):
        InputValidator().validate(Document(text))


@pytest.mark.parametrize("text", ["foo(", 'foo("open', "[{}", "{"])
def test_forced_submission_cannot_bypass_incomplete_input(text):
    with pytest.raises(ValidationError, match="Close"):
        InputValidator().validate(Document(text))


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
