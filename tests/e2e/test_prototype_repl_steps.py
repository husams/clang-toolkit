"""PTY acceptance for the compiled scripting prototype in both console UIs."""

from __future__ import annotations

import errno
import fcntl
import gc
import os
import pty
import select
import signal
import struct
import subprocess
import termios
import time
from pathlib import Path

import pyte
import pytest
from pytest_bdd import given, scenarios, then, when

from clang_toolkit.client import Client
from tests.e2e.test_network_steps import RunningServer, _launch_server

pytestmark = pytest.mark.e2e
scenarios("prototype_repl.feature")

_RESOURCE_COUNTERS = (
    "result_cursors",
    "explicit_file_leases",
    "active_work",
    "reserved_bytes",
    "reusable_snapshots",
)


def _resource_counters(status: object) -> tuple[int, ...]:
    return tuple(int(getattr(status, field)) for field in _RESOURCE_COUNTERS)


def _repl_fixture(
    ui: str,
    tmp_path: Path,
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> dict[str, object]:
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "native-storage"))
    server = _launch_server("unix", tmp_path, request)
    source = tmp_path / "prototype_match.cc"
    source.write_text(
        "int callee() { return 7; }\n"
        "int caller() { return callee(); }\n"
        "struct Sample {};\n",
        encoding="utf-8",
    )
    return {"server": server, "source": source, "ui": ui}


@given(
    "an isolated compiled prompt REPL and native sample", target_fixture="compiled_repl"
)
def compiled_prompt_repl(tmp_path, request, monkeypatch):
    return _repl_fixture("prompt", tmp_path, request, monkeypatch)


@given(
    "an isolated compiled workspace REPL and native sample",
    target_fixture="compiled_repl",
)
def compiled_workspace_repl(tmp_path, request, monkeypatch):
    return _repl_fixture("workspace", tmp_path, request, monkeypatch)


