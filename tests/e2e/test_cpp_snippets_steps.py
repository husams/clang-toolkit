"""Exercise temporary source, borrowed profiles and both console engines."""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from clang_toolkit import AsyncClient, Client
from tests.e2e.test_network_steps import RunningServer, _launch_server

pytestmark = pytest.mark.e2e
scenarios("cpp_snippets.feature")

CALL_QUERY = 'cxxMemberCallExpr(callee(cxxMethodDecl(hasName("add")))).bind("call")'
BODY = "TemplateType<MyTest> test;\ntest.add(MyTest{});\n"


@dataclass
class SnippetProject:
    server: RunningServer
    directory: Path
    named_source: Path


@given("an isolated snippet project with distinct compilation commands", target_fixture="snippet_project")
def snippet_project(
    tmp_path: Path, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch,
) -> SnippetProject:
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "storage"))
    server = _launch_server("unix", tmp_path, request)
    directory = tmp_path / "project"
    directory.mkdir()
    headers = directory / "include"
    headers.mkdir()
    (headers / "template_type.hpp").write_text(
        "#pragma once\n"
        "#ifndef BORROWED_SETTINGS\n#error missing borrowed settings\n#endif\n"
        "struct MyTest { int value = BORROWED_SETTINGS; };\n"
        "template<class T> struct TemplateType {\n"
        "  int add(T input) { return input.value; }\n"
        "};\n",
        encoding="utf-8",
    )
    first, second = directory / "z_first.cpp", directory / "a_second.cpp"
    for source in (first, second):
        source.write_text("int original_source;\n", encoding="utf-8")
    commands = [
        {"directory": str(directory), "file": str(source),
         "arguments": ["clang++", "-std=c++20", "-Iinclude", f"-DBORROWED_SETTINGS={value}",
                       "-c", str(source), "-o", f"{source.stem}.o"]}
        for source, value in ((first, 17), (second, 29))
    ]
    (directory / "compile_commands.json").write_text(json.dumps(commands), encoding="utf-8")
    return SnippetProject(server, directory, second)


@when("I parse a template snippet using the named source settings", target_fixture="snippet_evidence")
def named_settings(snippet_project: SnippetProject) -> dict[str, Any]:
    project = snippet_project
    with Client(project.server.endpoint) as client:
        with client.parse_cpp(
            BODY, file=project.named_source, working_directory=project.directory,
            includes=["template_type.hpp"],
        ) as tree:
            temporary = Path(tree.source_file)
            assert temporary.is_file() and temporary.suffix == ".cpp"
            assert "test.add(MyTest{})" in temporary.read_text(encoding="utf-8")
            with client.match_in(CALL_QUERY, tree) as calls:
                assert len(calls) == 1
            with client.match_in('integerLiteral(equals(29)).bind("value")', tree) as values:
                assert len(values) >= 1
            # A derived value must remain usable after releasing the root tree.
            retained = client.match_in('varDecl(hasName("test")).bind("test")', tree)
        assert temporary.is_file()
        assert len(retained) == 1
        with client.match_in('varDecl(hasName("test")).bind("same")', retained[0].binding("test")) as again:
            count = len(again)
        retained.close()
    return {"count": count, "original": project.named_source.read_text(encoding="utf-8")}


@then("the retained snippet exposes the concrete method call and its source")
def verify_named(snippet_evidence: dict[str, Any]) -> None:
    assert snippet_evidence == {"count": 1, "original": "int original_source;\n"}


@when("I asynchronously parse a snippet without selecting a settings file", target_fixture="first_command_count")
def first_settings(snippet_project: SnippetProject) -> int:
    async def run() -> int:
        async with AsyncClient(snippet_project.server.endpoint) as client:
            async with await client.parse_cpp(
                "static_assert(BORROWED_SETTINGS == 17);\n" + BODY,
                working_directory=snippet_project.directory, includes=["template_type.hpp"],
            ) as tree:
                async with await client.match_in(CALL_QUERY, tree) as calls:
                    return len(calls)
    return asyncio.run(run())


@then("the first compilation command supplies its defines and header paths")
def verify_first(first_command_count: int) -> None:
    assert first_command_count == 1


@when(parsers.parse("I run a template snippet through the {engine} console engine"), target_fixture="snippet_console")
def console(snippet_project: SnippetProject, engine: str) -> subprocess.CompletedProcess[str]:
    project = snippet_project
    options = {"file": str(project.named_source), "includes": ["template_type.hpp"]}
    source = (
        f"let tree = parse cpp`{BODY}` using {json.dumps(options)}\n"
        f"let calls = match {CALL_QUERY} in tree\n"
        "print calls.length\n"
    )
    return subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server", project.server.endpoint,
         "--script-engine", engine, "--execute", source],
        cwd=project.directory, env=dict(os.environ), text=True, capture_output=True,
        timeout=45, check=False,
    )


@then("the console reports the snippet member call")
def verify_console(snippet_console: subprocess.CompletedProcess[str]) -> None:
    assert snippet_console.returncode == 0, snippet_console.stdout + snippet_console.stderr
    assert snippet_console.stdout.strip() == "1"


@when("I analyze a template snippet through the native scripting service", target_fixture="native_snippet_count")
def native_script(snippet_project: SnippetProject) -> int:
    options = {"file": str(snippet_project.named_source), "includes": ["template_type.hpp"]}
    source = (
        f"let tree = parse cpp`{BODY}` using {json.dumps(options)};\n"
        f"let calls = match {CALL_QUERY} in tree; emit calls;"
    )
    with Client(snippet_project.server.endpoint) as client:
        response = client.run_script(source, working_directory=snippet_project.directory)
        return len(response.emissions[0].value.matches.rows)


@then("the native script reports the instantiated call")
def verify_native(native_snippet_count: int) -> None:
    assert native_snippet_count == 1


@when("I parse standalone statements without compilation options", target_fixture="standalone_count")
def standalone(snippet_project: SnippetProject, tmp_path: Path) -> int:
    directory = tmp_path / "standalone"
    directory.mkdir()
    with Client(snippet_project.server.endpoint) as client:
        with client.parse_cpp("int answer = 42;\n++answer;", working_directory=directory) as tree:
            with client.match_in('varDecl(hasName("answer")).bind("answer")', tree) as values:
                return len(values)


@then("their local variable is available for native matching")
def verify_standalone(standalone_count: int) -> None:
    assert standalone_count == 1
