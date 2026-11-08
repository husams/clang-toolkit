"""Differential tests for the standalone native CTK frontend."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

from lark import Token, Tree
import pytest

from clang_toolkit.cli.runtime.prototype.repl_language import parser


_RUNNER = Path(__file__).resolve().parents[2] / "build/jit/ctk-jit-runner"


def _tree(value: Tree | Token) -> list:
    if isinstance(value, Token):
        return [value.type, str(value)]
    return [str(value.data), *map(_tree, value.children)]


@pytest.mark.parametrize(
    "source",
    [
        "let g = {c:1, n:3}; let a = true; print g; print a",
        "let greeting = 'café 🪿'\nprint greeting",
        "let f(x, scale: s=2) = x * s; f(3, scale=4)",
        "if true do if false do print 0\nelse do print 1",
        "let tree = parse arg.file\n"
        'let rows = match functionDecl(isDefinition()).bind("f") in tree\n'
        "foreach row in rows do { print row.f.decl_name }",
        'match functionDecl(hasName("add")).bind("f") in "sample.cpp" do { print f }',
        'let inputs = files ["sample.cpp"]; batch part in $inputs size 1 do { len(part.inputs) }',
        "history save 'session.ctk'\nsession label 'analysis'",
        "session list\ncache status\nserver status",
        "let a = 1; a += 2; print a",
        "let x = [1,2,3]; print x[1:]",
        "let text = parse cpp`int x;\n`",
        "# ignored comment\nlet x = 1 // trailing comment\n",
    ],
)
def test_native_parser_uses_the_same_syntax_tree(source: str) -> None:
    if not _RUNNER.is_file():
        pytest.skip("standalone ctk-jit runner has not been built")
    expected = _tree(parser().parse(source))
    result = subprocess.run(
        [_RUNNER, "parse-ctk"],
        input=source,
        env={"PATH": "/nonexistent", "CTK_SERVER": "unix:///nonexistent/ctk.sock"},
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert json.loads(result.stdout) == expected


def test_native_submission_retains_bindings_and_compiled_code(tmp_path: Path) -> None:
    if not _RUNNER.is_file():
        pytest.skip("standalone ctk-jit runner has not been built")
    (tmp_path / "example.cpp").write_text(
        "int add(int a, int b) { return a + b; }\nint square(int x) { return x * x; }\n"
    )
    requests = [
        {
            "slot": 0,
            "source": (
                'let tree = parse arg.file; let rows = match functionDecl().bind("f") in tree; '
                "foreach row in rows do { print row.f.decl_name }"
            ),
        },
        {"slot": 1, "source": "let record = {c:1, n:3}; let valid = true; print record.c; print valid"},
        {"slot": 0, "source": "let ="},
        {"slot": 0},
        {"slot": 2, "source": 'match functionDecl(hasName("add")).bind("f") do { print f.decl_name }'},
        {"inspect": "outline"},
        {"inspect": "resources"},
        {"inspect": "status"},
    ]
    result = subprocess.run(
        [_RUNNER, "repl", "example.cpp", ""],
        cwd=tmp_path,
        input="".join(json.dumps(request) + "\n" for request in requests),
        env={
            "PATH": "/nonexistent",
            "CTK_SERVER": "unix:///nonexistent/ctk.sock",
            "CTK_JIT_STATE_DIR": str(tmp_path / "state"),
        },
        check=True,
        capture_output=True,
        text=True,
        timeout=25,
    )
    ready, match, literals, broken, repeat, callback, outline, resources, status = [
        json.loads(line) for line in result.stdout.splitlines()
    ]
    assert ready == {"ready": True, "protocol": 3}
    assert match["compiled"] and match["output"] == "add\nsquare\n"
    assert literals["compiled"] and literals["output"] == "1\ntrue\n"
    assert broken["error"] and not broken["compiled"]
    assert not repeat["compiled"] and repeat["output"] == match["output"]
    assert callback["compiled"] and callback["output"] == "add\n"
    assert set(outline["value"]) >= {"record", "rows", "tree", "valid"}
    assert set(resources["value"]) >= {"files", "sessions"}
    assert status["value"]["type"] == "ctk.match.v1.ServerStatusResponse"


def test_native_ftxui_workspace_uses_fresh_ctk_source(tmp_path: Path) -> None:
    import errno
    import fcntl
    import os
    import pty
    from select import select
    import struct
    import termios
    import time

    import pyte

    if not _RUNNER.is_file():
        pytest.skip("standalone ctk-jit runner has not been built")
    (tmp_path / "sample.cpp").write_text("int add(int a, int b) { return a + b; }\n")
    executable = tmp_path / "ctk-jit"
    executable.symlink_to(_RUNNER)
    history = tmp_path / "xdg/clang_tools/history.jsonl"
    master, slave = pty.openpty()
    width, height = 140, 30
    fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", height, width, 0, 0))
    screen = pyte.Screen(width, height)
    stream = pyte.ByteStream(screen)
    try:
        process = subprocess.Popen(
            [executable, "repl", "--ui", "--file", "sample.cpp"],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            cwd=tmp_path,
            env={
                "PATH": "/nonexistent",
                "PYTHONHOME": "/nonexistent",
                "TERM": "xterm-256color",
                "CTK_SERVER": "unix:///nonexistent/ctk.sock",
                "CTK_JIT_STATE_DIR": str(tmp_path / "native"),
                "XDG_STATE_HOME": str(tmp_path / "xdg"),
            },
        )
    finally:
        os.close(slave)

    def read_until(text: str) -> None:
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            if text in "\n".join(screen.display):
                return
            if select([master], [], [], 0.05)[0]:
                try:
                    data = os.read(master, 65536)
                except OSError as error:
                    if error.errno != errno.EIO:
                        raise
                    break
                if not data:
                    break
                stream.feed(data)
                if b"\x1b[6n" in data:
                    os.write(master, b"\x1b[1;1R")
        pytest.fail(f"workspace did not display {text!r}\n" + "\n".join(screen.display))

    def send(text: str) -> None:
        os.write(master, text.encode())

    try:
        read_until("Ready")
        send("match functionDe\t")
        read_until("Completions")
        read_until("functionDecl(")
        send("\r")
        read_until("match functionDecl()")
        send("\x03")
        draft = "let data = {c:1,n:3}\nprint data.c + data.n"
        send("\x1b[200~" + draft + "\x1b[201~\r")
        read_until("let data = {c:1,n:3}")
        send("\x1b[18~")
        read_until("$data = record (2)")
        send("\x1b[19~")
        read_until("No open files")
        send("\x1b[20~")
        read_until("residentMemoryBytes")
        send("\x1b[17~")  # F6 moves from the side pane to the editor.
        send("print data.\t")
        read_until("Completions")
        send("\r\r")
        read_until("ctk-jit> print data.c")
        match = 'match functionDecl(hasName("add")).bind("f") in "sample.cpp"'
        send(match + "\r")
        read_until("▸ match")
        send("\x1b[17~\r")
        read_until("sample.cpp:1")
        send("\r")
        read_until("int add(int a, int b)")
        send("\x1b[21~")
        deadline = time.monotonic() + 15
        while process.poll() is None and time.monotonic() < deadline:
            if select([master], [], [], 0.05)[0]:
                try:
                    os.read(master, 65536)
                except OSError as error:
                    if error.errno != errno.EIO:
                        raise
                    break
        assert process.wait(timeout=2) == 0
        commands = [json.loads(line)["command"] for line in history.read_text().splitlines()]
        assert commands == [draft, "print data.c", match]
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        os.close(master)
