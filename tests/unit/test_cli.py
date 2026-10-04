from clang_toolkit.cli.app import dispatch
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
    client.match.assert_called_once_with(expression)


def test_invalid_matcher_is_not_dispatched():
    from unittest.mock import Mock

    client = Mock(spec=Client)
    assert dispatch(client, "match functionDecl(]").startswith("syntax error")
    client.match.assert_not_called()


def test_cfg_bare_and_qualified_names():
    from unittest.mock import Mock

    for name in ("foo", "app::foo"):
        client = Mock(spec=Client)
        client.cfg.return_value = "graph"
        assert dispatch(client, "cfg\t" + name) == "graph"
        client.cfg.assert_called_once_with(name)


def test_bare_callgraph_and_exit_alias():
    from unittest.mock import Mock

    client = Mock(spec=Client)
    client.callgraph.return_value = "graph"
    assert dispatch(client, "callgraph") == "graph"
    client.callgraph.assert_called_once_with()
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
    client.match.assert_called_once_with("varDecl(hasType(pointerType()))")
