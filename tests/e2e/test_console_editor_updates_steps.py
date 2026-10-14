"""Real TTY coverage for the active compiled console and offline picker."""

from __future__ import annotations

import errno
import fcntl
import os
import pty
import select
import struct
import subprocess
import sys
import termios
import time
from pathlib import Path

import pyte
import pytest
from pytest_bdd import given, scenarios, then, when

from clang_toolkit.cli.runtime.history import HistoryStore
from tests.e2e.test_network_steps import _launch_server

pytestmark = pytest.mark.e2e
scenarios("console_editor_updates.feature")


@given(
    "an isolated server for the compiled workspace editor",
    target_fixture="editor_server",
)
def editor_server(tmp_path, request, monkeypatch):
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "native-storage"))
    return _launch_server("unix", tmp_path, request)


@when(
    "I edit multiline matchers and request saved function help in a real terminal",
    target_fixture="editor_evidence",
)
def editor_evidence(editor_server, tmp_path):
    columns, rows = 160, 40
    (tmp_path / "empty-libraries").mkdir()
    master, slave = pty.openpty()
    fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", rows, columns, 0, 0))
    process = subprocess.Popen(
        [
            str(Path(sys.executable).with_name("ctk")),
            "--script-engine",
            "compiled",
            "--server",
            editor_server.endpoint,
            "-c",
            str(editor_server.config),
            "--lib-dir",
            str(tmp_path / "empty-libraries"),
        ],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        cwd=tmp_path,
        env=dict(
            os.environ, TERM="xterm-256color", XDG_STATE_HOME=str(tmp_path / "state")
        ),
        close_fds=True,
    )
    os.close(slave)
    screen = pyte.Screen(columns, rows)
    stream = pyte.ByteStream(screen)
    history = HistoryStore(tmp_path / "state/clang_tools/history.jsonl")

    def visible():
        return "\n".join(screen.display)

    def wait_for(predicate):
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if select.select([master], [], [], 0.1)[0]:
                try:
                    payload = os.read(master, 65536)
                except OSError as error:
                    if error.errno != errno.EIO:
                        raise
                    break
                if not payload:
                    break
                stream.feed(payload)
                if b"\x1b[6n" in payload:
                    os.write(master, b"\x1b[1;1R")
            elif predicate():
                return visible()
            if process.poll() is not None:
                break
        raise AssertionError(visible())

    def paste(source):
        os.write(master, ("\x1b[200~" + source + "\x1b[201~").encode())

    def submit(source, marker):
        previous = len(history.read_commands())
        paste(source)
        os.write(master, b"\x0a")
        return wait_for(
            lambda: marker in visible()
            and "Ready" in screen.display[-1]
            and len(history.read_commands()) > previous
        )

    try:
        wait_for(lambda: "Session open" in visible())
        helper = (
            Path(__file__).resolve().parents[2]
            / "skills/ctk-script/scripts/ctk_helpers.ctk"
        )
        submit(f'import "{helper}"', "import")
        # Two candidates keep the picker open while exposing full metadata.
        definition = "let scale(value, factor = 2) = { value * factor }"
        submit(definition + "; let scan(value) = value", "scale")
        os.write(master, b"sca\t")
        picker = wait_for(
            lambda: "user defined" in visible()
            and "scale(value, factor = 2)" in visible()
        )
        os.write(master, b"\x1b\x03")
        wait_for(lambda: "Input 1:1" in visible())
        help_output = submit("scale?", "Definition")
        assert "Signature" in help_output and "scale(value, factor = 2)" in help_output
        assert "unknown help topic" not in help_output
        # Inspect colors in the submitted definition, whose rendering shares
        # the editor lexer with the Markdown help examples.
        row = next(i for i, line in enumerate(screen.display) if definition in line)
        line = screen.display[row]
        colors = {
            screen.buffer[row][line.index(token)].fg
            for token in ("let", "scale", "value", "=", "2", "{")
        }
        assert len(colors) == 6
        target = tmp_path / "return_types.cc"
        target.write_text("int number() { return 7; }\nvoid action() {}\n")
        submit(f'let tree = parse "{target}"', "let tree")
        submit(
            'let typed = match functionDecl(returns(asString("int"))) in tree; '
            'print "RETURN_TYPES={typed.length}"',
            "RETURN_TYPES=1",
        )
        submit(
            'let located = match functionDecl(hasReturnTypeLoc(loc(asString("int")))) in tree; '
            'print "RETURN_LOCATIONS={located.length}"',
            "RETURN_LOCATIONS=1",
        )
        os.write(master, b"anc\t")
        helper_picker = wait_for(
            lambda: "user defined" in visible()
            and "ancestors(target, className, maxDepth = 32)" in visible()
        )
        os.write(master, b"\x1b\x03")
        wait_for(lambda: "Input 1:1" in visible())
        # The cursor returns to an earlier line, before existing arguments,
        # a native target and another statement. Tab must preserve all of it.
        draft = 'match functionDecl(\n  hasReturnTypeL()\n) in tree\nprint "KEEP_LATER"'
        paste(draft)
        wait_for(lambda: "KEEP_LATER" in visible())
        os.write(master, b"\x1b[A\x1b[A\x05\x1b[D\x1b[D\t")
        edited = wait_for(lambda: "hasReturnTypeLoc()" in visible())
        assert 'print "KEEP_LATER"' in edited
        assert "in tree" in edited
        # The missing auxiliary base matcher is now present in the picker.
        os.write(master, b"\x1b\x03")
        wait_for(lambda: "Input 1:1" in visible())
        paste("match cxxRecordDecl(hasDirectBase(cxxBaseS")
        os.write(master, b"\t")
        auxiliary = wait_for(lambda: "cxxBaseSpecifier" in visible())
        return picker, help_output, helper_picker, edited, auxiliary
    finally:
        if process.poll() is None:
            os.write(master, b"\x1b[21~")
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=5)
        os.close(master)


@then(
    "the workspace preserves later text and shows distinct colors and function signatures"
)
def verify_editor(editor_evidence):
    assert len(editor_evidence) == 5
    assert all("Traceback" not in frame for frame in editor_evidence)
