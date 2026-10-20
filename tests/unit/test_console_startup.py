"""Startup must keep help imports and delayed completion off the input path."""

from __future__ import annotations

import asyncio
import subprocess
import sys
import threading

import pytest
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.input import create_pipe_input

from clang_toolkit.cli.app import DispatchResult
from clang_toolkit.cli.prompt import create_session
from clang_toolkit.cli.workspace import WorkspaceConsole
from test_workspace import SizedOutput, wait_until


def test_importing_console_help_does_not_build_a_parser():
    subprocess.run(
        [sys.executable, "-c", '''
import lark
def unexpected(*args, **kwargs):
    raise AssertionError("help import must not build a parser")
lark.Lark.__init__ = unexpected
from clang_toolkit.cli.help import COMMAND_HELP
assert "cfg" in COMMAND_HELP and "callgraph" in COMMAND_HELP
'''],
        check=True, capture_output=True, text=True, timeout=10,
    )


def test_startup_output_does_not_reenter_redirected_stdout():
    # A subprocess deadline turns a printing-lock deadlock into a bounded failure.
    subprocess.run(
        [sys.executable, "-c", '''
from contextlib import redirect_stdout
from clang_toolkit.cli.workspace_markdown import render_markdown
from clang_toolkit.cli.workspace_output import WorkspaceOutput
rendered = []
stream = WorkspaceOutput(lambda text: rendered.append(render_markdown(text, 80)[0]))
with redirect_stdout(stream):
    print("Connection unavailable")
assert len(rendered) == 1 and "Connection unavailable" in rendered[0]
'''],
        check=True, capture_output=True, text=True, timeout=10,
    )


@pytest.mark.parametrize("engine", ["legacy", "compiled"])
def test_typing_and_redraw_continue_while_completion_is_blocked(tmp_path, engine):
    entered = threading.Event()
    release = threading.Event()

    class DelayedCompleter(Completer):
        def get_completions(self, document, complete_event):
            entered.set()
            assert release.wait(5), "completion must not block input processing"
            yield Completion("match", start_position=-len(document.text))

    async def run():
        async def execute(source):
            return DispatchResult(source, True)

        with create_pipe_input() as pipe:
            output = SizedOutput(columns=90)
            session = create_session(input=pipe, output=output, script_engine=engine)
            session.completer = DelayedCompleter()
            ui = WorkspaceConsole(session, tmp_path, execute, input=pipe, output=output)
            rendered = []
            ui.app.after_render += lambda _app: rendered.append(ui.buffer.text)
            task = asyncio.create_task(ui.run())
            try:
                await wait_until(lambda: ui.app.is_running)
                pipe.send_text("m")
                await wait_until(entered.is_set)
                pipe.send_text("a")
                await wait_until(lambda: "ma" in rendered)
                assert not release.is_set()
                release.set()
                await wait_until(lambda: ui.buffer.complete_state is not None)
                choices = ui.buffer.complete_state.completions
                assert choices[0].text == "match"
            finally:
                release.set()
                if not task.done():
                    ui.request_exit()
                await asyncio.wait_for(task, 3)

    asyncio.run(run())


def test_hidden_help_does_not_tokenize_and_visible_help_uses_active_editor(tmp_path):
    async def execute(source):
        return DispatchResult(source, True)

    with create_pipe_input() as pipe:
        output = SizedOutput(columns=90)
        session = create_session(input=pipe, output=output, script_engine="compiled")
        tokenize = session.editor_tokenizer
        sources = []

        def record(source):
            sources.append(source)
            return tokenize(source)

        session.editor_tokenizer = record
        ui = WorkspaceConsole(session, tmp_path, execute, input=pipe, output=output)
        ui.buffer.text = 'match functionDecl(hasName("'
        ui.buffer.cursor_position = len(ui.buffer.text)
        ui._update_context(ui.app)
        assert sources == []
        ui.panel_requested = True
        ui._update_context(ui.app)
        assert sources == [ui.buffer.text]
        assert "## hasName" in ui.context.render_key[0]
