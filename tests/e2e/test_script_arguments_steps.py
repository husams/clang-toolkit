"""Run parameterized scripts through the CLI and native query server."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.e2e.test_network_steps import RunningServer, _launch_server

pytestmark = pytest.mark.e2e
scenarios("script_arguments.feature")


@dataclass
class ScriptFixture:
    server: RunningServer
    directory: Path
    source: Path
    script: Path
    output: Path


@given("a private server and a parameterized script fixture", target_fixture="script_fixture")
def script_fixture(
    tmp_path: Path, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch,
) -> ScriptFixture:
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "native-storage"))
    server = _launch_server("unix", tmp_path, request)
    source = tmp_path / "functions.cc"
    source.write_text("int target() { return 7; }\nint other() { return 8; }\n", encoding="utf-8")
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "lib.ctk").write_text(
        'let named(name) = functionDecl(hasName($name)).bind("f")\n', encoding="utf-8",
    )
    script = scripts / "analysis script.ctk"
    script.write_text("\n".join([
        'import "lib.ctk"',
        "let tree = parse $arg.path",
        "let rows = match named($arg.name) in $tree",
        "print $rows[0].f.decl_name",
        'print "ARG=${arg.x}|COUNT=${arg.count}|EMPTY=${arg.empty}|MESSAGE=${arg.message}"',
        "save [$arg.x, $arg.count, $arg.empty, $arg.message] to $arg.output as json",
    ]), encoding="utf-8")
    return ScriptFixture(server, scripts, source, script, tmp_path / "arguments.json")


@when(parsers.parse("I run the parameterized script using {mode} input"), target_fixture="script_result")
def run_script(script_fixture: ScriptFixture, mode: str) -> subprocess.CompletedProcess[str]:
    fixture = script_fixture
    source = fixture.script.read_text(encoding="utf-8")
    arguments = {
        "positional": [str(fixture.script)],
        "explicit": ["--script", str(fixture.script)],
        "inline": ["--execute", source],
        "stdin": [],
    }[mode]
    values = [
        f"path={fixture.source}", "name=target", "x=gggg", "count=002", "empty=",
        "message=hello world", f"output={fixture.output}",
    ]
    return subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server", fixture.server.endpoint,
         "-c", str(fixture.server.config), *arguments, *values],
        input=source if mode == "stdin" else "",
        cwd=fixture.directory,
        env=dict(os.environ, XDG_STATE_HOME=str(fixture.directory / "state")),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=45,
        check=False,
    )


@then("its arguments select native matches and preserve literal values without a prompt")
def verify_script(
    script_fixture: ScriptFixture, script_result: subprocess.CompletedProcess[str],
) -> None:
    assert script_result.returncode == 0, script_result.stdout + script_result.stderr
    assert script_result.stdout.splitlines() == [
        "target", "ARG=gggg|COUNT=002|EMPTY=|MESSAGE=hello world",
    ]
    assert script_result.stderr == ""
    assert json.loads(script_fixture.output.read_text(encoding="utf-8")) == [
        "gggg", "002", "", "hello world",
    ]
    assert not (script_fixture.directory / "state").exists()
    assert script_fixture.server.process.poll() is None
