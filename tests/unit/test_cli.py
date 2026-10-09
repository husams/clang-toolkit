from clang_toolkit.cli.app import dispatch
from clang_toolkit.cli.help import HAS_NATIVE_ANALYSIS_GRAMMAR
from clang_toolkit.client import Client


def test_help_lists_commands():
    assert "match" in dispatch(Client(), "help")


def test_dispatch_result_does_not_infer_failure_from_output_text():
    from unittest.mock import Mock

    from clang_toolkit.cli.app import dispatch_result

    runtime = Mock()
    runtime.history = None
    runtime.execute.return_value = "error: this is a valid string value"

    result = dispatch_result(Client(), '"error: this is a valid string value"', runtime)

    assert result.output == "error: this is a valid string value"
    assert result.success


def test_dispatch_result_marks_evaluation_exceptions_as_failures():
    from unittest.mock import Mock

    from clang_toolkit.cli.app import dispatch_result
    from clang_toolkit.cli.runtime import EvaluationError

    runtime = Mock()
    runtime.history = None
    runtime.execute.side_effect = EvaluationError("unknown variable: missing")

    result = dispatch_result(Client(), "server status", runtime)

    assert result.output == "error: unknown variable: missing"
    assert not result.success


def test_interactive_command_failure_sets_nonzero_process_status(monkeypatch, tmp_path):
    import asyncio
    import sys
    from unittest.mock import Mock

    from clang_toolkit.cli import app

    class QuerySession:
        closing = False

        async def events(self):
            if False:
                yield None

        async def aclose(self):
            self.closing = True

        async def cancel(self):
            self.closing = True

    class FakeAsyncClient:
        def __init__(self, *_args, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def query_session(self):
            return QuerySession()

        async def wait_background(self):
            return None

    class Prompt:
        def __init__(self):
            self.commands = iter(["$missing", "quit"])

        def prompt(self, _message):
            return next(self.commands)

    client = Mock()
    monkeypatch.setattr(app, "Client", lambda *_args, **_kwargs: client)
    monkeypatch.setattr(app, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(app, "create_session", lambda **_kwargs: Prompt())
    monkeypatch.setattr(sys, "argv", ["ctk"])
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))

    assert asyncio.run(app._run()) == 1


def test_quit_returns_none():
    assert dispatch(Client(), "quit") is None


def test_unknown_command():
    result = dispatch(Client(), "bogus")
    assert result.startswith("unknown command: bogus at line 1, column 1.")
    assert "Use `help`" in result
    assert result.endswith("bogus\n^")


def test_multiline_matcher_reaches_client_unchanged():
    from unittest.mock import Mock

    client = Mock(spec=Client)
    client.match.return_value = ["matched"]
    expression = 'functionDecl(\n  hasName("f[()]")\n).bind("fn")'
    assert dispatch(client, "match\n" + expression) == "matched"
    client.match.assert_called_once_with(
        expression, files=None, working_directory=__import__("pathlib").Path.cwd(),
        compile_arguments=[],
    )


def test_invalid_matcher_is_not_dispatched():
    from unittest.mock import Mock

    client = Mock(spec=Client)
    assert dispatch(client, "match functionDecl(]").startswith("syntax error")
    client.match.assert_not_called()


def test_legacy_cfg_names_report_missing_path_locally():
    from unittest.mock import Mock

    for name in ("foo", "app::foo"):
        client = Mock(spec=Client)
        expected = "cfg requires a file" if HAS_NATIVE_ANALYSIS_GRAMMAR else "cfg native execution is not implemented"
        assert expected in dispatch(client, "cfg\t" + name)
        client.cfg.assert_not_called()


def test_bare_callgraph_and_exit_alias():
    from unittest.mock import Mock

    client = Mock(spec=Client)
    expected = "callgraph requires a file" if HAS_NATIVE_ANALYSIS_GRAMMAR else "callgraph native execution is not implemented"
    assert expected in dispatch(client, "callgraph")
    client.callgraph.assert_not_called()
    assert dispatch(client, "exit") is None


def test_assignment_is_evaluated_without_server_call():
    from unittest.mock import Mock
    from clang_toolkit.cli.runtime import Runtime

    client = Mock(spec=Client)
    runtime = Runtime(client)
    assert dispatch(client, "let fn = functionDecl()", runtime) == ""
    assert dispatch(client, "$fn", runtime) == "functionDecl()"
    client.match.assert_not_called()


def test_interrupt_cancels_input_and_keeps_console_running(monkeypatch, tmp_path):
    from unittest.mock import Mock
    from clang_toolkit.cli import app

    session = Mock()
    session.prompt.side_effect = [KeyboardInterrupt, "quit"]
    monkeypatch.setattr(app, "create_session", lambda **_kwargs: session)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    monkeypatch.setattr("sys.argv", ["ctk"])
    app.main()
    assert session.prompt.call_count == 2


