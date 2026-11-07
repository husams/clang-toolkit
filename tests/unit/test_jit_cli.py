from __future__ import annotations

import json
import os
from pathlib import Path
from select import select
import subprocess
import sys
from zipfile import ZipFile

import pytest

from clang_toolkit.cli import jit
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
    assert not (jit_project / "cache").exists()


def test_repl_retains_target_and_bindings_after_source_edit(jit_project: Path) -> None:
    initial = """\
let tree = parse arg.file
let saved = match functionDecl(hasName("add")).bind("f") in tree
foreach row in saved do { print row.f.decl_name }
"""
    later = """\
let rows = match functionDecl(isDefinition(), isExpansionInMainFile()).bind("f") in tree
foreach row in rows do {
    print row.f.decl_name
}
let rows = match functionDecl(isConst()).bind("f") in tree
foreach row in rows do { print row.f.qualified_name }
foreach row in saved do { print row.f.decl_name }
:quit
"""
    with subprocess.Popen(
        [sys.executable, "-m", "clang_toolkit.cli.jit", "repl", *_TARGET],
        cwd=jit_project,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ) as process:
        assert process.stdin is not None and process.stdout is not None
        try:
            process.stdin.write(initial)
            process.stdin.flush()
            assert select([process.stdout], [], [], 30)[0], (
                "REPL did not produce a result"
            )
            assert process.stdout.readline() == "add\n"
            (jit_project / "example.cpp").write_text(
                "int replacement() { return 0; }\n"
            )
            output, errors = process.communicate(later, timeout=30)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()
    assert process.returncode == 1
    assert output == "add\nsquare\nadd\nsquare\nadd\n"
    assert "Incorrect type for arg 1" in errors
    assert not (jit_project / "cache").exists()


@pytest.mark.parametrize(
    ("matcher", "projection", "target_suffix", "expected"),
    [
        (
            "functionDecl(isDefinition(), isExpansionInMainFile(), unless(isImplicit()))",
            "decl_name",
            "",
            "add\nsquare\n",
        ),
        (
            'cxxMethodDecl(isConst(), hasName("::Example::get"))',
            "qualified_name",
            "struct Example { int get() const { return 1; } };\n",
            "Example::get\n",
        ),
        ('functionDecl(hasName("missing"))', "decl_name", "", ""),
    ],
)
def test_default_ir_matches_cold_cpp_jit(
    jit_project: Path, matcher: str, projection: str, target_suffix: str, expected: str
) -> None:
    with (jit_project / "example.cpp").open("a", encoding="utf-8") as target:
        target.write(target_suffix)
    (jit_project / "query.ctk").write_text(
        f"let tree = parse arg.file\n"
        f'let rows = match {matcher}.bind("f") in tree\n'
        f"foreach row in rows do {{ print row.f.{projection} }}\n",
        encoding="utf-8",
    )
    args = ("run", "query.ctk", *_TARGET, "--no-cache")
    assert _output(jit_project, *args) == expected
    assert _output(jit_project, *args, "--cpp-jit") == expected
    assert not (jit_project / "cache").exists()


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


@pytest.mark.parametrize(
    ("backend", "object_glob"), [((), "ir-obj-*"), (("--cpp-jit",), "obj-*")]
)
def test_bundle_matches_source_and_reuses_cached_object(
    jit_project: Path, backend: tuple[str, ...], object_glob: str
) -> None:
    (jit_project / "query.ctk").write_text(QUERY, encoding="utf-8")
    direct = _cli(jit_project, "run", "query.ctk", *_TARGET, "--no-cache", *backend)
    assert direct.returncode == 0, direct.stderr
    assert direct.stdout == "add\nsquare\n"
    _output(
        jit_project, "precompile", "query.ctk", "--output", "query.ctk-bundle", *backend
    )
    (cached,) = (jit_project / "cache").glob(object_glob + ".bundle")
    timestamp = cached.stat().st_mtime_ns

    _output(
        jit_project, "precompile", "query.ctk", "--output", "again.ctk-bundle", *backend
    )
    assert cached.stat().st_mtime_ns == timestamp
    assert (jit_project / "again.ctk-bundle").read_bytes() == cached.read_bytes()
    assert _output(jit_project, "run", "query.ctk", *_TARGET, *backend) == direct.stdout
    assert cached.stat().st_mtime_ns == timestamp

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


@pytest.mark.parametrize(
    ("backend", "object_glob"), [((), "ir-obj-*"), (("--cpp-jit",), "obj-*")]
)
def test_jit_run_reuses_and_refreshes_cached_bundle(
    jit_project: Path, backend: tuple[str, ...], object_glob: str
) -> None:
    query = jit_project / "query.ctk"
    query.write_text(QUERY, encoding="utf-8")
    args = ("run", "query.ctk", *_TARGET, *backend)
    cache = jit_project / "cache"
    assert _output(jit_project, *args) == "add\nsquare\n"
    (original,) = cache.glob(object_glob + ".bundle")
    timestamp = original.stat().st_mtime_ns
    assert _output(jit_project, *args) == "add\nsquare\n"
    assert original.stat().st_mtime_ns == timestamp

    with (jit_project / "example.cpp").open("a", encoding="utf-8") as target:
        target.write("int twice(int x) { return 2 * x; }\n")
    assert _output(jit_project, *args) == "add\nsquare\ntwice\n"
    assert original.stat().st_mtime_ns == timestamp
    assert set(cache.glob(object_glob + ".bundle")) == {original}

    query.write_text(
        QUERY.replace("isDefinition(),", 'hasName("add"), isDefinition(),'),
        encoding="utf-8",
    )
    assert _output(jit_project, *args) == "add\n"
    (updated,) = set(cache.glob(object_glob + ".bundle")) - {original}
    updated.write_bytes(b"corrupted")
    assert _output(jit_project, *args) == "add\n"
    with ZipFile(updated) as archive:
        assert archive.read("program.o")


