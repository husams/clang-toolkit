"""Named arguments reach the real console runtime without opening a prompt."""

from __future__ import annotations

import asyncio
import io
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from clang_toolkit.cli import app
from clang_toolkit.client import Client


@pytest.fixture(autouse=True)
def isolate_default_libraries(monkeypatch, tmp_path):
    original = app.preload_libraries
    empty = tmp_path / "empty-ctk-libs"
    empty.mkdir()

    def preload(runtime, directory=None):
        return original(runtime, empty if directory is None else directory)

    monkeypatch.setattr(app, "preload_libraries", preload)


class TerminalInput(io.StringIO):
    def isatty(self) -> bool:
        return True


def run_cli(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, *arguments: str,
    stdin: str | None = None,
) -> int:
    client = Mock(spec=Client)
    client.compilation_database = None
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(app, "Client", lambda *_args, **_kwargs: client)
    monkeypatch.setattr(app, "create_session", Mock(side_effect=AssertionError("script opened an interactive UI")))
    monkeypatch.setattr(sys, "argv", ["ctk", *arguments])
    monkeypatch.setattr(sys, "stdin", TerminalInput() if stdin is None else io.StringIO(stdin))
    return asyncio.run(app._run())


@pytest.mark.parametrize("style", ["positional", "explicit", "intermixed"])
def test_script_file_receives_named_arguments(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str], style: str,
) -> None:
    script = tmp_path / "my script.ctk"
    script.write_text('print $arg.x\nprint $arg.count\nprint "EMPTY=${arg.empty}!"', encoding="utf-8")
    arguments = [str(script), "x=gggg", "count=002", "empty="]
    if style == "explicit":
        arguments.insert(0, "--script")
    elif style == "intermixed":
        arguments[1:1] = ["--server", "unix:///unused.sock"]
    assert run_cli(monkeypatch, tmp_path, *arguments) == 0
    assert capsys.readouterr().out.splitlines() == ["gggg", "002", "EMPTY=!"]


@pytest.mark.parametrize("mode", ["execute", "stdin"])
def test_values_remain_literal_strings(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str], mode: str,
) -> None:
    source = 'print $arg.x\nprint $arg.message\nprint $arg.syntax\nprint $arg.boolean'
    arguments = [" x =a=b=c", "message= hello world ", "syntax=$missing; quit", "boolean=false"]
    stdin = source if mode == "stdin" else None
    if mode == "execute":
        arguments[:0] = ["--execute", source]
    assert run_cli(monkeypatch, tmp_path, *arguments, stdin=stdin) == 0
    assert capsys.readouterr().out.splitlines() == ["a=b=c", " hello world ", "$missing; quit", "false"]


@pytest.mark.parametrize("style", ["positional", "explicit", "execute", "stdin"])
def test_arg_dictionary_exists_without_parameters(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str], style: str,
) -> None:
    script = tmp_path / "empty.ctk"
    script.write_text("print $arg.length", encoding="utf-8")
    arguments = {
        "positional": [str(script)], "explicit": ["--script", str(script)],
        "execute": ["-e", "print $arg.length"], "stdin": [],
    }[style]
    assert run_cli(monkeypatch, tmp_path, *arguments, stdin="print $arg.length" if style == "stdin" else None) == 0
    assert capsys.readouterr().out.strip() == "0"


def test_imported_library_can_read_script_arguments(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "lib.ctk").write_text("let value = $arg.x", encoding="utf-8")
    script = scripts / "main.ctk"
    script.write_text('import "lib.ctk"\nprint $value', encoding="utf-8")
    assert run_cli(monkeypatch, tmp_path, str(script), "x=from caller") == 0
    assert capsys.readouterr().out.strip() == "from caller"


@pytest.mark.parametrize("values, message", [
    (["missing_equals"], "must use KEY=VALUE"),
    (["=value"], "names cannot be empty"),
    (["  =value"], "names cannot be empty"),
    (["x=first", " x =second"], "duplicate script argument: x"),
])
def test_invalid_arguments_fail_before_script_effects(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str],
    values: list[str], message: str,
) -> None:
    script = tmp_path / "side_effect.ctk"
    script.write_text('save [1] to "ran.json" as json', encoding="utf-8")
    with pytest.raises(SystemExit) as raised:
        run_cli(monkeypatch, tmp_path, "--script", str(script), *values)
    assert raised.value.code == 2
    assert message in capsys.readouterr().err
    assert not (tmp_path / "ran.json").exists()


def test_named_values_require_script_mode(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as raised:
        run_cli(monkeypatch, tmp_path, "x=value")
    assert raised.value.code == 2
    assert "script arguments require" in capsys.readouterr().err


def test_unknown_and_non_utf8_scripts_do_not_open_the_ui(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    assert run_cli(monkeypatch, tmp_path, "missing.ctk", "x=value") == 1
    assert "cannot read script" in capsys.readouterr().out
    script = tmp_path / "binary.ctk"
    script.write_bytes(b"\xff")
    assert run_cli(monkeypatch, tmp_path, str(script)) == 1
    assert "cannot read script" in capsys.readouterr().out


def test_explicit_script_path_can_contain_equals(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    script = tmp_path / "name=value.ctk"
    script.write_text("print $arg.x", encoding="utf-8")
    assert run_cli(monkeypatch, tmp_path, "--script", str(script), "x=works") == 0
    assert capsys.readouterr().out.strip() == "works"
