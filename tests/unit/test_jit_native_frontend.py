"""Differential tests for the standalone native CTK frontend."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

from lark import Token, Tree
import pytest

from clang_toolkit.cli.jit_syntax import parser


_RUNNER = Path(os.environ.get(
    "CTK_TEST_JIT_RUNNER",
    str(Path(__file__).resolve().parents[2] / "build/jit-standalone/ctk-jit-runner"),
))


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


def test_native_nested_fields_match_python_workspace(tmp_path: Path) -> None:
    from unittest.mock import Mock

    from clang_toolkit.cli.jit_workspace import projected
    from clang_toolkit.cli.runtime import Runtime
    from clang_toolkit.client import Client

    if not _RUNNER.is_file():
        pytest.skip("standalone ctk-jit runner has not been built")
    (tmp_path / "sample.cpp").write_text("int add(int a, int b) { return a + b; }\n")
    references = (
        '$model["odd.key"].groups[1].details',
        "$model['odd.key'].groups[$last].details.flags",
        "$roots[0]",
        "$roots[0].f",
        "$roots[0].f.value.node",
        "$roots[0].f.value.node.function_decl.function.declarator.value.named",
        "$roots[0].f.value.node.function_decl.function.declarator.value.named.name",
    )
    presence = "$roots[0].f.value.node"
    unreadable = "$roots[0].f.value.node.function_decl.function.parameters[0]"
    requests = [
        {
            "slot": 0,
            "source": (
                "let model = {'odd.key': {groups: [{name:'old'}, "
                "{details:{name:'new', flags:[true]}}]}}; let last = 1; "
                'let roots = match functionDecl(hasName("add")).bind("f") in arg.file'
            ),
        },
        {"inspect": "outline", "expanded": ["$roots"]},
        *({"inspect": "complete_fields", "reference": ref} for ref in references),
        {"inspect": "complete_fields", "reference": presence, "presence": True},
        {"inspect": "complete_fields", "reference": unreadable},
        {"inspect": "complete_fields", "reference": "$model['odd.key'].groups.pop()"},
        {"inspect": "complete_fields", "reference": "$model['odd.key'].groups[5]"},
        {"slot": 1, "source": "print len(model['odd.key'].groups)"},
    ]
    result = subprocess.run(
        [_RUNNER, "repl", "sample.cpp", ""],
        cwd=tmp_path,
        input="".join(json.dumps(request) + "\n" for request in requests),
        env={
            "PATH": "/nonexistent",
            "PYTHONHOME": "/nonexistent",
            "CTK_SERVER": "unix:///nonexistent/ctk.sock",
            "CTK_JIT_STATE_DIR": str(tmp_path / "state"),
        },
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    ready, command, outline, *results = [json.loads(line) for line in result.stdout.splitlines()]
    assert ready["ready"] and command["compiled"] and not command["error"]
    client = Mock(spec=Client)
    runtime = Runtime(client, cwd=tmp_path, environment={})
    runtime.bindings.update(
        model={"odd.key": {"groups": [{"name": "old"}, {"details": {"name": "new", "flags": [True]}}]}},
        last=1,
        roots=[projected(row) for row in outline["value"]["roots"]["data"]],
    )
    try:
        for reference, reply in zip(references, results[:len(references)], strict=True):
            expected = {
                (item.name, item.kind == "method")
                for item in runtime.completion_suggestions(reference)
            }
            assert expected, reference
            assert {(item["name"], item["method"]) for item in reply["value"]} == expected, reference
        assert {item["name"] for item in results[-5]["value"]} == set(
            runtime.completion_presence_fields(presence)
        )
        assert not runtime.completion_suggestions(unreadable)
        assert all(reply["value"] == [] for reply in results[-4:-1])
        assert results[-1]["output"] == "2\n"
        assert client.mock_calls == []
    finally:
        runtime.close()


def test_native_bulk_close_releases_file_leases_and_cursors(tmp_path: Path) -> None:
    if not _RUNNER.is_file():
        pytest.skip("standalone ctk-jit runner has not been built")
    (tmp_path / "sample.cpp").write_text("int add(int a, int b) { return a + b; }\n")
    source = """\
