"""Real-terminal proof that project names come from the connected server."""

from __future__ import annotations

import errno
import fcntl
import json
import os
import pty
import select
import struct
import subprocess
import sys
import termios
import tempfile
import time
from pathlib import Path

import pyte
import pytest
from pytest_bdd import given, scenarios, then, when

from clang_toolkit import Client
from tests.e2e.test_network_steps import _launch_server

pytestmark = pytest.mark.e2e
scenarios("project_completion.feature")


@given("an indexed ctk-lab project for completion", target_fixture="project_console")
def project_console(tmp_path, request, monkeypatch):
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "storage"))
    server = _launch_server("unix", tmp_path, request)
    directory = tempfile.TemporaryDirectory(prefix="ctk-pc-", dir="/tmp")
    request.addfinalizer(directory.cleanup)
    root = Path(directory.name) / "ctk-lab"
    root.mkdir(parents=True)
    source = root / "flow.cc"
    source.write_text("namespace flow { int clamp(int value) { return value; } }\n")
    (root / "compile_commands.json").write_text(
        json.dumps(
            [
                {
                    "directory": str(root),
                    "file": str(source),
                    "arguments": [
                        os.environ.get("CTK_TEST_CLANG", "clang++"),
                        "-c",
                        str(source),
                    ],
                }
            ]
        )
    )
    with Client(server.endpoint) as client:
        client.start_project_index(root)
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            if client.project_index_status(root).translation_units_indexed == 1:
                break
            time.sleep(0.05)
        else:
            raise AssertionError("fixture did not finish indexing")
    return server, root


@when(
    "I select ctk-lab after in using Tab in the actual console",
    target_fixture="project_evidence",
)
def select_project(project_console, tmp_path):
    server, root = project_console
    empty = tmp_path / "empty"
    empty.mkdir()
    master, slave = pty.openpty()
    fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 160, 0, 0))
    process = subprocess.Popen(
        [
            str(sys.executable),
            "-m",
            "clang_toolkit.cli.app",
            "--script-engine",
            "compiled",
            "--server",
            server.endpoint,
            "-c",
            str(server.config),
            "--lib-dir",
            str(empty),
        ],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        cwd=empty,
        close_fds=True,
        env=dict(
            os.environ, TERM="xterm-256color", XDG_STATE_HOME=str(tmp_path / "state")
        ),
    )
    os.close(slave)
    screen = pyte.Screen(160, 40)
    stream = pyte.ByteStream(screen)

    def visible():
        return "\n".join(screen.display)

    def wait_for(predicate, timeout=20):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if select.select([master], [], [], 0.1)[0]:
                try:
                    payload = os.read(master, 65536)
                except OSError as error:
                    if error.errno != errno.EIO:
                        raise
                    break
                stream.feed(payload)
                if b"\x1b[6n" in payload:
                    os.write(master, b"\x1b[1;1R")
            if predicate():
                return visible()
            if process.poll() is not None:
                break
        raise AssertionError(visible())

    try:
        wait_for(lambda: "Session open" in visible())
        prefix = 'index find "flow::clamp" kind function in '
        os.write(master, prefix.encode())
        menu = wait_for(
            lambda: "ctk-lab" in visible() and "indexed project" in visible()
        )
        (tmp_path / "project-menu.txt").write_text(menu)
        os.write(master, b'"ct')
        wait_for(lambda: 'in "ct' in visible() and "indexed project" in visible())
        os.write(master, b"\t")
        wait_for(lambda: 'in "ctk-lab"' in visible())
        os.write(master, b"\x0a")
        result = wait_for(
            lambda: "flow::clamp" in visible() and "[Function]" in visible()
        )
        (tmp_path / "project-result.txt").write_text(result)
        return menu, result
    finally:
        if process.poll() is None:
            os.write(master, b"\x1b[21~")
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.terminate()
                process.wait(timeout=5)
        os.close(master)


@then("the scoped symbol search finds flow clamp and the menu shows its indexed path")
def verify_project(project_evidence, project_console):
    menu, result = project_evidence
    _, root = project_console
    assert "ctk-lab" in menu and str(root) in menu
    assert "flow::clamp" in result and "[Function]" in result
