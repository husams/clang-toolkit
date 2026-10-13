"""The isolated console entrypoint selects compiled scripting by default."""

from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest

from clang_toolkit.cli import app


SOURCE = "let x = 1\nlet y = $x + 1\nprint $y"


@pytest.fixture(autouse=True)
def isolated_console(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))


@pytest.mark.parametrize("engine_args", [[], ["--script-engine", "tree"], ["--script-engine", "compiled"]])
def test_prototype_default_and_explicit_engines_execute_arithmetic(monkeypatch, capsys, engine_args):
    monkeypatch.setattr(sys, "argv", ["ctk", *engine_args, "--execute", SOURCE])
    app.prototype_main()
    assert capsys.readouterr().out.strip() == "2"


@pytest.mark.parametrize("entrypoint,engine_args", [(app.main, []), (app.prototype_main, ["--script-engine", "legacy"])])
def test_legacy_default_and_override_preserve_legacy_parser(monkeypatch, capsys, entrypoint, engine_args):
    monkeypatch.setattr(sys, "argv", ["ctk", *engine_args, "--execute", SOURCE])
    with pytest.raises(SystemExit) as error:
        entrypoint()
    assert error.value.code == 1
    assert "unexpected character `+`" in capsys.readouterr().out


@pytest.mark.parametrize("input_mode", ["script", "positional", "stdin"])
def test_prototype_file_and_stdin_keep_named_arguments(monkeypatch, tmp_path, capsys, input_mode):
    source = "let x = 1; let y = $x + 1; print $arg.label; print $y"
    script = tmp_path / "example.ctks"
    script.write_text(source)
    if input_mode == "script":
        arguments = ["--script", str(script)]
    elif input_mode == "positional":
        arguments = [str(script)]
    else:
        arguments = []
        monkeypatch.setattr(sys, "stdin", io.StringIO(source))
    monkeypatch.setattr(sys, "argv", ["ctk", *arguments, "label=example"])
    app.prototype_main()
    assert capsys.readouterr().out.strip() == "example\n2"


def test_prototype_help_reports_compiled_default(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["ctk", "--help"])
    with pytest.raises(SystemExit) as error:
        app.prototype_main()
    assert error.value.code == 0
    assert "default: compiled" in capsys.readouterr().out


def test_prototype_invalid_option_preserves_argument_error(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["ctk", "--script-engine", "invalid"])
    with pytest.raises(SystemExit) as error:
        app.prototype_main()
    assert error.value.code == 2
    assert "invalid choice" in capsys.readouterr().err
