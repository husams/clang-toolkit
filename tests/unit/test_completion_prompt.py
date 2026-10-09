"""Exercise completion through the actual prompt input bindings."""

from __future__ import annotations

import asyncio

from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.document import Document

from clang_toolkit.cli.prompt import create_session
from clang_toolkit.cli.completion import ReplCompleter


def test_match_command_shows_root_choices_and_inserts_valid_expression():
    async def run():
        with create_pipe_input() as pipe:
            session = create_session(input=pipe, output=DummyOutput())
            prompt = asyncio.create_task(session.prompt_async("ctk> "))
            pipe.send_text("match\t\t")
            for _ in range(200):
                state = session.default_buffer.complete_state
                if state and state.completions:
                    break
                await asyncio.sleep(0.01)
            else:
                prompt.cancel()
                raise AssertionError("Tab did not show matcher choices")
            choices = state.completions
            displays = {choice.display_text for choice in choices}
            assert "functionDecl(" in displays
            assert "hasName(" not in displays
            assert "match" not in displays
            selected = next(c for c in choices if c.display_text == "functionDecl(")
            session.default_buffer.apply_completion(selected)
            assert session.default_buffer.text == "match functionDecl("
            pipe.send_text(")\r")
            return await asyncio.wait_for(prompt, 2)

    assert asyncio.run(run()) == "match functionDecl()"


def test_very_long_partial_input_skips_automatic_completion(monkeypatch):
    from clang_toolkit.cli import completion

    def unexpected_completion(*_args, **_kwargs):
        raise AssertionError("long partial input should not be parsed for completion")

    monkeypatch.setattr(completion, "cursor_context", unexpected_completion)
    assert list(ReplCompleter().get_completions(Document('"' + "x" * 2100), None)) == []
