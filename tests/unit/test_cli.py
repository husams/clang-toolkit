from clang_toolkit.cli.app import dispatch
from clang_toolkit.cli.help import HAS_NATIVE_ANALYSIS_GRAMMAR
from clang_toolkit.client import Client


def test_help_lists_commands():
    assert "match" in dispatch(Client(), "help")


def test_quit_returns_none():
    assert dispatch(Client(), "quit") is None


def test_unknown_command():
    assert dispatch(Client(), "bogus") == "unknown command: bogus"


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


def test_bidi_commands_require_and_forward_to_opted_in_session():
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

    consumed = None

    class BackgroundClient:
        def __init__(self, *_args):
            pass

        async def __aenter__(self):
            nonlocal consumed
            consumed = asyncio.Event()
            return self

        async def __aexit__(self, *_args):
            return None

        def start_background_query(self, *_args, **_kwargs):
            async def consume():
                await asyncio.sleep(0)
                consumed.set()
            return asyncio.create_task(consume())

        async def wait_background(self):
            await asyncio.sleep(0)

    class Prompt:
        async def prompt_async(self, _message):
            await consumed.wait()
            return "quit"

    monkeypatch.setattr(app, "AsyncClient", BackgroundClient)
    monkeypatch.setattr(app, "create_session", lambda **_kwargs: Prompt())
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path))
    monkeypatch.setattr("sys.argv", ["ctk", "--query", "varDecl()", "--background"])
    app.main()
