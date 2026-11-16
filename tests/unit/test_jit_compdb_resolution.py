"""ctk-jit resolves compilation databases like the server, for every command."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
import json
import os
from pathlib import Path
import platform
from select import select
import shlex
import subprocess
import time

import pytest


_RUNNER = Path(__file__).resolve().parents[2] / "build/jit-standalone/ctk-jit-runner"

# Each profile defines VALUE; the source declares a function named after it.
_SOURCE = """\
#if VALUE == 1
int from_one();
#elif VALUE == 2
int from_two();
#else
int from_none();
#endif
"""
_FUNCTIONS = (
    "let tree = parse arg.file\n"
    'let rows = match functionDecl(matchesName("from_")).bind("f") in tree\n'
    "foreach row in rows do { print row.f.decl_name }\n"
)
_SNIPPET = (
    "let tree = parse cpp`#if VALUE == 1\nint one = VALUE;\n#else\nint two = VALUE;\n#endif`\n"
    'let rows = match varDecl(matchesName("one|two")).bind("v") in tree\n'
    "foreach row in rows do { print row.v.decl_name }\n"
)


def _environment(home: Path) -> dict[str, str]:
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(home),
        "XDG_CACHE_HOME": str(home / "cache"),
        "XDG_STATE_HOME": str(home / "state"),
        "CTK_SERVER": "unix:///nonexistent/ctk.sock",
        "CTK_JIT_STATE_DIR": str(home / "jit-state"),
        "CTK_JIT_CACHE_DIR": str(home / "jit-cache"),
    }


def _entry(directory: Path, file: str, *arguments: str, driver: str = "clang++") -> dict:
    return {
        "directory": str(directory),
        "file": file,
        "arguments": [driver, "-std=c++20", *arguments, "-c", file],
    }


def _database(path: Path, *entries: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(list(entries)))
    return path


@pytest.fixture
def jit(tmp_path: Path) -> Callable[..., subprocess.CompletedProcess[str]]:
    if not _RUNNER.is_file():
        pytest.skip("standalone ctk-jit runner has not been built")
    executable = tmp_path / "bin/ctk-jit"
    executable.parent.mkdir()
    executable.symlink_to(_RUNNER)
    (tmp_path / "home").mkdir()

    def invoke(cwd: Path, *args: str, script: str = _FUNCTIONS) -> subprocess.CompletedProcess[str]:
        query = tmp_path / "query.ctk"
        query.write_text(script)
        return subprocess.run(
            [executable, "run", query, "--no-cache", *args],
            cwd=cwd,
            env=_environment(tmp_path / "home"),
            capture_output=True,
            text=True,
            timeout=60,
        )

    return invoke


@contextmanager
def _repl(cwd: Path, home: Path, target: str = "", database: str = "") -> Iterator[Callable[[str], str]]:
    if not _RUNNER.is_file():
        pytest.skip("standalone ctk-jit runner has not been built")
    with subprocess.Popen(
        [_RUNNER, "repl", target, database],
        cwd=cwd,
        env=_environment(home),
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as process:
        assert process.stdin is not None and process.stdout is not None
        assert json.loads(process.stdout.readline())["ready"]
        slot = 0

        def submit(script: str) -> str:
            nonlocal slot
            process.stdin.write(json.dumps({"slot": slot, "source": script}) + "\n")
            process.stdin.flush()
            slot += 1
            assert select([process.stdout], [], [], 60)[0], script
            reply = json.loads(process.stdout.readline())
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
            submit.stderr = process.stderr.read() if process.stderr else ""  # type: ignore[attr-defined]


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / "src").mkdir(parents=True)
    (root / "src/sample.cpp").write_text(_SOURCE)
    (root / "src/sibling.cpp").write_text(_SOURCE)
    (tmp_path / "neutral").mkdir()
    return root


def _output(result: subprocess.CompletedProcess[str]) -> str:
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


def test_working_directory_database_precedes_the_source_database(
    tmp_path: Path, project: Path, jit: Callable[..., subprocess.CompletedProcess[str]]
) -> None:
    source = project / "src/sample.cpp"
    _database(project / "compile_commands.json", _entry(project, "src/sample.cpp", "-DVALUE=2"))
    work = tmp_path / "work"
    _database(work / "compile_commands.json", _entry(project, "src/sample.cpp", "-DVALUE=1"))
    assert _output(jit(work, "--file", str(source))) == "from_one"
    assert _output(jit(tmp_path / "neutral", "--file", str(source))) == "from_two"


@pytest.mark.parametrize("build", ["build", "build/dev", "build/release"])
def test_build_directories_are_discovered_from_the_source(
    tmp_path: Path, project: Path, jit: Callable[..., subprocess.CompletedProcess[str]], build: str
) -> None:
    _database(project / build / "compile_commands.json",
              _entry(project, "src/sample.cpp", "-DVALUE=2"))
    result = jit(tmp_path / "neutral", "--file", str(project / "src/sample.cpp"))
    assert _output(result) == "from_two"


def test_compile_flags_file_is_discovered_after_json_databases(
    tmp_path: Path, project: Path, jit: Callable[..., subprocess.CompletedProcess[str]]
) -> None:
    (project / "compile_flags.txt").write_text("-DVALUE=1\n")
    source = str(project / "src/sample.cpp")
    assert _output(jit(tmp_path / "neutral", "--file", source)) == "from_one"
    _database(project / "build/compile_commands.json",
              _entry(project, "src/sample.cpp", "-DVALUE=2"))
    assert _output(jit(tmp_path / "neutral", "--file", source)) == "from_two"


@pytest.mark.parametrize("explicit", [True, False])
def test_missing_entries_are_interpolated(
    tmp_path: Path, project: Path, jit: Callable[..., subprocess.CompletedProcess[str]],
    explicit: bool
) -> None:
    database = _database(project / "compile_commands.json",
                         _entry(project, "src/sample.cpp", "-DVALUE=2"))
    args = ["--file", str(project / "src/sibling.cpp")]
    if explicit:
        args += ["--compdb", str(database)]
    assert _output(jit(tmp_path / "neutral", *args)) == "from_two"


def test_the_first_of_several_entries_wins(
    tmp_path: Path, project: Path, jit: Callable[..., subprocess.CompletedProcess[str]]
) -> None:
    database = _database(project / "compile_commands.json",
                         _entry(project, "src/sample.cpp", "-DVALUE=1"),
                         _entry(project, "src/sample.cpp", "-DVALUE=2"))
    result = jit(tmp_path / "neutral", "--file", str(project / "src/sample.cpp"),
                 "--compdb", str(database))
    assert _output(result) == "from_one"


def test_missing_explicit_database_is_an_error(
    tmp_path: Path, project: Path, jit: Callable[..., subprocess.CompletedProcess[str]]
) -> None:
    result = jit(tmp_path / "neutral", "--file", str(project / "src/sample.cpp"),
                 "--compdb", str(project / "missing.json"))
    assert result.returncode == 1
    assert "compilation database not found" in result.stderr


@pytest.mark.parametrize("flag", ["--compdb", "--compile-commands"])
def test_command_line_database_outranks_settings(
    tmp_path: Path, project: Path, jit: Callable[..., subprocess.CompletedProcess[str]], flag: str
) -> None:
    one = _database(tmp_path / "one/compile_commands.json",
                    _entry(project, "src/sample.cpp", "-DVALUE=1"))
    two = _database(tmp_path / "two/compile_commands.json",
                    _entry(project, "src/sample.cpp", "-DVALUE=2"))
    (project / ".clang_tools.yaml").write_text(f"compile_commands: {json.dumps(str(two))}\n")
    source = str(project / "src/sample.cpp")
    assert _output(jit(project, "--file", source, flag, str(one))) == "from_one"
    assert _output(jit(project, "--file", source)) == "from_two"


def test_session_setting_outranks_the_command_line_database(
    tmp_path: Path, project: Path
) -> None:
    one = _database(tmp_path / "one/compile_commands.json",
                    _entry(project, "src/sample.cpp", "-DVALUE=1"))
    two = _database(tmp_path / "two/compile_commands.json",
                    _entry(project, "src/sample.cpp", "-DVALUE=2"))
    with _repl(project, tmp_path, str(project / "src/sample.cpp"), str(one)) as submit:
        assert submit(_FUNCTIONS) == "from_one"
        submit(f"set compile_commands {json.dumps(str(two))}")
        assert submit(_FUNCTIONS) == "from_two"
        submit("clear compile_commands")
        assert submit(_FUNCTIONS) == "from_one"


def test_parse_cpp_without_using_borrows_the_target_then_the_first_entry(
    tmp_path: Path, project: Path, jit: Callable[..., subprocess.CompletedProcess[str]]
) -> None:
    database = _database(project / "compile_commands.json",
                         _entry(project, "src/sibling.cpp", "-DVALUE=2"),
                         _entry(project, "src/sample.cpp", "-DVALUE=1"))
    neutral = tmp_path / "neutral"
    target = ("--file", str(project / "src/sample.cpp"))
    assert _output(jit(neutral, *target, "--compdb", str(database), script=_SNIPPET)) == "one"
    assert _output(jit(neutral, "--compdb", str(database), script=_SNIPPET)) == "two"
    # Discovery from the working directory supplies the first entry as well.
    assert _output(jit(project, script=_SNIPPET)) == "two"
    # Without a database the snippet keeps CTK's defaults.
    result = jit(neutral, script=_SNIPPET)
    assert result.returncode == 1
    assert "could not parse C++ snippet" in result.stderr
    # `using` still parses the snippet with the named file's command.
    using = _SNIPPET.replace("#endif`",
                             f"#endif` using {json.dumps(str(project / 'src/sample.cpp'))}")
    assert _output(jit(neutral, "--compdb", str(database), script=using)) == "one"


def _gcc_project(tmp_path: Path, project: Path) -> tuple[Path, Path]:
    compiler = json.loads(subprocess.check_output([_RUNNER, "config"], text=True))["compiler"]
    log = tmp_path / "gcc-invocations"
    gcc = tmp_path / "toolchain/g++-12"
    gcc.parent.mkdir()
    gcc.write_text(
        "#!/bin/sh\n"
        f"echo invoked >> {shlex.quote(str(log))}\n"
        f"exec {shlex.quote(compiler)} -Wno-unknown-warning-option \"$@\"\n"
    )
    gcc.chmod(0o700)
    database = _database(tmp_path / "gcc/compile_commands.json",
                         _entry(project, "src/sample.cpp", "-DVALUE=1", driver=str(gcc)))
    return database, log


def _invocations(log: Path) -> int:
    return len(log.read_text().splitlines()) if log.exists() else 0


def test_gcc_driver_runs_once_for_a_selected_database(tmp_path: Path, project: Path) -> None:
    database, log = _gcc_project(tmp_path, project)
    with _repl(project, tmp_path, str(project / "src/sample.cpp"), str(database)) as submit:
        assert submit(_FUNCTIONS) == "from_one"
        submit('set extra_args ["-DEXTRA=1"]')
        assert submit(_FUNCTIONS) == "from_one"
        submit("clear extra_args")
        # The unchanged command and source reuse this process's accepted check.
        assert submit(_FUNCTIONS) == "from_one"
    assert _invocations(log) == 2


def test_gcc_driver_runs_for_a_settings_database(
    tmp_path: Path, project: Path, jit: Callable[..., subprocess.CompletedProcess[str]]
) -> None:
    database, log = _gcc_project(tmp_path, project)
    (project / ".clang_tools.yaml").write_text(f"compile_commands: {json.dumps(str(database))}\n")
    assert _output(jit(project, "--file", str(project / "src/sample.cpp"))) == "from_one"
    assert _invocations(log) == 1


def test_gcc_driver_never_runs_for_a_discovered_database(
    tmp_path: Path, project: Path, jit: Callable[..., subprocess.CompletedProcess[str]]
) -> None:
    database, log = _gcc_project(tmp_path, project)
    result = jit(database.parent, "--file", str(project / "src/sample.cpp"))
    assert _output(result) == "from_one"
    assert _invocations(log) == 0


def test_file_open_keeps_the_target_implied_by_the_driver(
    tmp_path: Path, project: Path, jit: Callable[..., subprocess.CompletedProcess[str]]
) -> None:
    architecture = {"arm64": "aarch64", "AMD64": "x86_64"}.get(
        platform.machine(), platform.machine())
    foreign = "apple-darwin20" if platform.system() == "Linux" else "linux-gnu"
    macro = "__APPLE__" if platform.system() == "Linux" else "__linux__"
    (project / "src/target.cpp").write_text(
        f"#if defined({macro})\nint from_driver_target();\n#else\nint from_host();\n#endif\n")
    driver = tmp_path / f"toolchain/{architecture}-{foreign}-clang++"
    _database(project / "compile_commands.json",
              _entry(project, "src/target.cpp", driver=str(driver)))
    script = (
        f"let f = file open {json.dumps(str(project / 'src/target.cpp'))}\n"
        'let rows = match functionDecl(matchesName("from_")).bind("f") in f\n'
        "foreach row in rows do { print row.f.decl_name }\n"
    )
    assert _output(jit(project, script=script)) == "from_driver_target"
    assert _output(jit(project, "--file", str(project / "src/target.cpp"))) == "from_driver_target"


def _wait_for(read: Callable[[], str], expected: str) -> None:
    deadline = time.monotonic() + 60
    actual = ""
    while time.monotonic() < deadline:
        actual = read()
        if actual == expected:
            return
        time.sleep(0.2)
    pytest.fail(f"timed out waiting for {expected!r}, got {actual!r}")


@pytest.mark.parametrize("selection", ["directory", "json", "discovered"])
def test_index_accepts_a_database_directory_or_json_path(
    tmp_path: Path, project: Path, selection: str
) -> None:
    (project / "src/sample.cpp").write_text("int indexed_symbol() { return 1; }\n")
    database = _database(project / "build/compile_commands.json",
                         _entry(project, "src/sample.cpp"))
    argument = {"directory": str(database.parent), "json": str(database),
                "discovered": ""}[selection]
    work = tmp_path / "neutral"
    with _repl(work, tmp_path, "", argument) as submit:
        submit(f'let status = index start {json.dumps(str(project))} as "Demo"')
        _wait_for(lambda: submit('let s = index status "Demo"; print s.state.name'),
                  "INDEX_STATE_COMPLETE")
        found = submit('let f = index find "indexed_symbol" exact in "Demo"; print len(f.symbols)')
    assert found == "1"
    assert "compilation-database" not in submit.stderr  # type: ignore[attr-defined]
