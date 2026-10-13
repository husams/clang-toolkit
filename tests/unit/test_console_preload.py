"""Startup libraries use the console's existing import semantics."""

from __future__ import annotations

import asyncio
import io
import sys
from pathlib import Path
from unittest.mock import Mock

import pytest

from clang_toolkit.cli import app
from clang_toolkit.cli.runtime import EvaluationError
from clang_toolkit.cli.runtime.imports import preload_libraries
from clang_toolkit.client import Client


@pytest.fixture
def isolated_home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(home / ".config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(home / ".local" / "state"))
    monkeypatch.chdir(tmp_path)
    return home


@pytest.fixture(params=["legacy", "tree", "compiled"])
def runtime(request, tmp_path: Path, isolated_home: Path):
    client = Mock(spec=Client)
    client.compilation_database = None
    instance = app._runtime_for_engine(client, request.param, cwd=tmp_path, environment={})
    yield instance
    instance.close()


def test_preload_sorts_libraries_and_resolves_nested_imports(runtime) -> None:
    library_dir = runtime.cwd / "libraries"
    parts = library_dir / "parts"
    parts.mkdir(parents=True)
    (parts / "constants.ctk").write_text('let label = "loaded"', encoding="utf-8")
    # Create these in the reverse order to expose unsorted directory iteration.
    (library_dir / "20-matchers.ctk").write_text(
        'let selected = $label\nlet named(name) = functionDecl(hasName($name))',
        encoding="utf-8",
    )
    (library_dir / "10-values.ctk").write_text('import "parts/constants.ctk"', encoding="utf-8")
    (library_dir / "ignored.txt").write_text("quit", encoding="utf-8")
    (library_dir / "directory.ctk").mkdir()
    (library_dir / "directory.ctk" / "ignored.ctk").write_text("quit", encoding="utf-8")
    runtime.history = Mock()

    preload_libraries(runtime, "libraries")

    assert runtime.bindings["selected"] == "loaded"
    assert "named" in runtime.matcher_function_names()
    assert runtime._import_stack == []
    runtime.history.append.assert_not_called()


@pytest.mark.parametrize("explicit", [False, True])
def test_preload_default_directory_and_explicit_tilde(runtime, isolated_home: Path, explicit: bool) -> None:
    library_dir = isolated_home / ".ctk" / "lib"
    library_dir.mkdir(parents=True)
    (library_dir / "values.ctk").write_text("let answer = 42", encoding="utf-8")

    preload_libraries(runtime, "~/.ctk/lib" if explicit else None)

    assert runtime.bindings["answer"] == 42


def test_missing_default_directory_is_a_noop(runtime, isolated_home: Path) -> None:
    preload_libraries(runtime)
    assert runtime.bindings == {}
    assert not (isolated_home / ".ctk").exists()


@pytest.mark.parametrize("kind", ["missing", "file"])
def test_invalid_explicit_directory_is_an_error(runtime, kind: str) -> None:
    path = runtime.cwd / kind
    if kind == "file":
        path.write_text("", encoding="utf-8")
    with pytest.raises(EvaluationError, match="cannot read library directory"):
        preload_libraries(runtime, path)


def test_failed_preload_restores_library_bindings_and_stops_later_files(runtime) -> None:
    library_dir = runtime.cwd / "libraries"
    library_dir.mkdir()
    (library_dir / "10-invalid.ctk").write_text(
        "let added = 1\nlet invalid = $missing", encoding="utf-8",
    )
    (library_dir / "20-later.ctk").write_text("let later = true", encoding="utf-8")
    runtime.bindings["existing"] = 7

    with pytest.raises(EvaluationError, match=r"10-invalid.ctk:2:.*unknown variable: missing"):
        preload_libraries(runtime, library_dir)

    assert runtime.bindings == {"existing": 7}
    assert runtime._import_stack == []


class TerminalInput(io.StringIO):
    def isatty(self) -> bool:
        return True


def run_cli(monkeypatch: pytest.MonkeyPatch, *arguments: str, stdin: str | None = None) -> tuple[int, Mock]:
    client = Mock(spec=Client)
    client.compilation_database = None
    monkeypatch.setattr(app, "Client", lambda *_args, **_kwargs: client)
    monkeypatch.setattr(sys, "argv", ["ctk", *arguments])
    monkeypatch.setattr(sys, "stdin", TerminalInput() if stdin is None else io.StringIO(stdin))
    return asyncio.run(app._run(script_engine_default="compiled")), client


@pytest.mark.parametrize("engine", ["legacy", "tree", "compiled"])
@pytest.mark.parametrize("mode", ["execute", "script", "stdin"])
def test_cli_preloads_before_every_script_mode(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, isolated_home: Path,
    capsys: pytest.CaptureFixture[str], engine: str, mode: str,
) -> None:
    libraries = tmp_path / "custom libraries"
    libraries.mkdir()
    (libraries / "values.ctk").write_text("let label = $arg.label", encoding="utf-8")
    source = "print $label"
    script = tmp_path / "main.ctk"
    script.write_text(source, encoding="utf-8")
    arguments = ["--script-engine", engine, "--lib-dir", str(libraries)]
    arguments += {"execute": ["-e", source], "script": ["--script", str(script)], "stdin": []}[mode]
    arguments += ["label=preloaded"]
    monkeypatch.setattr(app, "create_session", Mock(side_effect=AssertionError("unexpected prompt")))

    code, client = run_cli(monkeypatch, *arguments, stdin=source if mode == "stdin" else None)

    assert code == 0
    assert capsys.readouterr().out.splitlines() == ["preloaded"]
    client.close.assert_called_once()


def test_cli_default_directory_is_loaded_and_override_replaces_it(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, isolated_home: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    default = isolated_home / ".ctk" / "lib"
    default.mkdir(parents=True)
    (default / "values.ctk").write_text('let label = "default"', encoding="utf-8")
    override = tmp_path / "override"
    override.mkdir()
    (override / "values.ctk").write_text('let label = "override"', encoding="utf-8")

    assert run_cli(monkeypatch, "-e", "print $label")[0] == 0
    assert capsys.readouterr().out.strip() == "default"
    assert run_cli(monkeypatch, "--lib-dir", "override", "-e", "print $label")[0] == 0
    assert capsys.readouterr().out.strip() == "override"


@pytest.mark.parametrize("engine", ["legacy", "tree", "compiled"])
@pytest.mark.parametrize("interactive", [False, True])
def test_cli_reports_preload_failure_before_input_or_script_effects(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, isolated_home: Path,
    capsys: pytest.CaptureFixture[str], engine: str, interactive: bool,
) -> None:
    libraries = tmp_path / "libraries"
    libraries.mkdir()
    (libraries / "invalid.ctk").write_text("quit", encoding="utf-8")
    arguments = ["--script-engine", engine, "--lib-dir", str(libraries)]
    if not interactive:
        arguments += ["-e", 'save [1] to "ran.json" as json']
    monkeypatch.setattr(app, "create_session", Mock(side_effect=AssertionError("unexpected prompt")))

    code, client = run_cli(monkeypatch, *arguments)

    assert code == 1
    output = capsys.readouterr().out
    assert "invalid.ctk:1:" in output and "libraries accept let definitions" in output
    assert "Traceback" not in output
    assert not (tmp_path / "ran.json").exists()
    client.close.assert_called_once()


@pytest.mark.parametrize("engine", ["legacy", "tree", "compiled"])
@pytest.mark.parametrize("ui", ["prompt", "workspace"])
def test_interactive_preloads_before_completion_and_input(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, isolated_home: Path,
    capsys: pytest.CaptureFixture[str], engine: str, ui: str,
) -> None:
    from clang_toolkit.cli import workspace

    libraries = tmp_path / "libraries"
    libraries.mkdir()
    (libraries / "matchers.ctk").write_text(
        'let label = "loaded"\nlet named(name) = functionDecl(hasName($name))', encoding="utf-8",
    )
    class QuerySession:
        closing = False

        async def events(self):
            if False:
                yield None

        async def aclose(self):
            self.closing = True

    class AsyncClient:
        def __init__(self, *_args, **_kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

        async def query_session(self):
            return QuerySession()

        async def wait_background(self):
            pass

        async def _session_info(self, _identity):
            raise AssertionError("unexpected lease refresh")

    class Prompt:
        def __init__(self, runtime):
            self.runtime = runtime
            self.commands = iter(["print $label", "quit"])

        async def prompt_async(self, _message):
            return next(self.commands)

    class Workspace:
        def __init__(self, session, *_args, **_kwargs):
            self.session = session

        def show_batch_progress(self, _progress):
            pass

        async def run(self):
            runtime = self.session.runtime
            outcome = await app._run_interactive_command(runtime.client, "print $label", runtime, None)
            assert outcome.success
            print(outcome.output)
            return 0

    def create_session(**kwargs):
        assert "label" in kwargs["references"]()
        assert "named" in kwargs["matcher_functions"]()
        return Prompt(kwargs["references"].__self__)

    monkeypatch.setattr(app, "AsyncClient", AsyncClient)
    monkeypatch.setattr(workspace, "WorkspaceConsole", Workspace)
    monkeypatch.setattr(app, "create_session", create_session)
    code, client = run_cli(monkeypatch, "--script-engine", engine, "--lib-dir", str(libraries), "--ui", ui)
    assert code == 0
    assert capsys.readouterr().out.strip() == "loaded"
    client.close.assert_called_once()
