from __future__ import annotations

from contextlib import contextmanager
from io import StringIO
import json
import os
from pathlib import Path
from select import select
import subprocess
import sys
import time
from tempfile import TemporaryDirectory
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
    monkeypatch.setenv("CTK_JIT_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "xdg-state"))
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
    ("options", "expected_workspace"),
    [
        ((), False),
        (("--ui",), True),
        (("--ui", "prompt"), False),
        (("--ui", "workspace"), True),
    ],
)
def test_repl_ui_selection(
    options: tuple[str, ...], expected_workspace: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    def run_repl(*_args: object, workspace: bool) -> int:
        assert workspace == expected_workspace
        return 0

    monkeypatch.setattr(jit, "run_repl", run_repl)
    assert jit.main(["repl", *options, "--runner", str(_RUNNER)]) == 0


def test_repl_reuses_compiled_commands_with_current_bindings(
    jit_project: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    first = 'let rows = match functionDecl(hasName("add")).bind("f") in tree'
    second = first.replace('"add"', '"square"')
    print_rows = "foreach row in rows do {\n    print row.f.decl_name\n}"
    commands = (
        "let tree = parse arg.file",
        print_rows,
        first,
        print_rows,
        second,
        print_rows,
        first,
        print_rows,
        ":quit",
    )
    monkeypatch.setattr(sys, "stdin", StringIO("\n".join(commands) + "\n"))
    lowered: set[str] = set()

    def lower_once(source: str) -> str | None:
        assert source not in lowered, f"cached command was parsed again: {source!r}"
        lowered.add(source)
        return jit.lower_repl(source)

    assert (
        jit.run_repl(
            _RUNNER,
            jit_project / "example.cpp",
            jit_project / "compile_commands.json",
            lower_once,
        )
        == 1
    )
    output = capsys.readouterr()
    assert output.out == "add\nsquare\nadd\n"
    assert output.err == "ctk-jit: LLVM IR query: undefined binding 'rows'\n"


def test_repl_literal_bindings_and_cached_field_projection(jit_project: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.jit", "repl", *_TARGET],
        cwd=jit_project,
        input="""\
let g  = {c:1, n:3}
let a = true
print g
print a
print g.n
let g = {n:7}
g.n
""",
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    record, *values = result.stdout.splitlines()
    assert json.loads(record) == {"c": 1, "n": 3}
    assert values == ["true", "3", "7"]


def test_repl_runs_compiled_language_and_native_matchers(jit_project: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.jit", "repl", *_TARGET],
        cwd=jit_project,
        input="""\
let config = {limit:3, enabled:true}; let alias = config
alias.limit += 1
let scale(x, n = config.limit) = x * n
print 3 | scale
print scale(3, n=2)
let head:tail = range(config.limit)
print tail[::-1] | json
print true or missing
let values = foreach value in tail do {
    if value == 2 then continue
    value + value.index
}
print values | json
let count = 0
while count < 10 do {
    count += 1
    if count == 3 then break
}
print count
print (missing on error { 7 })
let handled = if true then { on error { 17 }; on exit { print "clean" }; missing }
print handled
print [1,2,3] | map((x) = x * 2) | json
let total = { ([]) = 0; ((x:xs)) = x + total(xs) }
print total([1,2,3])
let ast = parse arg.file
let name = "add"
let matcher = functionDecl(hasName(name), parameterCountIs(2), hasAnyParameter(parmVarDecl().bind("p"))).bind("fn")
let rows = match matcher in ast
foreach row in rows do {
    print "$" + row.fn.decl_name
    print row.p is ParmVarDecl
}
print "limit is ${config.limit}"
let named(n) = functionDecl(hasName(n)).bind("f")
let named_rows = match named("square") in ast
print named_rows[0].f.decl_name
let snippet = parse cpp`int sample() { return 9; }` using {translation_unit:true}
let snippets = match functionDecl(hasName("sample")).bind("f") in snippet
snippet = ast
print snippets[0].f.decl_name
""",
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert result.stdout.splitlines() == [
        "12",
        "6",
        "[3,2,1]",
        "true",
        "[1,5]",
        "3",
        "7",
        "17",
        "[2,4,6]",
        "6",
        "$add",
        "true",
        "limit is 4",
        "square",
        "sample",
    ]


def test_repl_retains_native_callable_after_cache_slot_is_reused(
    jit_project: Path,
) -> None:
    commands = ["let f(x) = x * 2", "let saved = f"]
    commands.extend(f"let counter = {index}" for index in range(130))
    commands.extend(("let f(x) = x + 1", "print saved(21)", "print f(21)"))
    result = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.jit", "repl", *_TARGET],
        cwd=jit_project,
        input="\n".join(commands) + "\n",
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    assert result.stdout == "42\n22\n"


def test_general_ir_has_identical_cold_cached_and_bundle_output(
    jit_project: Path,
) -> None:
    filename = "general.ctk"
    (jit_project / filename).write_text(
        "let score(x) = x * x\n"
        "let scores = foreach x in range(4) do { score(x) }\n"
        "print {scores:scores, good:true} | json\n",
        encoding="utf-8",
    )
    expected = _output(jit_project, "run", filename, *_TARGET, "--no-cache")
    assert expected == '{"scores":[0,1,4,9],"good":true}\n'
    assert _output(jit_project, "run", filename, *_TARGET) == expected
    assert _output(jit_project, "run", filename, *_TARGET) == expected
    _output(jit_project, "precompile", filename, "-o", "general.ctkb")
    assert _output(jit_project, "run", "--bundle", "general.ctkb", *_TARGET) == expected


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
import time
from tempfile import TemporaryDirectory
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
import time
from tempfile import TemporaryDirectory
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


def _compiled_console_output(
    project: Path, script: str, endpoint: str | None = None
) -> str:
    from clang_toolkit.cli.app import dispatch_result
    from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
    from clang_toolkit.client import Client

    client = Client(endpoint) if endpoint else Client()
    runtime = PrototypeRuntime(client, cwd=project, environment={})
    try:
        result = dispatch_result(client, script, runtime)
        assert result.success, result.output
        return result.output
    finally:
        runtime.close()
        client.close()


def _native_repl_submission(project: Path, script: str) -> str:
    program = jit.lower_repl(script)
    assert program is not None
    result = subprocess.run(
        [_RUNNER, "repl", "example.cpp", "compile_commands.json"],
        cwd=project,
        input=json.dumps({"slot": 0, "ir": program}) + "\n",
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert result.returncode == 0, (result.stdout, result.stderr)
    ready, response = result.stdout.splitlines()
    assert json.loads(ready)["ready"]
    reply = json.loads(response)
    assert reply["compiled"], (reply["error"], result.stderr)
    assert not reply["error"], reply["error"]
    assert not result.stderr, result.stderr
    return reply["output"].removesuffix("\n")


@pytest.mark.parametrize(
    "script",
    [
        """\
let nums = range(6)
let count = len
print count(nums)
print nums | take(n=3) | drop(1) | json
print nums | first
print nums | last(n=2) | reverse | json
print [] | last | json
print [[0, 1], (2, 3)] | flatten | to_tuple | to_list | json
""",
        """\
print zip([1,2,3], ["a","b"], strict=false) | map((n,s) = "{n}{s}") | json
print zip_longest([1,2], ["a"], fill="?") | json
print ["x","y"] | enumerate(start=7) | json
print [2,3,4] | map((n) = n*n) | filter((n) = n > 5) | json
""",
        """\
let r = {z:2, a:3}
print r | keys | json
print r | values | json
print r | entries | json
print r | pick("a", "z") | json
print r | length
print [3,1,2,1.0,true,1,false] | unique | json
print [3,1,2,5] | unique_by((n) = n % 2) | json
print [4.5,1,4,2] | sort(reverse=true) | json
print [{n:3},{n:1}] | sort_by((v) = v.n) | json
""",
        """\
print "straße" | upper
print "ΣΕΛΗΝΗ" | lower
print "Straße" | casefold
print "HTTPServer status" | camel_case
print "HTTPServer status" | pascal_case
print "HTTPServer status" | snake_case
print "HTTPServer status" | kebab_case
print "  value  " | trim
print "  value  " | trim_start
print "  value  " | trim_end
print "aaa" | replace("a", "z", count=2)
print "prefix-title.cpp" | strip_prefix("prefix-") | strip_suffix(".cpp")
print "a.cpp" | starts_with("a")
print "a.cpp" | ends_with(".cpp")
print "a.cpp" | contains(".c")
print "a/b/c" | split_by("/") | join(separator=".")
""",
        """\
print {z:[1.0,1e-5,1e20], a:"é"} | json(indent=2)
print [1,2] | pretty
print [{n:2,label:"wide"},{n:10,label:"x"}] | table(["n","label"])
print (true,null,"a")
print [1,2,3]
print {z:1, a:2}
print "{{literal}} {3 + 4}"
""",
        """\
let vals = foreach x in [1,2] do {print x; x * 2}
print vals | json
if true then { print 2; 3 }
if true then { print 4 }
let f() = { print 5; 6 }
f()
""",
    ],
)
def test_native_language_matches_existing_compiled_console(
    jit_project: Path, script: str
) -> None:
    assert _native_repl_submission(jit_project, script) == _compiled_console_output(
        jit_project, script
    )


def test_native_document_commands_match_existing_compiled_console(
    jit_project: Path,
) -> None:
    (jit_project / "lines.txt").write_text("alpha\nbeta\n", encoding="utf-8")
    (jit_project / "values.yaml").write_text(
        "order:\n- 3\n- 1\nok: true\n", encoding="utf-8"
    )
    (jit_project / "rows.csv").write_text('name,qty\n"one,two",3\n', encoding="utf-8")
    script = """\
let words = read "lines.txt"
let data = read "values.yaml"
let rows = read "rows.csv"
save {data:data, rows:rows, words:words} to "result" as json
load "result.json" into value
print value | json
save [{label:"one,two", count:3, ok:true, rate:1.5}, {label:"two", count:4, ok:false, rate:2.5}] to "typed" as csv
load "typed.csv" into csv_values
print csv_values | json
save ["","x"] to "labels" as csv
load "labels" into labels
print labels | json
print value.data.order[0] to "message.txt"
print value.words[-1] to "message.txt" mode append
set output to "stream.txt" mode replace
print "first"
print "second"
clear output
print "done"
"""
    expected = _compiled_console_output(jit_project, script)
    files = ("result.json", "message.txt", "stream.txt", "typed.csv", "labels.csv")
    outputs = {name: (jit_project / name).read_bytes() for name in files}
    for name in files:
        (jit_project / name).unlink()
    assert _native_repl_submission(jit_project, script) == expected
    assert {name: (jit_project / name).read_bytes() for name in files} == outputs


@contextmanager
def _oracle_endpoint(jit_project: Path):
    import grpc

    root = Path(__file__).resolve().parents[2]
    server = Path(os.environ.get("CTK_SERVER", root / "build/dev/server/ctk-server"))
    if not server.is_file():
        pytest.skip("existing CTK oracle server has not been built")
    with TemporaryDirectory(prefix="ctk-oracle-", dir="/tmp") as directory:
        socket = Path(directory) / "s"
        config = Path(directory) / "server.yaml"
        config.write_text(
            f"network:\n  transport: unix\n  unix:\n    socket_path: {socket}\n"
        )
        process = subprocess.Popen(
            [server, "-c", config],
            cwd=jit_project,
            env={**os.environ, "CTK_STORAGE_ROOT": str(Path(directory) / "storage")},
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        endpoint = f"unix://{socket}"
        try:
            with grpc.insecure_channel(endpoint) as channel:
                grpc.channel_ready_future(channel).result(timeout=15)
            yield endpoint
        finally:
            if process.poll() is None:
                process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)



def _native_console_oracle(jit_project: Path, script: str) -> str:
    with _oracle_endpoint(jit_project) as endpoint:
        return _compiled_console_output(jit_project, script, endpoint)


@contextmanager
def _embedded_repl(jit_project: Path):
    with subprocess.Popen(
        [_RUNNER, "repl", "", "compile_commands.json"],
        cwd=jit_project,
        env={**os.environ, "CTK_SERVER": "unix:///tmp/ctk-jit-test-missing.sock"},
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as process:
        assert process.stdin is not None and process.stdout is not None
        assert json.loads(process.stdout.readline())["ready"]
        slots: dict[str, int] = {}

        def submit(script: str) -> str:
            if script in slots:
                request = {"slot": slots[script]}
            else:
                slots[script] = len(slots)
                request = {"slot": slots[script], "ir": jit.lower_repl(script)}
            process.stdin.write(json.dumps(request) + "\n")
            process.stdin.flush()
            assert select([process.stdout], [], [], 60)[0], script
            response = process.stdout.readline()
            assert response, process.stderr.read() if process.stderr else ""
            reply = json.loads(response)
            assert not reply["error"], reply["error"]
            return reply["output"].removesuffix("\n")

        try:
            yield submit
        finally:
            process.stdin.close()
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)


def _wait_for(read, expected):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        actual = read()
        if actual == expected:
            return
        time.sleep(0.1)
    pytest.fail(f"timed out waiting for {expected!r}, got {actual!r}")


def test_embedded_foreground_batch_matches_existing_console(jit_project: Path) -> None:
    script = """\
let inputs = files ["example.cpp"]
let report = batch part in $inputs size 1 jobs 1 progress off do {
  let rows = match functionDecl(hasName("add")) in part.inputs
  len(rows)
}
print report.status
print report.completed_groups
print report.completed_files
print report.cleanup_acknowledged
print report.results | json
let usage = resource status
print usage.explicit_file_leases
"""
    assert _native_repl_submission(jit_project, script) == _native_console_oracle(
        jit_project, script
    )


def test_embedded_durable_batch_matches_existing_console_and_survives_restart(
    jit_project: Path,
) -> None:
    from clang_toolkit.cli.app import dispatch_result
    from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
    from clang_toolkit.client import Client

    start = """\
let inputs = files ["example.cpp"]
let run = durable batch part in $inputs size 1 jobs 1 request "compare" do {
  let i = $part.index; $i;
}
print run.run_id
"""
    with _oracle_endpoint(jit_project) as endpoint:
        with Client(endpoint) as client:
            runtime = PrototypeRuntime(client, cwd=jit_project, environment={})
            try:
                started = dispatch_result(client, start.removesuffix("print run.run_id\n"), runtime)
                assert started.success, started.output
                run_id = runtime.bindings["run"].run_id
                _wait_for(lambda: client.batch_status(run_id).status, "completed")
                result = dispatch_result(
                    client, f'let id = "{run_id}"; let x = batch promote $id; print x | json', runtime
                )
                assert result.success, result.output
                expected = result.output
            finally:
                runtime.close()
    with _embedded_repl(jit_project) as submit:
        run_id = submit(start)
        assert submit(start) == run_id
        _wait_for(lambda: submit("let status = batch status $run; print status.status"), "completed")
        assert submit("let values = batch promote $status; print values | json") == expected
    with _embedded_repl(jit_project) as submit:
        assert submit(f'let id = "{run_id}"; let values = batch promote $id; print values | json') == expected


def test_embedded_project_index_matches_existing_console_and_survives_restart(
    jit_project: Path,
) -> None:
    from clang_toolkit._generated.index.v1 import index_service_pb2
    from clang_toolkit.client import Client

    # A small project avoids spending the test's budget indexing standard headers.
    (jit_project / "example.cpp").write_text("int add(int a, int b) { return a + b; }\n")
    search = """\
let found = index find "add" exact kind function in "Demo"
print len(found.symbols)
print found.symbols[0].qualified_name
print found.symbols[0].line
"""
    with _oracle_endpoint(jit_project) as endpoint:
        with Client(endpoint) as client:
            client.start_project_index(jit_project, project_name="Demo")
            _wait_for(lambda: client.project_index_status(jit_project).state,
                      index_service_pb2.INDEX_STATE_COMPLETE)
        expected = _compiled_console_output(jit_project, search, endpoint)
    with _embedded_repl(jit_project) as submit:
        assert submit('let status = index start "." as "Demo"; print status.project_name') == "Demo"
        _wait_for(lambda: submit('let state = index status "Demo"; print state.state.name'),
                  "INDEX_STATE_COMPLETE")
        assert submit(search) == expected
        assert submit('let status = index pause "Demo"; print status.state.name') == "INDEX_STATE_PAUSED"
        assert submit('let status = index resume "Demo"; print status.state.name') == "INDEX_STATE_QUEUED"
        assert submit('let status = index cancel "Demo"; print status.state.name') == "INDEX_STATE_CANCELLED"
        assert submit('let status = index rename "Demo" to "Renamed"; print status.project_name') == "Renamed"
    with _embedded_repl(jit_project) as submit:
        assert submit(search.replace('"Demo"', '"Renamed"')) == expected


def test_embedded_managed_session_matches_existing_console(jit_project: Path) -> None:
    commands = r"""
session start "functionDecl(hasName(\"add\")).bind(\"f\")"
session add "example.cpp"
session pause
session resume
session match
session close
"""
    result = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.jit", "repl"],
        cwd=jit_project,
        env={**os.environ, "CTK_SERVER": "unix:///tmp/ctk-jit-test-missing.sock"},
        input=commands,
        text=True,
        capture_output=True,
        timeout=45,
    )
    assert result.returncode == 0, result.stderr
    assert not result.stderr
    rows = [json.loads(line.split("] ", 1)[1]) for line in result.stdout.splitlines()
            if "] {" in line]
    (jit_project / "session.ctk").write_text(commands, encoding="utf-8")
    (jit_project / "empty-libraries").mkdir()
    with _oracle_endpoint(jit_project) as endpoint:
        existing = subprocess.run(
            [sys.executable, "-m", "clang_toolkit.cli.app", "--server", endpoint,
             "--script", "session.ctk", "--lib-dir", str(jit_project / "empty-libraries")],
            cwd=jit_project,
            text=True,
            capture_output=True,
            timeout=45,
        )
        assert existing.returncode == 0, existing.stderr + existing.stdout
        expected = [json.loads(line.split("] ", 1)[1])
                    for line in existing.stdout.splitlines() if "] {" in line]
    assert rows == expected
    assert [row["f"]["name"] for row in rows] == ["add"]
    assert "completed: 1 matches" in result.stdout


def test_native_scoped_matching_matches_existing_compiled_console(
    jit_project: Path,
) -> None:
    script = """\
let tree = parse cpp`int f(int n) {return n+1;} int g() {return f(1);}` using {translation_unit:true}
let functions = match functionDecl(hasName("g")).bind("f") in tree
let calls = match callExpr(callee(functionDecl().bind("callee"))) in functions[0].f scope subtree
print calls[0].callee.qualified_name
let same = match functionDecl().bind("f") in functions[0].f scope self
print same[0].f.decl_name
"""
    expected = _native_console_oracle(jit_project, script)
    assert _native_repl_submission(jit_project, script) == expected


def test_native_analysis_matches_existing_compiled_console(jit_project: Path) -> None:
    script = """\
let tree = parse cpp`int leaf(int n) {return n+1;}
int outer(int i) {int n = leaf(i); return n;}` using {translation_unit:true}
let rows = match functionDecl(hasName("outer")).bind("f") in tree
let f = rows[0].f
let vars = match varDecl(hasName("n")).bind("v") in f
let v = vars[0].v
let flow = variableflow v in f
print flow.analysis.variable
print len(flow.usages)
let cfgs = cfg in f
print len(cfgs.graphs)
print cfgs.graphs[0].function.qualified_name
let walked = traverse f depth 2
print len(walked.nodes)
let graph = callgraph in tree
print len(graph.nodes)
let matched = match functionDecl(hasName("outer")) in graph.function("outer")
print len(matched)
let body = step children compoundStmt() in f
let body_rows = match compoundStmt() in body scope self
print len(body_rows)
let parent = step parents functionDecl() in body
print parent.decl_name
let children = match compoundStmt() in f scope children
print len(children)
"""
    expected = _native_console_oracle(jit_project, script)
    assert _native_repl_submission(jit_project, script) == expected
    (jit_project / "analysis.ctk").write_text(script, encoding="utf-8")
    assert _output(jit_project, "run", "analysis.ctk", "--no-cache") == expected + "\n"
    _output(jit_project, "precompile", "analysis.ctk", "-o", "analysis.bundle")
    assert _output(jit_project, "run", "--bundle", "analysis.bundle") == expected + "\n"


def test_native_file_leases_and_cursors_match_existing_compiled_console(
    jit_project: Path,
) -> None:
    script = """\
let inputs = files ["example.cpp"]
print len(inputs)
foreach item in inputs do { print item.path == inputs.inputs[0].path }
let discovered_rows = match functionDecl(hasName("add")) in inputs
print len(discovered_rows)
let selected = inputs.inputs[0]
let opened = file open selected into $source
print opened.path == selected.path
let details = file info $source
print details.lease_id == opened.lease_id
let rows = match functionDecl(hasName("add")) in source
print len(rows)
let refreshed = file refresh $source
print refreshed.path == opened.path
let cursor = cursor open "example.cpp" functionDecl(hasName("add")).bind("fn")
print cursor.result_revision
print len(cursor.results)
let next = cursor continue "{cursor.session_id}" "fn" parmVarDecl() row 0 scope subtree revision 1
print next.result_revision
print len(next.results)
let state = resource status
print state.explicit_file_leases
let closed = file close all
print closed.released_leases
let inventory = file list
print len(inventory)
"""
    expected = _native_console_oracle(jit_project, script)
    assert _native_repl_submission(jit_project, script) == expected



def test_native_script_command_matches_existing_compiled_console(jit_project: Path) -> None:
    script = """\
let report = script "let n = 7; emit n;"
print report.emissions[0].value.scalar.integer
"""
    expected = _native_console_oracle(jit_project, script)
    assert _native_repl_submission(jit_project, script) == expected



def test_embedded_call_graph_methods_match_existing_console(jit_project: Path) -> None:
    script = """\
let tree = parse cpp`int leaf() { return 1; }
int recursive(int n) { return n ? recursive(n-1) : leaf(); }
int outer() { return recursive(2); }` using {translation_unit:true}
let graph = callgraph in tree
let path = $graph.shortest_path("outer", "leaf")
print len(path)
let route = $graph.shortest_route("outer", "leaf")
print len(route[0].call_sites)
let groups = $graph.grouped_calls()
print len(groups)
let recursion = $graph.recursive_components()
print len(recursion)
let outgoing = $graph.callees("outer", 1)
print len(outgoing.nodes)
let incoming = $graph.callers("leaf", 1)
print len(incoming.nodes)
"""
    expected = _native_console_oracle(jit_project, script)
    assert _native_repl_submission(jit_project, script) == expected



def test_embedded_settings_match_existing_console_and_persist(jit_project: Path) -> None:
    from clang_toolkit.cli.runtime.config import ConfigStore

    source = jit_project / "example.cpp"
    source.write_text(
        source.read_text() + "\n#ifdef LOCAL_FLAG\nint flagged() { return 1; }\n#endif\n"
    )
    script = """\
set compile_commands "compile_commands.json"
set extra_args ["-DLOCAL_FLAG"]
set traversal IgnoreUnlessSpelledInSource
set files to ["example.cpp"]
let rows = match functionDecl(hasName("flagged"))
print len(rows)
add extra_arg "-DOTHER_FLAG"
"""
    expected = _native_console_oracle(jit_project, script)
    settings = jit_project / ".clang_tools.yaml"
    settings.unlink()
    assert _native_repl_submission(jit_project, script) == expected == "1"
    config = ConfigStore(jit_project).effective
    assert config["extra_args"] == ["-DLOCAL_FLAG", "-DOTHER_FLAG"]
    assert config["traversal"] == "IgnoreUnlessSpelledInSource"
    assert config["files"] == ["example.cpp"]
    # Startup must apply the saved flags before the default target's first parse.
    source.write_text(
        source.read_text() + '\n#ifndef LOCAL_FLAG\n#error "missing saved profile"\n#endif\n'
    )
    assert _native_repl_submission(jit_project, 'let rows = match functionDecl(hasName("flagged")); print len(rows)') == "1"
    _native_repl_submission(jit_project, "clear extra_args")
    assert ConfigStore(jit_project).effective["extra_args"] == []

def test_embedded_semantic_snapshot_cross_runtime(jit_project: Path) -> None:
    save = """\
let tree = parse "example.cpp"
let rows = match functionDecl(hasName("add")).bind("f") in tree
let selected = rows[0].f
save selected to "binding" as proto
"""
    load = 'load "binding" into saved; print saved.name; print saved.value.location.line'
    _native_console_oracle(jit_project, save)
    expected = _compiled_console_output(jit_project, load)
    assert _native_repl_submission(jit_project, load) == expected
    (jit_project / "binding.proto").unlink()
    _native_repl_submission(jit_project, save)
    assert _compiled_console_output(jit_project, load) == expected

def test_native_typed_snapshot_interoperates_with_existing_console(jit_project: Path) -> None:
    save = 'save {names:["α", "β"], count:3, enabled:true, nested:[null, 3.5]} to "data" as proto'
    load = 'load "data" into saved; print saved | json'
    _compiled_console_output(jit_project, save)
    reference = (jit_project / "data.proto").read_bytes()
    assert json.loads(_native_repl_submission(jit_project, load)) == json.loads(
        _compiled_console_output(jit_project, load)
    )
    (jit_project / "data.proto").unlink()
    _native_repl_submission(jit_project, save)
    assert (jit_project / "data.proto").read_bytes() == reference

def test_native_runtime_imports_match_console_and_work_in_bundles(
    jit_project: Path,
) -> None:
    library = jit_project / "library"
    library.mkdir()
    (library / "base.ctk").write_text("let base(n) = n * 3\n")
    (library / "main.ctk").write_text('import "base.ctk"\nlet triple(n) = base(n)\n')
    # A failing import must undo definitions and in-place changes made earlier
    # in the library while preserving aliases held by the importing script.
    (library / "broken.ctk").write_text(
        "let added = push list, 99\nlet broken = 1 / 0\n"
    )
    script = """\
import "library/main.ctk"
let list = [4]
let alias = list
if true then { on error { print "recovered" }; import "library/broken.ctk" }
print alias | json
print added is defined
print triple(7)
print ctk("6")
print "done"; quit; print "unreachable"
"""
    (jit_project / "offline.ctk").write_text(script, encoding="utf-8")
    expected = _compiled_console_output(jit_project, script)
    assert (
        _output(jit_project, "run", "offline.ctk", "--no-cache").removesuffix("\n")
        == expected
    )
    _output(jit_project, "precompile", "offline.ctk", "-o", "offline.bundle")
    assert (
        _output(jit_project, "run", "--bundle", "offline.bundle").removesuffix("\n")
        == expected
    )
    (library / "base.ctk").write_text("let base(n) = n * 4\n")
    assert _output(jit_project, "run", "--bundle", "offline.bundle").removesuffix(
        "\n"
    ) == expected.replace("21", "28")


def test_native_script_accepts_named_arguments_without_a_translation_unit(
    jit_project: Path,
) -> None:
    (jit_project / "args.ctk").write_text('print "hello {arg.name}"\n')
    assert _output(jit_project, "run", "args.ctk", "--arg", "name=CTK") == "hello CTK\n"


def test_glob_files_and_match_blocks_match_existing_console(jit_project: Path) -> None:
    (jit_project / "include" / ".hidden.hpp").write_text("// hidden\n", encoding="utf-8")
    os.utime(jit_project / "example.cpp", (1700000000, 1700000000))
    script = """\
let sources = glob("*.cpp")
let file = sources[0]
print file.path
print file.absolute
print file.basename
print file.dirname
print file.parts | json
print file.size
print file.modified
print len(glob("**/*.hpp"))
let directories = glob("include/")
print directories[0].basename
let exact = match functionDecl(hasName("add"), isExpansionInFileMatching($file)) in $sources
print len(exact)
let f = "outer"
let captured = match functionDecl(isDefinition(), isExpansionInMainFile()).bind("f") in $sources do {
  let name = $f.value.node.qualified_name;
  print $name;
}
print captured
print f
match functionDecl(hasName("add")) in "*.cpp" do {
  print $root.name;
  print $root.decl_name;
  match parmVarDecl(hasName("b")).bind("p") in $root.source_file do {
    print $p.value.node.qualified_name;
  }
}
"""
    expected = _native_console_oracle(jit_project, script)
    assert expected.endswith("add\nsquare\nouter\nroot\nadd\nb")
    assert _native_repl_submission(jit_project, script) == expected
    assert _run_jit(jit_project, script).stdout == expected + "\n"
    _output(jit_project, "precompile", "query.ctk", "-o", "query.bundle")
    assert _output(jit_project, "run", "--bundle", "query.bundle", *_TARGET) == expected + "\n"


def test_repl_history_round_trips_with_existing_store(jit_project: Path) -> None:
    from clang_toolkit.cli.runtime.history import HistoryStore

    source = (
        'session label "native"\n'
        'let items = [\n  1, 2\n]\n'
        'print len(items)\n'
        'print len(items)\n'
        'history save "before.jsonl"\n'
        'history clear\n'
        'print "after"\n'
        'quit\n'
    )
    result = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.jit", "repl"],
        cwd=jit_project,
        input=source,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert (result.returncode, result.stderr, result.stdout) == (0, "", "2\n2\nafter\n")
    store = HistoryStore()
    assert store.read_commands() == ['print "after"', "quit"]
    assert store.path.stat().st_mode & 0o777 == 0o600
    exported = HistoryStore(jit_project / "before.jsonl")
    assert exported.read_commands() == [
        'session label "native"',
        "let items = [\n  1, 2\n]",
        "print len(items)",
        "print len(items)",
        'history save "before.jsonl"',
    ]
    entries = [json.loads(line) for line in exported.path.read_text().splitlines()]
    assert entries[0]["label"] is None
    assert {entry["label"] for entry in entries[1:]} == {"native"}
    assert len({entry["session_id"] for entry in entries}) == 1


def test_embedded_graph_expands_outside_current_graph(jit_project: Path) -> None:
    source = jit_project / "example.cpp"
    source.write_text(
        source.read_text()
        + "\nint another() { return square(2); }\nint caller() { return another(); }\n",
        encoding="utf-8",
    )
    script = """\
let tree = parse "example.cpp"
let roots = match functionDecl(hasName("add")).bind("f") in tree
let graph = callgraph in $roots[0].f depth 0 main-file true
let rows = match functionDecl(hasName("another")).bind("f") in tree
let outgoing = $graph.callees($rows[0].f, 1)
let incoming = $graph.callers($rows[0].f, 1)
print len(graph.nodes)
print len(outgoing.nodes)
print len(incoming.nodes)
let square_node = $outgoing.function("square")
let caller_node = $incoming.function("caller")
print square_node.function.qualified_name
print caller_node.function.qualified_name
"""
    expected = _native_console_oracle(jit_project, script)
    assert _native_repl_submission(jit_project, script) == expected


def test_embedded_collection_snapshots_cross_runtime(jit_project: Path) -> None:
    save = """\
let tree = parse "example.cpp"
let rows = match functionDecl(hasName("add")).bind("f") in tree
let params = rows[0].f.value.supported_scopes
save params to "params" as proto
save rows to "matches" as proto
"""
    load = """\
load "params" into params
print len(params)
"""
    read_rows = """\
load "matches" into rows
let function = rows[0].bindings.f.node.function_decl.function
print function.declarator.value.named.qualified_name
print rows[0].source_file
"""
    from clang_toolkit.cli.runtime.persistence import load as load_snapshot

    _native_console_oracle(jit_project, save)
    expected = _compiled_console_output(jit_project, load)
    row = load_snapshot(jit_project / "matches.proto").rows[0]
    assert _native_repl_submission(jit_project, load) == expected
    assert _native_repl_submission(jit_project, read_rows) == f"add\n{row['source_file']}"
    (jit_project / "matches.proto").unlink()
    (jit_project / "params.proto").unlink()
    _native_repl_submission(jit_project, save)
    assert _compiled_console_output(jit_project, load) == expected
    actual = load_snapshot(jit_project / "matches.proto").rows[0]
    assert actual["source_file"] == row["source_file"]
    assert actual["bindings"]["f"]["symbol_identity"] == row["bindings"]["f"]["symbol_identity"]

def test_standalone_workspace_reads_live_panels_and_frozen_previews(jit_project: Path) -> None:
    import asyncio

    from clang_toolkit.cli.jit_workspace import NativeWorkspace, command_outcome
    from clang_toolkit.cli.workspace_state import outline_snapshot

    env = {**os.environ, "CTK_SERVER": "unix:///tmp/ctk-jit-test-missing.sock"}
    with subprocess.Popen(
        [_RUNNER, "repl", "", "compile_commands.json"], cwd=jit_project,
        env=env, text=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    ) as process:
        assert process.stdin and process.stdout
        assert json.loads(process.stdout.readline())["ready"]

        progress = []

        def exchange(request):
            process.stdin.write(json.dumps(request) + "\n")
            process.stdin.flush()
            assert select([process.stdout], [], [], 30)[0], request
            while line := process.stdout.readline():
                reply = json.loads(line)
                if "progress" in reply:
                    progress.append(reply["progress"])
                    continue
                assert not reply.get("error"), reply
                return reply
            pytest.fail("native workspace closed before replying")

        def submit(slot, source):
            return exchange({"slot": slot, "ir": jit.lower_repl(source), "workspace": True})

        async def verify():
            workspace = NativeWorkspace(exchange, asyncio.Lock())
            reply = submit(0, 'let values = range(60); print "α"; print values; print "end"')
            parts = command_outcome(reply).parts
            assert [part.output for part in parts] == ["α", "", "end"]
            kind, result = parts[1].outline_value
            expanded = frozenset({"$List"})
            entries = await workspace.result(kind, result, expanded, {"$List": 1})
            assert entries == outline_snapshot({"List": list(range(60))}, expanded, {"$List": 1})
            submit(1, "set values[50] = 100")
            assert await workspace.result(kind, result, expanded, {"$List": 1}) == entries
            live = await workspace.outline(frozenset({"$values"}), {"$values": 1})
            assert any(item.label == "[50] = 100" for item in live)

            match = submit(2, 'match functionDecl(hasName("add")).bind("f") in "example.cpp"')
            kind, result = command_outcome(match).parts[0].outline_value
            matches = await workspace.result(kind, result, frozenset({"$Matches", "$Matches[0]"}), {})
            link = next(row.source for row in matches if row.source and row.label.startswith("f "))
            assert (Path(link.path).name, link.line) == ("example.cpp", 6)

            submit(3, 'file open "example.cpp" into $file')
            inventory = await workspace.resources(frozenset({":files", ":sessions"}))
            opened = next(item for item in inventory if item.label.startswith("example.cpp"))
            assert opened.commands[0][1].startswith('file close "')
            status = await workspace.status()
            assert status.cache.memory_available
            submit(4, opened.commands[0][1])
            empty = await workspace.resources(frozenset({":files"}))
            assert any(item.label == "No open files" for item in empty)

            submit(5, 'let cursor = cursor open "example.cpp" functionDecl(hasName("add")).bind("f")')
            retained = await workspace.resources(frozenset({":sessions"}))
            session = next(item for item in retained if item.identity.startswith("session:"))
            submit(6, session.commands[0][1])
            assert any(row.identity == "$attached1" for row in await workspace.outline(frozenset(), {}))
            submit(7, session.commands[1][1])

            batch = submit(8, 'let inputs = files ["example.cpp"]; batch part in $inputs size 1 do { len(part.inputs) }')
            assert progress[0]["state"] == "running" and progress[-1]["state"] == "completed"
            assert command_outcome(batch).parts[-1].outline_value[0] == "batch_statement"
            help_result = command_outcome(submit(9, "help loops")).parts[0]
            assert help_result.markdown.startswith("# Console loops")

        try:
            asyncio.run(verify())
        finally:
            process.stdin.close()
            process.wait(timeout=20)
        assert process.returncode == 0


def test_native_command_previews_match_existing_console(jit_project: Path) -> None:
    source = """\
session list
let fileset = files ["example.cpp"]
file list discovered in $fileset
script "let n = 7; emit n;"
let rows = match functionDecl(anyOf(hasName("add"), hasName("square"))).bind("f") in "example.cpp"
inspect rows[1].f
let inspection = inspect {a:1}
print len(inspection)
match functionDecl(hasName("add")).bind("f") in "example.cpp"
"""
    expected = _native_console_oracle(jit_project, source)
    assert _run_jit(jit_project, source).stdout == expected + "\n"
    _output(jit_project, "precompile", "query.ctk", "-o", "previews.bundle")
    assert _output(jit_project, "run", "--bundle", "previews.bundle", *_TARGET) == expected + "\n"
