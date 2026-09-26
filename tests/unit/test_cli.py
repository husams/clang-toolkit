from clang_toolkit.cli.app import dispatch
from clang_toolkit.client import Client


def test_help_lists_commands():
    assert "match" in dispatch(Client(), "help")


def test_quit_returns_none():
    assert dispatch(Client(), "quit") is None


def test_unknown_command():
    assert dispatch(Client(), "bogus") == "unknown command: bogus"