def test_warm_ir_skips_lowering(
    jit_project: Path,
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    (jit_project / "query.ctk").write_text(QUERY, encoding="utf-8")
    args = ["run", "query.ctk", *_TARGET]
    assert _output(jit_project, *args) == "add\nsquare\n"

    def unexpected_lowering(source: str) -> str:
        pytest.fail("warm IR run lowered the script again")

    monkeypatch.chdir(jit_project)
    monkeypatch.setattr(jit, "lower_ir", unexpected_lowering)
    assert jit.main(args) == 0
    assert capfd.readouterr() == ("add\nsquare\n", "")


def test_jit_run_falls_back_when_cache_is_unavailable(jit_project: Path) -> None:
    (jit_project / "query.ctk").write_text(QUERY, encoding="utf-8")
    (jit_project / "cache").touch()
    assert _output(jit_project, "run", "query.ctk", *_TARGET) == "add\nsquare\n"


def test_warm_script_skips_lowering_and_preprocessing_until_inputs_change(
    jit_project: Path,
) -> None:
    (jit_project / "query.ctk").write_text(QUERY, encoding="utf-8")
    config = json.loads(subprocess.check_output([_RUNNER, "config"], timeout=15))
    sdk = Path(config["runtime_header"]).read_text(encoding="utf-8")
    sdk = sdk.replace("#pragma once", '#pragma once\n#include "prefix.hpp"').replace(
        "llvm::outs() << text", "llvm::outs() << CTK_TEST_PREFIX << text"
    )
    high = jit_project / "high" / "ctk" / "jit"
    low = jit_project / "low" / "ctk" / "jit"
    high.mkdir(parents=True)
    low.mkdir(parents=True)
    (low / "runtime.hpp").write_text(sdk, encoding="utf-8")
    prefix = low / "prefix.hpp"
    prefix.write_text('#define CTK_TEST_PREFIX "one "\n', encoding="utf-8")
    driver_log = jit_project / "driver.jsonl"
    driver = jit_project / "clang-wrapper"
    driver.write_text(
        f"""#!/usr/bin/env python3
import json
import os
import sys
with open({str(driver_log)!r}, "a") as log:
    log.write(json.dumps(sys.argv[1:]) + "\\n")
os.execv({config["compiler"]!r}, [{config["compiler"]!r}, *sys.argv[1:]])
""",
        encoding="utf-8",
    )
    driver.chmod(0o755)
    config["compiler"] = str(driver)
    config["flags"][:0] = ["-I", str(high.parents[1]), "-I", str(low.parents[1])]
    wrapper = jit_project / "runner"
    wrapper.write_text(
        f"""#!/usr/bin/env python3
import os
import sys
if sys.argv[1:] == ["config"]:
    print({json.dumps(config)!r})
else:
    os.execv({str(_RUNNER)!r}, [{str(_RUNNER)!r}, *sys.argv[1:]])
""",
        encoding="utf-8",
    )
    wrapper.chmod(0o755)
    args = ("run", "query.ctk", *_TARGET, "--cpp-jit", "--runner", str(wrapper))
    assert _output(jit_project, *args) == "one add\none square\n"
    driver_log.write_text("", encoding="utf-8")
    warm = subprocess.run(
        [
            sys.executable,
            "-c",
            """
from clang_toolkit.cli import jit
def unexpected_lowering(*args):
    raise AssertionError("warm run lowered the script")
jit.lower_script = unexpected_lowering
raise SystemExit(jit.main())
""",
            *args,
        ],
        cwd=jit_project,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    assert warm.returncode == 0, warm.stderr
    assert warm.stdout == "one add\none square\n"
    invocations = [json.loads(line) for line in driver_log.read_text().splitlines()]
    assert len(invocations) == 1 and "-###" in invocations[0]

    previous = prefix.stat()
    prefix.write_text('#define CTK_TEST_PREFIX "two "\n', encoding="utf-8")
    os.utime(prefix, ns=(previous.st_atime_ns, previous.st_mtime_ns))
    assert _output(jit_project, *args) == "two add\ntwo square\n"

    (high / "runtime.hpp").write_text(sdk, encoding="utf-8")
    (high / "prefix.hpp").write_text(
        '#define CTK_TEST_PREFIX "high "\n', encoding="utf-8"
    )
    assert _output(jit_project, *args) == "high add\nhigh square\n"

    with driver.open("a", encoding="utf-8") as stream:
        stream.write("\n# Changed toolchain\n")
    driver_log.write_text("", encoding="utf-8")
    assert _output(jit_project, *args) == "high add\nhigh square\n"
    invocations = [json.loads(line) for line in driver_log.read_text().splitlines()]
    assert any("-c" in invocation for invocation in invocations)


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