def test_main_preserves_bindings_between_prompt_commands(monkeypatch, tmp_path):
    from unittest.mock import Mock
    from clang_toolkit.cli import app

    client = Mock(spec=Client)
    client.match.return_value = ["matched"]
    session = Mock()
    session.prompt.side_effect = [
        "let m = hasType(pointerType())",
        "let f = varDecl($m)",
        "match $f",
        "quit",
    ]
    monkeypatch.setattr(app, "Client", lambda _address: client)
    monkeypatch.setattr(app, "create_session", lambda **_kwargs: session)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    monkeypatch.setattr("sys.argv", ["ctk"])
    app.main()
    client.match.assert_called_once_with(
        "varDecl(hasType(pointerType()))", files=None,
        working_directory=__import__("pathlib").Path.cwd(), compile_arguments=[],
    )


def test_background_command_uses_lark_matcher_and_selected_files():
    from pathlib import Path
    from unittest.mock import Mock
    from clang_toolkit.cli.runtime import Runtime

    client = Mock(spec=Client)
    runtime = Runtime(client, cwd=Path("/workspace"))
    runtime.config_store.effective["extra_args"] = ["-std=c++20"]
    assert dispatch(client, 'background varDecl(hasName("f")) in ["src/a.cpp"]', runtime) == client.start_background_query.return_value
    client.start_background_query.assert_called_once_with(
        'varDecl(hasName("f"))', ["/workspace/src/a.cpp"],
        working_directory=Path("/workspace"), compile_arguments=["-std=c++20"],
    )


def test_bidi_commands_forward_to_active_session():
    from unittest.mock import Mock
    from clang_toolkit.cli.runtime import Runtime

    client = Mock(spec=Client)
    runtime = Runtime(client)
    assert dispatch(client, 'session start "varDecl()"', runtime) == client.send_session_command.return_value
    client.send_session_command.assert_called_once_with(
        "start", "varDecl()", working_directory=runtime.cwd, compile_arguments=[],
    )


def test_session_add_uses_runtime_directory_and_compile_arguments():
    from pathlib import Path
    from unittest.mock import Mock
    from clang_toolkit.cli.runtime import Runtime

    client = Mock(spec=Client)
    runtime = Runtime(client, cwd=Path("/workspace"))
    runtime.config_store.effective["extra_args"] = ["-std=c++20"]
    dispatch(client, 'session add "src/query.cpp"', runtime)
    client.send_session_command.assert_called_once_with(
        "add", "src/query.cpp", working_directory=Path("/workspace"),
        compile_arguments=["-std=c++20"],
    )


def test_background_stream_is_consumed_while_prompt_accepts_next_command(monkeypatch, tmp_path):
    import asyncio
    from clang_toolkit.cli import app

    background_consumed = None

    class BackgroundClient:
        def __init__(self, *_args):
            self.query_session_instance = None

        async def __aenter__(self):
            nonlocal background_consumed
            background_consumed = asyncio.Event()
            return self

        async def __aexit__(self, *_args):
            return None

        def start_background_query(self, *_args, **_kwargs):
            async def consume():
                await asyncio.sleep(0)
                background_consumed.set()
            return asyncio.create_task(consume())

        async def wait_background(self):
            await asyncio.sleep(0)

        async def query_session(self):
            self.query_session_instance = SessionStream()
            return self.query_session_instance

    class SessionStream:
        def __init__(self):
            self.closing = False
            self.closed = asyncio.Event()

        async def events(self):
            await self.closed.wait()
            raise app.QueryError("query session cancelled: CANCELLED")
            yield None

        async def aclose(self):
            self.closing = True
            self.closed.set()

        async def cancel(self):
            self.closing = True
            self.closed.set()

    class Prompt:
        async def prompt_async(self, _message):
            await background_consumed.wait()
            return "quit"

    monkeypatch.setattr(app, "AsyncClient", BackgroundClient)
    monkeypatch.setattr(app, "create_session", lambda **_kwargs: Prompt())
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    monkeypatch.setattr("sys.argv", ["ctk", "--query", "varDecl()", "--background"])
    app.main()