@when(
    "I exercise compiled scripts through the real prompt terminal",
    target_fixture="compiled_repl_evidence",
)
@when(
    "I exercise compiled scripts through the real workspace terminal",
    target_fixture="compiled_repl_evidence",
)
def exercise_compiled_repl(compiled_repl, tmp_path: Path):
    server = compiled_repl["server"]
    source = compiled_repl["source"]
    ui = compiled_repl["ui"]
    assert isinstance(server, RunningServer)
    assert isinstance(source, Path)
    assert isinstance(ui, str)

    master, slave = pty.openpty()
    fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 110, 0, 0))
    state_root = tmp_path / "state"
    project_root = Path(__file__).resolve().parents[2]
    process = subprocess.Popen(
        [
            "uv",
            "run",
            "--quiet",
            "--project",
            str(project_root),
            "ctk",
            "--server",
            server.endpoint,
            "-c",
            str(server.config),
            "--ui",
            ui,
        ],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        cwd=tmp_path,
        env=dict(os.environ, TERM="xterm-256color", NO_COLOR="1", XDG_STATE_HOME=str(state_root)),
        close_fds=True,
    )
    os.close(slave)
    screen = pyte.Screen(110, 30)
    stream = pyte.ByteStream(screen)

    def feed_terminal(payload: bytes) -> None:
        request = b"\x1b[6n"
        while payload:
            cursor_request = payload.find(request)
            if cursor_request < 0:
                stream.feed(payload)
                return
            end = cursor_request + len(request)
            stream.feed(payload[:end])
            os.write(
                master,
                f"\x1b[{screen.cursor.y + 1};{screen.cursor.x + 1}R".encode(),
            )
            payload = payload[end:]

    def is_idle() -> bool:
        if ui == "workspace":
            return "Ready" in screen.display[-1] or "Command failed" in screen.display[-1]
        active_line = next(
            (line.strip() for line in reversed(screen.display) if line.strip()), ""
        )
        return active_line == "ctk>"

    def read_until(
        marker: str,
        timeout: float = 15,
        occurrences: int = 1,
        *,
        idle: bool = False,
    ) -> str:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if process.poll() is not None:
                break
            if select.select([master], [], [], 0.05)[0]:
                try:
                    payload = os.read(master, 65_536)
                except OSError as exc:
                    if exc.errno != errno.EIO:
                        raise
                    break
                if not payload:
                    break
                feed_terminal(payload)
            else:
                visible = "\n".join(screen.display)
                if visible.count(marker) >= occurrences and (not idle or is_idle()):
                    return visible
        visible = "\n".join(screen.display)
        (tmp_path / f"prototype-repl-{ui}-screen.txt").write_text(visible)
        raise AssertionError(f"{ui} REPL did not show {marker!r}:\n{visible}")

    def submit(text: str, marker: str, *, success: bool = True) -> str:
        # Match the real multiline paste gesture. The workspace uses Ctrl+Enter;
        # the prompt accepts with Enter after bracketed paste. Prompt mode uses
        # the normal Enter key once all pasted lines have arrived.
        sequence = "\x1b[27;5;13~" if ui == "workspace" else "\r"
        os.write(master, ("\x1b[200~" + text + "\x1b[201~").encode())
        final_fragment = text.splitlines()[-1][-18:]
        visible = read_until(final_fragment)
        os.write(master, sequence.encode())
        if marker:
            visible = read_until(marker, idle=success)
        elif success:
            visible = read_until("", idle=True)
        return visible or "\n".join(screen.display)

    def wait_for_exit(timeout: float = 10) -> int:
        deadline = time.monotonic() + timeout
        while process.poll() is None and time.monotonic() < deadline:
            if select.select([master], [], [], 0.05)[0]:
                try:
                    payload = os.read(master, 65_536)
                except OSError as exc:
                    if exc.errno != errno.EIO:
                        raise
                    break
                if payload:
                    feed_terminal(payload)
        return process.wait(timeout=max(0.1, deadline - time.monotonic()))

    try:
        read_until("Session open" if ui == "workspace" else "ctk>")
        # New operators and conditional expressions are not in the legacy
        # grammar. The installed project's default ctk entrypoint must accept it.
        setup_script = (
            "let total = 0\n"
            "let arithmetic = (2 +\n 3 * 4)\n"
            'let branch = if $arithmetic >= 14 do "large" else "small"\n'
            'let fallback = unless $branch == "empty" do "kept" else "lost"\n'
            'let chosen = true ? $arithmetic : (1 / 0)\n'
            "foreach value in [2, 4] do $total += $value\n"
            'let result = if $arithmetic == 14 and $branch == "large" and '
            '$fallback == "kept" and $chosen == 14 and $total == 6 '
            'do $arithmetic * 10 + $total else 0\n'
            'print "SETUP_${result}"'
        )
        result = submit(setup_script, "SETUP_146")
        # A separate submission proves that variables survive between REPL
        # submissions and that the multiline group executed as compiled code.
        result += submit(
            "$total += 1\nlet mutation = $total * 100 + 3\n"
            'print "MUTATION_${mutation}"',
            "MUTATION_703",
        )
        screenshot = submit("let x = 1", "")
        screenshot += submit("let y = if $x > 0 then $x * 10 else 1", "")
        screenshot += submit('print "SCREENSHOT_${y}"', "SCREENSHOT_10")

        # ctk() keeps native analysis inside the interactive compiled runtime;
        # its returned MatchRows are consumed by a conditional collected loop.
        root_query = (
            'let functions = match functionDecl(hasName("caller")).bind("f") '
            f'in "{source.name}"\n'
            'let root_result = $functions.length * 100 + 7\n'
            'print "ROOT_${root_result}"'
        )
        native = submit(root_query, "ROOT_107")
        continuation_query = (
            'let calls = match callExpr().bind("call") in $functions.f\n'
            'let names = foreach row in $calls do if $row.call.decl_name == "callee" '
            'do $row.call.decl_name else "other"\n'
            'let native_result = $calls.length * 100 + $names[0].length\n'
            'print "CONTINUATION_${native_result}"'
        )
        native += submit(continuation_query, "CONTINUATION_106")

        predicates = submit(
            'let data = {a: null, disabled: false}\n'
            'let present = $data has a\n'
            'let member = 2 in [1, 2, 3]\n'
            'let absent = $not_bound is not defined and $not_bound is not set\n'
            'let disabled = $data.disabled\n'
            'let disabled_is_set = $disabled is set\n'
            'let records = match cxxRecordDecl(hasName("Sample")).bind("item") '
            f'in "{source.name}"\n'
            'let is_record = $records[0].item is CXXRecord and '
            '$records[0].item is CXXRecordDecl\n'
            'let predicate_result = if $present and $member and $absent and '
            '$disabled_is_set and $is_record then 11111 else 0\n'
            'print "PREDICATES_${predicate_result}"',
            "PREDICATES_11111",
        )

        lazy = submit(
            'let skipped = false and ctk("file open \\"never-open.cc\\"")\n'
            'let also_skipped = true ? "safe" : ctk("server status")\n'
            'let lazy_result = (not $skipped and $also_skipped == "safe") ? '
            '($also_skipped.length * 100 + $calls.length) : 0\n'
            'print "LAZY_${lazy_result}"',
            "LAZY_401",
        )
        cancellation = ""
        cancel_recovery = ""
        if ui == "workspace":
            loop = (
                "foreach outer in range(10000) do "
                "foreach inner in range(10000) do $outer + $inner"
            )
            os.write(master, ("\x1b[200~" + loop + "\x1b[201~").encode())
            read_until("$outer + $inner")
            os.write(master, b"\x1b[27;5;13~")
            read_until("Running")
            os.write(master, b"\x03")
            cancellation = read_until("execution cancelled", idle=True)
            cancel_recovery = submit(
                'let cancel_recovered = 31\n'
                'print "CANCEL_RECOVERY_${cancel_recovered}"',
                "CANCEL_RECOVERY_31",
            )
        error = submit("let broken = 1 / 0", "division by zero", success=False)
        read_until("division by zero", idle=True)
        recovered = submit(
            'let recovered = 10 + 20\nprint "RECOVERED_${recovered}"',
            "RECOVERED_30",
        )
        with Client(server.endpoint) as observer:
            during = _resource_counters(observer.resource_status())
        submit("quit", "", success=False)
        returncode = wait_for_exit()
        with Client(server.endpoint) as observer:
            observer.prune_caches(memory=True, disk=True)
            gc.collect()
            after = _resource_counters(observer.resource_status())
        return {
            "ui": ui,
            "result": result,
            "screenshot": screenshot,
            "native": native,
            "predicates": predicates,
            "lazy": lazy,
            "cancellation": cancellation,
            "cancel_recovery": cancel_recovery,
            "error": error,
            "recovered": recovered,
            "during": during,
            "after": after,
            "returncode": returncode,
        }
    finally:
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        os.close(master)


@then(
    "the prompt retains values, runs native continuation, and releases resources"
)
@then(
    "the workspace retains values, runs native continuation, and releases resources"
)
def verify_compiled_repl_evidence(compiled_repl_evidence):
    evidence = compiled_repl_evidence
    assert evidence["ui"] in {"prompt", "workspace"}
    assert "SETUP_146" in evidence["result"] and "MUTATION_703" in evidence["result"]
    assert "SCREENSHOT_10" in evidence["screenshot"]
    assert "ROOT_107" in evidence["native"] and "CONTINUATION_106" in evidence["native"]
    assert "PREDICATES_11111" in evidence["predicates"]
    assert "LAZY_401" in evidence["lazy"]
    assert "division by zero" in evidence["error"]
    assert "RECOVERED_30" in evidence["recovered"]
    if evidence["ui"] == "workspace":
        assert "execution cancelled" in evidence["cancellation"]
        assert "CANCEL_RECOVERY_31" in evidence["cancel_recovery"]
    assert evidence["during"][0] > 0
    assert evidence["after"] == (0, 0, 0, 0, 0)
    assert evidence["returncode"] == 1