let lease = file open "sample.cpp"
let cursor = cursor open "sample.cpp" functionDecl(hasName("add")).bind("f")
let closed = file close all
print closed.released_leases
print closed.closed_cursors
print len(closed.remaining)
"""
    result = subprocess.run(
        [_RUNNER, "repl", "sample.cpp", ""],
        cwd=tmp_path,
        input=json.dumps({"slot": 0, "source": source}) + "\n",
        env={
            "PATH": "/nonexistent",
            "CTK_SERVER": "unix:///nonexistent/ctk.sock",
            "CTK_JIT_STATE_DIR": str(tmp_path / "state"),
        },
        check=True,
        capture_output=True,
        text=True,
        timeout=20,
    )
    ready, reply = map(json.loads, result.stdout.splitlines())
    assert ready["ready"] and reply["compiled"] and not reply["error"]
    assert reply["output"] == "1\n1\n0\n"


def test_native_ftxui_workspace_uses_fresh_ctk_source(tmp_path: Path) -> None:
    import errno
    import fcntl
    import os
    import pty
    from select import select
    import signal
    import struct
    import termios
    import time

    import pyte

    if not _RUNNER.is_file():
        pytest.skip("standalone ctk-jit runner has not been built")
    project = tmp_path / "project"
    project.mkdir()
    (project / "sample.cpp").write_text("int add(int a, int b) { return a + b; }\n")
    (project / "src").mkdir()
    (project / "src" / "inside.cpp").write_text("int inside;\n")
    (project / "src" / "space {name}.cpp").write_text("int spaced;\n")
    (project / ".hidden").touch()
    executable = tmp_path / "ctk-jit"
    executable.symlink_to(_RUNNER)
    history = tmp_path / "xdg/clang_tools/history.jsonl"
    master, slave = pty.openpty()
    width, height = 156, 30
    fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", height, width, 0, 0))
    screen = pyte.Screen(width, height)
    stream = pyte.ByteStream(screen)
    try:
        process = subprocess.Popen(
            [executable, "repl", "--ui", "--file", "sample.cpp"],
            stdin=slave,
            stdout=slave,
            stderr=slave,
            cwd=project,
            env={
                "PATH": "/nonexistent",
                "PYTHONHOME": "/nonexistent",
                "TERM": "xterm-256color",
                "CTK_SERVER": "unix:///nonexistent/ctk.sock",
                "CTK_STORAGE_ROOT": str(tmp_path / "server-store"),
                "CTK_JIT_STATE_DIR": str(tmp_path / "native"),
                "XDG_STATE_HOME": str(tmp_path / "xdg"),
            },
        )
    finally:
        os.close(slave)

    def read_until(
        text: str, *, row: int | None = None, absent: str = "",
        cursor: tuple[int, int] | None = None,
    ) -> None:
        deadline = time.monotonic() + 12
        while time.monotonic() < deadline:
            visible = "\n".join(screen.display)
            found = text in (visible if row is None else screen.display[row])
            cursor_matches = cursor is None or (
                not screen.cursor.hidden and (screen.cursor.x, screen.cursor.y) == cursor
            )
            if found and (not absent or absent not in visible) and cursor_matches:
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
        read_until("Command help · F4")
        read_until("Script · 1 line · Ctrl+J run", cursor=(7, height - 2))
        editor_row = next(
            i for i, line in enumerate(screen.display) if line.startswith(" Script ·")
        )
        assert "CTK console | Actions [F2]" in screen.display[0]
        assert screen.display[1].startswith("CTK console")
        assert editor_row == height - 3
        assert screen.display[editor_row + 1].startswith("   1 │ ")
        assert "Input 1:1 | Follow" in screen.display[-1]

        send("\x1bOP")  # F1 writes shortcuts into results.
        read_until("Workspace shortcuts")
        send("\x1bOQ")  # F2 opens Actions at the left edge.
        read_until("Actions · scroll or use arrows")
        assert screen.display[1].index("Actions ·") < 4
        send("\r")  # The first action opens local files.
        read_until("Local files [×]")
        assert any("Local files" in row[:30] and "Command help" in row[100:]
                   for row in screen.display)
        assert not any(".hidden" in row for row in screen.display)
        read_until("▸ src")
        send("\r\x1b[B\r")  # Expand a folder, select a file, and prepare parse.
        read_until('│ parse "')
        read_until('inside.cpp"')
        send("\x03\x1bOR")  # Clear the prepared draft, then close the file pane.
        read_until("Draft cleared")
        send("\x1bOS")  # F4 closes the default help pane.
        send("\x1bOS")  # F4 reopens it with keyboard focus.
        read_until("Command help · F4")
        send("\x1b[17~")  # F6 from the right pane returns to the editor.

        send("parse\t")
        read_until("sample.cpp  file")
        send("\x03")
        send("parse sr\t")
        read_until("src/  directory")
        send("\r\t")
        read_until("inside.cpp  file")
        send("\r")
        read_until("parse 'src/inside.cpp'", row=-2)
        send("\x03")

        for prefix, candidate, completed in (
            ('let tree = parse "src/sp', "space {name}.cpp  file",
             "let tree = parse 'src/space {name}.cpp'"),
            ('match functionDecl() in "sam', "sample.cpp  file",
             'match functionDecl() in "sample.cpp"'),
            ("cfg in sam", "sample.cpp  file", "cfg in 'sample.cpp'"),
            ("callgraph sam", "sample.cpp  file", "callgraph 'sample.cpp'"),
            ("traverse sam", "sample.cpp  file", "traverse 'sample.cpp'"),
            ('script "emit 1;" in sam', "sample.cpp  file",
             """script "emit 1;" in 'sample.cpp'"""),
            ("file open sam", "sample.cpp  file", "file open 'sample.cpp'"),
            ("cursor open sam", "sample.cpp  file", "cursor open 'sample.cpp'"),
            ("session add sam", "sample.cpp  file", "session add 'sample.cpp'"),
            ("read sam", "sample.cpp  file", "read 'sample.cpp'"),
            ("load sam", "sample.cpp  file", "load 'sample.cpp'"),
            ("import sam", "sample.cpp  file", "import 'sample.cpp'"),
            ("history save sam", "sample.cpp  file", "history save 'sample.cpp'"),
            ("save 1 to sam", "sample.cpp  file", "save 1 to 'sample.cpp'"),
            ("print 1 to sam", "sample.cpp  file", "print 1 to 'sample.cpp'"),
            ("set output to sam", "sample.cpp  file", "set output to 'sample.cpp'"),
            ("set compile_commands sam", "sample.cpp  file",
             "set compile_commands 'sample.cpp'"),
            ("let paths = files sr", "src/  directory", "let paths = files 'src/'"),
            ("files [\"src/ins", "inside.cpp  file", 'files ["src/inside.cpp"]'),
            ("glob(\"src/ins", "inside.cpp  file", 'glob("src/inside.cpp")'),
            ("set cache_dir to s", "src/  directory", "set cache_dir to 'src/'"),
            ("index start s", "src/  directory", "index start 'src/'"),
            ('index lookup "usr" in s', "src/  directory",
             """index lookup "usr" in 'src/'"""),
        ):
            send(prefix + "\t")
            directory_only = prefix in {
                "set cache_dir to s", "index start s", 'index lookup "usr" in s'
            }
            read_until(candidate, absent="sample.cpp  file" if directory_only else "")
            send("\r")
            read_until(completed, row=-2)
            send("\x03")

        long_draft = "\n".join(f"# draft line {i}" for i in range(1, 21))
        send("\x1b[200~" + long_draft + "\x1b[201~")
        read_until("20 │ # draft line 20")
        assert not any(line.startswith("   1 │ # draft line 1") for line in screen.display)
        send("\x1b[A" * 19)
        read_until("   1 │ # draft line 1")
        send("\x03")
        send("# " + "x" * 145)
        read_until("     │ x")
        assert any(row.startswith("     │ x") for row in screen.display)
        send("\x03")

        send("let pair = [\r")
        read_until("3 │ ]")
        send("7\n")  # Ctrl+J runs even before the closing bracket.
        read_until("2 │     7")
        send("print 'ctrl-j-run'\x01")  # Ctrl+A moves to the start of the draft.
        read_until("1 │ print 'ctrl-j-run'", row=-2, cursor=(7, height - 2))
        send("\n")
        read_until("\nctrl-j-run")

        send("let undo = (\x1f")  # Ctrl+_ removes the pair in one step.
        read_until("1 │ let undo = ", row=-2, absent="let undo = ()")
        send("\x03")

        send("let modified = 1\x1b[13;2u")
        read_until("Script · 2 lines")
        send("print modified\x1b[27;3;13~")
        read_until("Script · 3 lines")
        send("\x1b[13;5u")
        read_until("Script · 4 lines")
        send("\x1b\r")
        read_until("Script · 5 lines")
        send("\x03")

        send("match functionDe\t")
        read_until("Completions")
        read_until("functionDecl(")
        send("\r")
        read_until("match functionDecl()")
        send("\x03")
        draft = "let data = {c:1,n:3,outer:{items:[{nested_field:17}]}}\nprint data.c + data.n"
        send("\x1b[200~" + draft + "\x1b[201~")
        read_until("2 │ print data.c + data.n")
        assert any(line.startswith("   1 │ let data") for line in screen.display)
        send("\r")
        read_until("let data = {c:1,n:3,outer:")
        read_until("Script · 1 line · Ctrl+J run")
        send("\x1b[18~")
        read_until("$data = record (3)")
        send("\x1b[19~")
        read_until("Open files · file list [0]")
        send("\r")
        read_until("No open files")
        send("\x1b[20~")
        read_until("residentMemoryBytes")
        send("z")  # Unbound panel keys must not edit the draft.
        send("\x1b[17~")  # F6 moves from the side pane to the editor.
        read_until("1 │ ", row=-2, cursor=(7, height - 2))
        send("print data.\t")
        read_until("Completions")
        send("\r\r")
        read_until("1 │ print data.c")
        send("print $data.outer.items[0].nested_fild + 1")
        send("\x1b[D" * len("ld + 1") + "\t")
        read_until("Completions")
        read_until("nested_field")
        send("\r\x1b[F\r")
        read_until("1 │ print $data.outer.items[0].nested_field + 1")
        match_prefix = 'match functionDecl(hasName("add")).bind("f") in "sam'
        match = match_prefix + 'ple.cpp"'
        send(match_prefix + "\t")
        read_until("sample.cpp  file")
        send("\r\r")
        read_until("▸ match")
        send("\x1b[17~\r")
        read_until("sample.cpp:1")
        assert any(row.startswith("  sample.cpp:1") for row in screen.display)
        send("\x1b[B\r")
        read_until("Selected match")
        read_until("int add(int a, int b)")
        read_until("Match · 1:1")
        send("\t")
        send("\x1b")
        read_until("CTK console | Actions [F2]")
        send("\x12")
        read_until("Search results:")
        send("ctrl-j-run\r")
        read_until("Transcript match")
        send("\x1b[1;5F")
        read_until(" | Follow")

        send("\x1b[20~")  # Close runtime details before resizing.
        read_until("Session open |", absent="Local runtime · F9")
        narrow_width = 64
        fcntl.ioctl(
            master, termios.TIOCSWINSZ, struct.pack("HHHH", height, narrow_width, 0, 0)
        )
        screen.resize(lines=height, columns=narrow_width)
        os.kill(process.pid, signal.SIGWINCH)
        send("\x1bOR")
        read_until("Local files [×]")
        read_until("   1 │ ", row=-2)
        send("\x1bOS")
        read_until("Command help · F4")
        send("\x1b")
        read_until("Local files [×]", absent="Command help · F4")
        # Use the explicit file toggle to exercise the overlay without depending
        # on the terminal's timeout for a second standalone Escape.
        send("\x1bOR")
        send("print 'narrow-ok'\r")
        read_until("\nnarrow-ok")
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
        assert not (tmp_path / "server-store").exists()
        assert (tmp_path / "native/ast-cache").is_dir()
        commands = [json.loads(line)["command"] for line in history.read_text().splitlines()]
        assert commands == [
            "let pair = [\n    7\n]",
            "print 'ctrl-j-run'",
            draft,
            "print data.c",
            "print $data.outer.items[0].nested_field + 1",
            match,
            "print 'narrow-ok'",
        ]
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
        os.close(master)
