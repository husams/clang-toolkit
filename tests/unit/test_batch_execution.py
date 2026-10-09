from clang_toolkit.cli.app import DispatchResult
from clang_toolkit.cli.batch import execute_batch


def test_batch_keeps_success_status_separate_from_rendered_error_prefix():
    result = execute_batch(
        '"error: this is a value"',
        lambda _command: DispatchResult("error: this is a value", True),
    )

    assert result.exit_code == 0
    assert result.outputs == ("error: this is a value",)


def test_batch_stops_at_first_failed_command_by_default():
    seen = []

    def dispatch(command):
        seen.append(command)
        return DispatchResult("error: missing variable", False)

    result = execute_batch("$missing\nhelp", dispatch)

    assert result.exit_code == 1
    assert seen == ["$missing"]
    assert result.outputs == ("error at line 1: error: missing variable",)


def test_batch_can_continue_after_failed_command():
    seen = []

    def dispatch(command):
        seen.append(command)
        if command == "$missing":
            return DispatchResult("error: missing variable", False)
        return DispatchResult("help output", True)

    result = execute_batch("$missing\nhelp", dispatch, continue_on_error=True)

    assert result.exit_code == 1
    assert seen == ["$missing", "help"]
    assert result.outputs == (
        "error at line 1: error: missing variable",
        "help output",
    )


def test_batch_diagnostics_use_source_line_for_syntax_errors():
    result = execute_batch('help\n"unterminated', lambda _command: None)

    assert result.exit_code == 1
    assert "line 2" in result.outputs[0]


def test_empty_batch_succeeds_without_dispatch():
    result = execute_batch(" \n", lambda _command: None)

    assert result.exit_code == 0
    assert result.outputs == ()


def test_batch_requirements_come_from_formal_command_trees():
    from clang_toolkit.cli.batch import batch_requirements

    assert not batch_requirements('print "session start is only text"').query_session
    assert batch_requirements('session start "varDecl()"').query_session
    assert batch_requirements('background varDecl()').background_query
    assert not batch_requirements('print "ok"\n"unterminated').query_session


def test_session_match_waits_for_its_correlated_delayed_completion():
    import asyncio
    import threading
    from types import SimpleNamespace

    from clang_toolkit.cli.app import _SessionCompletionTracker

    async def run():
        tracker = _SessionCompletionTracker(asyncio.get_running_loop())
        tracker.observe(SimpleNamespace(
            request_id="add-request",
            control=SimpleNamespace(action="files-accepted"),
            WhichOneof=lambda _name: "control",
        ))
        waiting = threading.Event()

        def wait_for_completion():
            waiting.set()
            return tracker.wait_from_thread("match-request", "match")

        waiter = asyncio.create_task(asyncio.to_thread(wait_for_completion))
        await asyncio.to_thread(waiting.wait)
        assert not waiter.done()

        completed = SimpleNamespace(
            request_id="match-request",
            progress=SimpleNamespace(completed_files=1, accepted_files=1),
            WhichOneof=lambda _name: "progress",
        )
        tracker.observe(completed)
        assert await waiter is completed
        assert "match-request" not in tracker._controls
        assert "match-request" not in tracker._latest_progress
        assert "match-request" not in tracker._ready

    asyncio.run(run())


def test_session_tracker_discards_match_payloads_and_keeps_only_latest_progress():
    import asyncio
    from types import SimpleNamespace

    from clang_toolkit.cli.app import _SessionCompletionTracker

    tracker = _SessionCompletionTracker(asyncio.new_event_loop())
    large_payload = b"x" * (128 * 1024)
    for index in range(2000):
        tracker.observe(SimpleNamespace(
            request_id="match-request",
            semantic_result=large_payload,
            WhichOneof=lambda _name: "match",
        ))
        tracker.observe(SimpleNamespace(
            request_id="match-request",
            progress=SimpleNamespace(completed_files=index, accepted_files=2000),
            WhichOneof=lambda _name: "progress",
        ))

    assert tracker._controls == {}
    assert tracker._rejections == {}
    assert len(tracker._latest_progress) == 1
    assert tracker._latest_progress["match-request"].progress.completed_files == 1999
    assert tracker._ready == {}
    tracker._loop.close()


def test_session_tracker_eof_wakes_pending_command_wait():
    import asyncio
    import threading
    from types import SimpleNamespace

    import pytest

    from clang_toolkit.cli.app import _SessionCompletionTracker
    from clang_toolkit.client import QueryError

    async def run():
        tracker = _SessionCompletionTracker(asyncio.get_running_loop())
        waiting = threading.Event()

        def wait_for_acknowledgment():
            waiting.set()
            return tracker.wait_from_thread("missing-request", "start")

        waiter = asyncio.create_task(asyncio.to_thread(wait_for_acknowledgment))
        await asyncio.to_thread(waiting.wait)
        tracker.finish()
        with pytest.raises(QueryError, match="ended before start request missing-request"):
            await waiter

    asyncio.run(run())


