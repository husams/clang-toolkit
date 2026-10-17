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
from pytest_bdd import given, parsers, scenarios, then, when

from clang_toolkit.cli.runtime.history import HistoryStore
from tests.e2e.test_network_steps import _launch_server

pytestmark = pytest.mark.e2e
scenarios("list_patterns.feature")


@given("an isolated list-pattern console", target_fixture="pattern_console")
def pattern_console(tmp_path, request, monkeypatch):
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "native-storage"))
    server = _launch_server("unix", tmp_path, request)
    library = tmp_path / "empty-libraries"
    library.mkdir()
    return server, library


@when(parsers.parse('I run the list-pattern example in the "{engine}" terminal'), target_fixture="pattern_terminal")
def pattern_terminal(pattern_console, tmp_path, engine):
    server, library = pattern_console
    master, slave = pty.openpty()
    fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", 45, 140, 0, 0))
    process = subprocess.Popen([
        str(Path(sys.executable).with_name("ctk")), "--script-engine", engine,
        "--ui", "prompt", "--server", server.endpoint, "-c", str(server.config),
        "--lib-dir", str(library),
    ], stdin=slave, stdout=slave, stderr=slave, cwd=tmp_path,
        env=dict(os.environ, TERM="xterm-256color", XDG_STATE_HOME=str(tmp_path / "state")))
    os.close(slave)
    screen = pyte.Screen(140, 45)
    stream = pyte.ByteStream(screen)
    transcript = bytearray()

    def wait_for(marker):
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if select.select([master], [], [], 0.1)[0]:
                try:
                    data = os.read(master, 65536)
                except OSError as error:
                    if error.errno != errno.EIO:
                        raise
                    break
                if not data:
                    break
                transcript.extend(data)
                stream.feed(data)
                if b"\x1b[6n" in data:
                    os.write(master, f"\x1b[{screen.cursor.y + 1};{screen.cursor.x + 1}R".encode())
            elif marker in "\n".join(screen.display):
                return "\n".join(screen.display)
            if process.poll() is not None:
                break
        raise AssertionError("\n".join(screen.display))

    try:
        wait_for("ctk>")
        source = (Path(__file__).resolve().parents[2] / "examples/list_patterns.ctk").read_text()
        source += '\nprint "PATTERNS_PTY_{total([1, 2, 3])}"'
        os.write(master, ("\x1b[200~" + source + "\x1b[201~\n").encode())
        visible = wait_for("PATTERNS_PTY_6")
        assert HistoryStore(tmp_path / "state/clang_tools/history.jsonl").read_commands() == [source]
        return visible
    finally:
        (tmp_path / "list-patterns-terminal.txt").write_bytes(transcript)
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        os.close(master)


@then("the terminal prints the list-pattern results")
def verify_pattern_terminal(pattern_terminal):
    lines = [line.strip() for line in pattern_terminal.splitlines()]
    assert "60" in lines and "0" in lines and "30" in lines
    assert "[10,30]" in lines
    assert "Destructured: 10, 20, 30" in lines
    assert "Large total: 12497500" in lines
    assert "error:" not in pattern_terminal
