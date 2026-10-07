"""BDD using real prompt input, a real filesystem, and native RPC integration."""

from __future__ import annotations

import asyncio
from pathlib import Path

from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from pytest_bdd import given, parsers, scenarios, then, when

from clang_toolkit.cli.app import dispatch
from clang_toolkit.cli.language import parser
from clang_toolkit.cli.prompt import create_session
from clang_toolkit.cli.runtime import Runtime
from clang_toolkit.client import Client

from tests.e2e.test_network_steps import _launch_server

scenarios("console_help_completion.feature")


async def _wait_text(session, expected: str) -> None:
    for _ in range(300):
        if session.default_buffer.text == expected:
            return
        await asyncio.sleep(0.01)
    raise AssertionError(f"expected {expected!r}, got {session.default_buffer.text!r}")


async def _tab(pipe, session, expected: str) -> None:
    original = session.default_buffer.text
    for _ in range(300):
        if session.default_buffer.text == expected:
            return
        state = session.default_buffer.complete_state
        if (
            state is not None
            and state.completions
            and state.original_document.text == original
        ):
            assert len(state.completions) == 1
            pipe.send_text("\t")
            await _wait_text(session, expected)
            return
        await asyncio.sleep(0.01)
    raise AssertionError("Tab did not produce path candidates")


async def _prompt(
    cwd: Path, source: str, *, completion: bool = False, navigate: bool = False
) -> str:
    with create_pipe_input() as pipe:
        session = create_session(input=pipe, output=DummyOutput(), cwd=cwd)
        task = asyncio.create_task(session.prompt_async("ctk> "))
        try:
            pipe.send_text(source)
            await _wait_text(session, source)
            if completion:
                expected = (
                    'parse "source dir/"' if navigate else 'parse "source space.cc"'
                )
                await _tab(pipe, session, expected)
                if navigate:
                    pipe.send_text("nes")
                    await _wait_text(session, expected + "nes")
                    await _tab(pipe, session, 'parse "source dir/nested file.cc"')
            pipe.send_text("\r")
            return await asyncio.wait_for(task, 3)
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)


@given("an offline interactive console", target_fixture="offline_client")
def offline_client():
    # The socket does not exist. Help must neither connect nor open a session.
    return Client("unix:///tmp/ctk-console-help-no-server.sock")


@when(
    parsers.parse('I submit help text "{command}" through the prompt'),
    target_fixture="help_output",
)
def submit_help(offline_client, tmp_path, command):
    line = asyncio.run(_prompt(tmp_path, command))
    return dispatch(offline_client, line)


@then(parsers.parse('detailed help contains "{usage}"'))
def detailed_help(help_output, usage):
    assert usage in help_output
    assert "Arguments, options and defaults:" in help_output
    assert "Examples:" in help_output


@then("help reports an unknown topic")
def unknown_topic(help_output):
    assert (
        help_output == "unknown help topic: cursor missing; use help to list commands"
    )


@given("console files with spaces", target_fixture="console_files")
def console_files(tmp_path):
    (tmp_path / "source space.cc").write_text(
        "int completed_function() { return 7; }\n"
    )
    (tmp_path / "source dir").mkdir()
    (tmp_path / "source dir" / "nested file.cc").write_text(
        "int nested_function() { return 1; }\n"
    )
    return tmp_path


@when(
    "I complete the unfinished path through the prompt", target_fixture="completed_line"
)
def complete_path(console_files):
    return asyncio.run(_prompt(console_files, 'parse "source sp', completion=True))


@then("the submitted sentence is a valid quoted parse command")
def valid_path(completed_line):
    assert completed_line == 'parse "source space.cc"'
    assert parser().parse(completed_line)


@when(
    "I navigate a directory and complete its child through the prompt",
    target_fixture="completed_line",
)
def navigate(console_files):
    return asyncio.run(
        _prompt(console_files, 'parse "source d', completion=True, navigate=True)
    )


@then("the submitted sentence selects the child file")
def child_path(completed_line):
    assert completed_line == 'parse "source dir/nested file.cc"'
    assert parser().parse(completed_line)


@given("a native server for console completion", target_fixture="console_server")
def console_server(tmp_path, request):
    return _launch_server("unix", tmp_path, request)


@when(
    "I complete the unfinished path and execute declarative analysis",
    target_fixture="native_output",
)
def execute_analysis(console_files, console_server):
    line = asyncio.run(_prompt(console_files, 'parse "source sp', completion=True))
    client = Client(console_server.endpoint)
    runtime = Runtime(client, cwd=console_files, environment={})
    try:
        assert dispatch(client, "let tree = " + line, runtime) == ""
        output = dispatch(
            client,
            'match functionDecl(hasName("completed_function")).bind("f") in $tree',
            runtime,
        )
        return output
    finally:
        runtime.close()
        client.close()


@then("native analysis finds the declared function")
def native_function(native_output):
    assert "completed_function" in native_output