def test_execute_flag_runs_without_opening_a_prompt(monkeypatch, tmp_path, capsys):
    import asyncio
    import sys
    from unittest.mock import Mock

    from clang_toolkit.cli import app
    from clang_toolkit.client import Client

    client = Mock(spec=Client)
    monkeypatch.setattr(app, "Client", lambda *_args, **_kwargs: client)
    monkeypatch.setattr(sys, "argv", ["ctk", "-e", "help"])
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    assert asyncio.run(app._run()) == 0
    assert "callgraph" in capsys.readouterr().out


def test_execute_treats_literal_error_prefix_as_success(monkeypatch, tmp_path, capsys):
    import asyncio
    import sys
    from unittest.mock import Mock

    from clang_toolkit.cli import app
    from clang_toolkit.client import Client

    client = Mock(spec=Client)
    monkeypatch.setattr(app, "Client", lambda *_args, **_kwargs: client)
    monkeypatch.setattr(sys, "argv", ["ctk", "-e", '"error: literal value"'])
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    assert asyncio.run(app._run()) == 0
    assert capsys.readouterr().out.strip() == "error: literal value"


def test_continue_on_error_runs_later_commands_and_keeps_failure_status(
    monkeypatch, tmp_path, capsys
):
    import asyncio
    import sys
    from unittest.mock import Mock

    from clang_toolkit.cli import app
    from clang_toolkit.client import Client

    client = Mock(spec=Client)
    monkeypatch.setattr(app, "Client", lambda *_args, **_kwargs: client)
    monkeypatch.setattr(
        sys,
        "argv",
        ["ctk", "--continue-on-error", "-e", "$missing\nhelp"],
    )
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    assert asyncio.run(app._run()) == 1
    output = capsys.readouterr().out
    assert "error at line 1" in output
    assert "callgraph" in output


def test_long_incomplete_batch_string_fails_without_prompt_completion(
    monkeypatch, tmp_path, capsys
):
    import asyncio
    import sys
    from unittest.mock import Mock

    from clang_toolkit.cli import app
    from clang_toolkit.client import Client

    client = Mock(spec=Client)
    monkeypatch.setattr(app, "Client", lambda *_args, **_kwargs: client)
    monkeypatch.setattr(
        app,
        "create_session",
        Mock(side_effect=AssertionError("batch opened a prompt")),
    )
    monkeypatch.setattr(sys, "argv", ["ctk", "-e", '"' + "x" * 4200])
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    assert asyncio.run(app._run()) == 1
    assert "syntax error" in capsys.readouterr().out


def test_script_file_and_nonterminal_stdin_use_batch_path(monkeypatch, tmp_path, capsys):
    import asyncio
    import io
    import sys
    from unittest.mock import Mock

    from clang_toolkit.cli import app
    from clang_toolkit.client import Client

    client = Mock(spec=Client)
    monkeypatch.setattr(app, "Client", lambda *_args, **_kwargs: client)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    script = tmp_path / "commands.ctk"
    script.write_text("help\nhelp", encoding="utf-8")

    monkeypatch.setattr(sys, "argv", ["ctk", "--script", str(script)])
    assert asyncio.run(app._run()) == 0
    assert capsys.readouterr().out.count("callgraph") == 2

    monkeypatch.setattr(sys, "stdin", io.StringIO("help\n"))
    monkeypatch.setattr(sys, "argv", ["ctk"])
    assert asyncio.run(app._run()) == 0
    assert "callgraph" in capsys.readouterr().out


def test_local_batch_and_syntax_error_do_not_connect_to_server(tmp_path):
    import os
    import subprocess
    import sys

    endpoint = f"unix://{tmp_path / 'absent.sock'}"
    env = dict(os.environ, XDG_STATE_HOME=str(tmp_path / "state"))

    local = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server", endpoint,
         "-e", 'print "LOCAL_BATCH_OK"'],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        env=env, timeout=10, check=False,
    )
    assert local.returncode == 0, local.stdout
    assert local.stdout.strip() == "LOCAL_BATCH_OK"

    invalid = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server", endpoint,
         "-e", 'print "MUST_NOT_RUN"\n"unterminated'],
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        env=env, timeout=10, check=False,
    )
    assert invalid.returncode == 1, invalid.stdout
    assert "syntax error" in invalid.stdout
    assert "MUST_NOT_RUN" not in invalid.stdout
