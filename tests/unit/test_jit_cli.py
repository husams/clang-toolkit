from __future__ import annotations

import json
from pathlib import Path
import platform
import subprocess
import sys
from zipfile import ZipFile

import pytest

from clang_toolkit.cli.jit import lower_script


QUERY = """\
let tree = parse arg.file
let rows = match functionDecl(isDefinition(), isExpansionInMainFile(), unless(isImplicit())).bind("f") in tree
foreach row in rows do {
    print row.f.decl_name
}
"""
_RUNNER = Path(__file__).resolve().parents[2] / "build/jit/ctk-jit-runner"


def test_jit_lowers_to_typed_matcher_and_native_projection() -> None:
    source = QUERY.replace("isDefinition(),", 'hasName("add"), isDefinition(),')
    source = source.replace("decl_name", "qualified_name")
    cpp = lower_script(source, Path("query.ctk"))
    assert (
        'functionDecl(hasName("add"), isDefinition(), isExpansionInMainFile(), unless(isImplicit())).bind("f")'
        in cpp
    )
    assert 'getNodeAs<clang::FunctionDecl>("f")' in cpp
    assert "getQualifiedNameAsString()" in cpp
    assert '#line 2 "query.ctk"' in cpp


@pytest.mark.parametrize(
    ("before", "after", "message"),
    [
        ("arg.file", '"other.cpp"', "expected parse arg.file"),
        ("in tree", "in rows", "expected match"),
        ("in rows do", "in tree do", "expected foreach over rows"),
        ("row.f.decl_name", "row.root.decl_name", "expected a bound declaration"),
        ("isDefinition()", "hasBody(compoundStmt())", "unsupported matcher predicate"),
    ],
)
def test_jit_reports_unsupported_script_forms(
    before: str, after: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        lower_script(QUERY.replace(before, after), Path("query.ctk"))


@pytest.fixture
def jit_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    if not _RUNNER.is_file():
        pytest.skip("standalone ctk-jit runner has not been built")
    monkeypatch.setenv("CTK_JIT_CACHE_DIR", str(tmp_path / "cache"))
    (tmp_path / "include").mkdir()
    (tmp_path / "include" / "helper.hpp").write_text(
        "inline int from_header() { return 1; }\n", encoding="utf-8"
    )
    (tmp_path / "example.cpp").write_text(
        """\
#include "helper.hpp"
#include <stddef.h>
#if !defined(ENABLE_ADD)
#error Missing project compile flag
#endif
int add(int a, int b) { return a + b; }
int square(int x) { return x * x; }
int declared_only(int x);
""",
        encoding="utf-8",
    )
    command = [
        "clang++",
        "-std=c++20",
        "-Iinclude",
        "-DENABLE_ADD",
        "-c",
        "example.cpp",
    ]
    (tmp_path / "compile_commands.json").write_text(
        json.dumps(
            [{"directory": str(tmp_path), "arguments": command, "file": "example.cpp"}]
        ),
        encoding="utf-8",
    )
    return tmp_path


def _run_jit(
    project: Path, script: str, suffix: str = ".ctk"
) -> subprocess.CompletedProcess[str]:
    filename = "query" + suffix
    (project / filename).write_text(script, encoding="utf-8")
    return _cli(project, "run", filename, *_TARGET, "--no-cache")


_TARGET = ("--file", "example.cpp", "--compdb", ".")


def _cli(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.jit", *args],
        cwd=project,
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )


def _output(project: Path, *args: str) -> str:
    result = _cli(project, *args)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    return result.stdout


def test_jit_runs_ctk_with_project_compile_flags(jit_project: Path) -> None:
    result = _run_jit(jit_project, QUERY)
    assert result.returncode == 0, result.stderr
    assert result.stdout == "add\nsquare\n"
    assert result.stderr == ""


def test_jit_can_execute_a_custom_native_matcher(jit_project: Path) -> None:
    (jit_project / "filter.hpp").write_text(
        """\
namespace clang::ast_matchers {
AST_MATCHER(FunctionDecl, hasTwoParameters) { return Node.getNumParams() == 2; }
}
""",
        encoding="utf-8",
    )
    result = _run_jit(
        jit_project,
        """\
#include <ctk/jit/runtime.hpp>
#include "filter.hpp"
void run(ctk::jit::RunContext &ctx) {
  using namespace clang::ast_matchers;
  ctx.match(functionDecl(isDefinition(), hasTwoParameters()).bind("f"),
            [&](const MatchFinder::MatchResult &row) {
              ctx.emit_text(row.Nodes.getNodeAs<clang::FunctionDecl>("f")->getNameAsString());
            });
}
""",
        ".cpp",
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == "add\n"
    assert result.stderr == ""


def test_jit_fails_before_execution_on_invalid_target_flags(jit_project: Path) -> None:
    database = jit_project / "compile_commands.json"
    commands = json.loads(database.read_text(encoding="utf-8"))
    commands[0]["arguments"].insert(1, "-this-flag-does-not-exist")
    database.write_text(json.dumps(commands), encoding="utf-8")
    result = _run_jit(jit_project, QUERY)
    assert result.returncode == 1
    assert result.stdout == ""
    assert "could not parse target" in result.stderr


def test_bundle_matches_source_and_reuses_cached_object(jit_project: Path) -> None:
    direct = _run_jit(jit_project, QUERY)
    assert direct.returncode == 0, direct.stderr
    assert direct.stdout == "add\nsquare\n"
    _output(jit_project, "precompile", "query.ctk", "--output", "query.ctk-bundle")
    (cached,) = (jit_project / "cache").glob("obj-*.bundle")
    timestamp = cached.stat().st_mtime_ns

    _output(jit_project, "precompile", "query.ctk", "--output", "again.ctk-bundle")
    assert cached.stat().st_mtime_ns == timestamp
    assert (jit_project / "again.ctk-bundle").read_bytes() == cached.read_bytes()

    (jit_project / "query.ctk").unlink()
    assert (
        _output(jit_project, "run", "--bundle", "query.ctk-bundle", *_TARGET)
        == direct.stdout
    )

    with ZipFile(cached) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        obj = archive.read("program.o")
    for manifest_data, object_data, diagnostic in [
        (manifest, obj + b"bad", "object checksum mismatch"),
        (manifest | {"toolchain": "stale"}, obj, "different ctk-jit toolchain"),
    ]:
        with ZipFile(jit_project / "broken.ctk-bundle", "w") as archive:
            archive.writestr("manifest.json", json.dumps(manifest_data))
            archive.writestr("program.o", object_data)
        result = _cli(jit_project, "run", "--bundle", "broken.ctk-bundle", *_TARGET)
        assert result.returncode == 1
        assert result.stdout == ""
        assert diagnostic in result.stderr


def test_jit_reuses_and_repairs_cached_prelude(jit_project: Path) -> None:
    (jit_project / "query.ctk").write_text(QUERY, encoding="utf-8")
    args = ("run", "query.ctk", *_TARGET)
    assert _output(jit_project, *args) == "add\nsquare\n"
    config = json.loads(subprocess.check_output([_RUNNER, "config"], timeout=15))
    uses_prelude = (
        sys.platform == "darwin"
        and platform.machine() == "arm64"
        and int(config["llvm"].split(".")[0]) >= 22
    )
    preludes = list((jit_project / "cache").glob("pch-*.pch"))
    if not uses_prelude:
        assert not preludes
        return
    (prelude,) = preludes
    before = prelude.stat()
    assert _output(jit_project, *args) == "add\nsquare\n"
    assert prelude.stat().st_mtime_ns == before.st_mtime_ns
    prelude.write_bytes(b"corrupted")
    assert _output(jit_project, *args) == "add\nsquare\n"
    assert prelude.stat().st_size > len(b"corrupted")


def test_precompile_observes_changed_extension_headers(jit_project: Path) -> None:
    (jit_project / "query.cpp").write_text(
        '#include <ctk/jit/runtime.hpp>\n#include "label.hpp"\n'
        "void run(ctk::jit::RunContext &ctx) { ctx.emit_text(label); }\n",
        encoding="utf-8",
    )
    header = jit_project / "label.hpp"
    header.write_text('constexpr auto label = "before";\n', encoding="utf-8")
    _output(jit_project, "precompile", "query.cpp", "--output", "before.ctk-bundle")
    header.write_text('constexpr auto label = "after";\n', encoding="utf-8")
    _output(jit_project, "precompile", "query.cpp", "--output", "after.ctk-bundle")
    assert len(list((jit_project / "cache").glob("obj-*.bundle"))) == 2
    assert (
        _output(jit_project, "run", "--bundle", "before.ctk-bundle", *_TARGET)
        == "before\n"
    )
    assert (
        _output(jit_project, "run", "--bundle", "after.ctk-bundle", *_TARGET)
        == "after\n"
    )