def test_interactive_console_starts_session_by_default_and_keeps_legacy_flag(monkeypatch, tmp_path, capsys):
    import asyncio
    from clang_toolkit.cli import app

    class QuerySession:
        def __init__(self):
            self.closing = False
            self.started_reading = asyncio.Event()
            self.closed = asyncio.Event()

        async def events(self):
            self.started_reading.set()
            await self.closed.wait()
            raise app.QueryError("query session cancelled: CANCELLED")
            yield None

        async def aclose(self):
            self.closing = True
            self.closed.set()

        async def cancel(self):
            self.closing = True
            self.closed.set()

    class FakeAsyncClient:
        instances = []

        def __init__(self, *_args, **_kwargs):
            self.session = QuerySession()
            self.session_opens = 0
            self.__class__.instances.append(self)

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def query_session(self):
            self.session_opens += 1
            return self.session

        async def wait_background(self):
            return None

    class Prompt:
        async def prompt_async(self, _message):
            await FakeAsyncClient.instances[-1].session.started_reading.wait()
            return "quit"

    def run_console(arguments):
        FakeAsyncClient.instances.clear()
        monkeypatch.setattr(app, "AsyncClient", FakeAsyncClient)
        monkeypatch.setattr(app, "create_session", lambda **_kwargs: Prompt())
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
        monkeypatch.setattr("sys.argv", ["ctk", *arguments])
        app.main()
        fake = FakeAsyncClient.instances[-1]
        assert fake.session_opens == 1
        assert fake.session.closing
        assert "error:" not in capsys.readouterr().out

    run_console([])
    run_console(["--session"])


def test_foreground_query_does_not_open_interactive_session(monkeypatch, tmp_path):
    from clang_toolkit.cli import app

    class FakeAsyncClient:
        session_opens = 0

        def __init__(self, *_args, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def query(self, *_args, **_kwargs):
            return None

        async def query_session(self):
            self.session_opens += 1
            raise AssertionError("one-shot query opened an interactive session")

    monkeypatch.setattr(app, "AsyncClient", FakeAsyncClient)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    monkeypatch.setattr("sys.argv", ["ctk", "--query", "varDecl()"])
    app.main()
    assert FakeAsyncClient.session_opens == 0


def test_paused_session_shutdown_cancels_after_bounded_drain(monkeypatch, tmp_path):
    import asyncio
    from clang_toolkit.cli import app

    class QuerySession:
        def __init__(self, finish_reader):
            self.closing = False
            self.finish_reader = finish_reader
            self.reading = asyncio.Event()
            self.cancelled = asyncio.Event()
            self.reader_done = asyncio.Event()

        async def events(self):
            self.reading.set()
            try:
                if self.finish_reader:
                    return
                await self.cancelled.wait()
                raise app.QueryError("query session cancelled: CANCELLED")
                yield None
            finally:
                self.reader_done.set()

        async def aclose(self):
            self.closing = True
            await self.reading.wait()
            await asyncio.Event().wait()

        async def cancel(self):
            self.closing = True
            self.cancelled.set()

    class FakeAsyncClient:
        instance = None
        finish_reader = False

        def __init__(self, *_args, **_kwargs):
            self.session = QuerySession(self.finish_reader)
            self.__class__.instance = self

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def query_session(self):
            return self.session

        async def wait_background(self):
            return None

    class Prompt:
        async def prompt_async(self, _message):
            await FakeAsyncClient.instance.session.reading.wait()
            return "quit"

    monkeypatch.setattr(app, "_SESSION_CLOSE_TIMEOUT", 0.01)
    monkeypatch.setattr(app, "AsyncClient", FakeAsyncClient)
    monkeypatch.setattr(app, "create_session", lambda **_kwargs: Prompt())
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    monkeypatch.setattr("sys.argv", ["ctk"])
    for finish_reader in (False, True):
        FakeAsyncClient.finish_reader = finish_reader
        app.main()
        assert FakeAsyncClient.instance.session.cancelled.is_set()
        assert FakeAsyncClient.instance.session.reader_done.is_set()


def test_session_command_reports_closed_stream_failure():
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    import pytest
    from clang_toolkit.client import Client, QueryError

    async def exercise():
        session = SimpleNamespace(
            client=SimpleNamespace(compilation_database=None),
            _input_closed=False,
            start_query=AsyncMock(side_effect=RuntimeError("query session input is already closed")),
        )
        async_client = SimpleNamespace(config=SimpleNamespace())
        client = Client()
        client.bind_async_client(async_client)
        client.bind_query_session(session)
        with pytest.raises(QueryError, match="query session input is already closed"):
            await asyncio.to_thread(client.send_session_command, "start", "varDecl()")
        session._input_closed = True
        with pytest.raises(QueryError, match="interactive query session is closed"):
            await asyncio.to_thread(client.send_session_command, "start", "varDecl()")

    asyncio.run(exercise())


def test_session_command_reports_ended_stream_failure():
    import asyncio
    from types import SimpleNamespace
    import pytest
    from clang_toolkit.client import Client, QueryError, QuerySession

    async def exercise():
        async_client = SimpleNamespace(config=SimpleNamespace(), compilation_database=None)
        session = QuerySession(async_client)
        session._call = SimpleNamespace(done=lambda: True)
        client = Client()
        client.bind_async_client(async_client)
        client.bind_query_session(session)
        with pytest.raises(QueryError, match="query session stream has ended"):
            await asyncio.to_thread(client.send_session_command, "start", "varDecl()")

    asyncio.run(exercise())
