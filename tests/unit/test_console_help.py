"""Detailed help is grammar-driven, offline, and independent of output routing."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from clang_toolkit.cli.app import dispatch
from clang_toolkit.cli.help import COMMAND_HELP, reference_markdown
from clang_toolkit.cli.input_state import input_state
from clang_toolkit.cli.language import parser
from clang_toolkit.cli.runtime import Runtime
from clang_toolkit.client import Client


@pytest.mark.parametrize("topic", COMMAND_HELP)
def test_topic_shortcuts_equivalent_and_submit_without_continuation(topic):
    client = Mock(spec=Client)
    long = dispatch(client, f"help {topic}")
    short = dispatch(client, f"{topic}?")
    assert long == short
    assert "Usage:" in long
    assert "Arguments, options and defaults:" in long
    assert "Examples:" in long
    assert input_state(f"{topic}?").error_at is None
    assert not input_state(f"{topic}?").needs_more
    assert client.mock_calls == []


@pytest.mark.parametrize(
    "source", ["help nonsense", "nonsense?", "help cursor nonsense", "cursor nonsense?"]
)
def test_unknown_help_is_local(source):
    client = Mock(spec=Client)
    assert dispatch(client, source).startswith("unknown help topic:")
    assert client.mock_calls == []


def test_help_does_not_initialize_settings_or_output(monkeypatch):
    def unexpected_runtime(*_args, **_kwargs):
        raise AssertionError("offline help must not initialize runtime state")

    monkeypatch.setattr("clang_toolkit.cli.app.Runtime", unexpected_runtime)
    client = Mock(spec=Client)
    assert "help <command>" in dispatch(client, "help")
    assert dispatch(client, "") == dispatch(client, "help")
    assert "parse PATH" in dispatch(client, "parse?")
    assert dispatch(client, "unknown") == "unknown command: unknown"
    assert client.mock_calls == []


def test_runtime_help_stays_visible_when_values_are_redirected(tmp_path):
    runtime = Runtime(Mock(spec=Client), cwd=tmp_path, environment={})
    destination = tmp_path / "results.txt"
    runtime.output.configure(str(destination))
    try:
        assert "match MATCHER" in runtime.execute("match?")
        assert "match MATCHER" in dispatch(runtime.client, "help match", runtime)
        assert destination.read_text() == ""
    finally:
        runtime.close()


def test_every_help_example_is_accepted_by_the_current_grammar():
    for entry in COMMAND_HELP.values():
        for example in entry.examples:
            assert parser().parse(example), (entry.topic, example)


def test_checked_in_reference_matches_console_entries():
    root = Path(__file__).resolve().parents[2]
    assert (
        root / "docs/console-command-reference.md"
    ).read_text() == reference_markdown()


def test_semicolons_whitespace_and_unknown_commands():
    client = Mock(spec=Client)
    assert dispatch(client, "cursor\t open ?;") == dispatch(client, "help cursor open;")
    assert dispatch(client, "help\nparse") == dispatch(client, "parse?")
    assert dispatch(client, "bogus args") == "unknown command: bogus"
    assert dispatch(client, "match bogus?").startswith("unknown help topic:")
    assert client.mock_calls == []


def test_help_topic_completion():
    from prompt_toolkit.document import Document
    from clang_toolkit.cli.completion import ReplCompleter

    def choices(text):
        return [c.text for c in ReplCompleter().get_completions(Document(text), None)]

    assert "parse" in choices("help pa")
    assert choices("help cursor o") == ["open"]
    assert set(choices("help session ")) == {
        "start",
        "add",
        "match",
        "pause",
        "resume",
        "close",
        "label",
    }
