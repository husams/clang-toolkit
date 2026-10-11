"""Real terminal and native server acceptance for the workspace entry point."""

from __future__ import annotations

import errno
import fcntl
import os
import pty
import re
import select
import signal
import struct
import subprocess
import sys
import termios
import time
from collections.abc import Callable
from pathlib import Path

import pyte
import pytest
from clang_toolkit.cli.runtime.history import HistoryStore
from clang_toolkit.client import Client
from pytest_bdd import given, scenarios, then, when

from tests.e2e.test_network_steps import RunningServer, _launch_server

pytestmark = pytest.mark.e2e
scenarios("workspace_console.feature")


@given(
    "an isolated workspace server and a C++ input", target_fixture="workspace_server"
)
def workspace_server(
    tmp_path: Path, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> tuple[RunningServer, Path]:
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "native-storage"))
    source = tmp_path / "sample.cpp"
    source.write_text("int workspace_native() {\n    const int value = 7;\n    const int result = 6 + (value + 5) * 3;\n    return result;\n}\n")
    return _launch_server("unix", tmp_path, request), source


@when(
    "I use the real workspace menu and file panel then submit multiline analysis",
    target_fixture="workspace_run",
)
def run_workspace(
    workspace_server: tuple[RunningServer, Path], tmp_path: Path
) -> tuple[int, str, list[str], list[str]]:
    server, source = workspace_server
    master, slave = pty.openpty()
    fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", 28, 100, 0, 0))
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "clang_toolkit.cli.app",
            "--server",
            server.endpoint,
            "-c",
            str(server.config),
        ],
        stdin=slave,
        stdout=slave,
        stderr=slave,
        cwd=tmp_path,
        env=dict(
            os.environ,
            TERM="xterm-256color",
            NO_COLOR="1",
            XDG_STATE_HOME=str(tmp_path / "state"),
        ),
        close_fds=True,
    )
    os.close(slave)
    screen = pyte.Screen(100, 28)
    stream = pyte.ByteStream(screen)
    commands = [
        'let inputs = [\n"one",\n"two"\n]',
        f'let tree = parse "{source}"',
        'let rows = match functionDecl().bind("f") in $tree',
        "print $rows[0].f.decl_name",
        'print "INPUT_COUNT=${inputs.length}"',
    ]

    def read_until(
        expected: str,
        timeout: float = 15,
        ready: bool = False,
        recorded: Callable[[], bool] | None = None,
    ) -> str:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if select.select([master], [], [], 0.05)[0]:
                try:
                    payload = os.read(master, 65_536)
                except OSError as exc:
                    if exc.errno != errno.EIO:
                        raise
                    break
                if not payload:
                    break
                text = payload.decode("utf-8", errors="replace")
                stream.feed(payload)
                # Respond to terminal cursor-position requests.
                if "\x1b[6n" in text:
                    os.write(master, b"\x1b[1;1R")
            else:
                # A renderer frame can span several PTY reads. Observe it after
                # writes settle, rather than returning in the middle of a redraw.
                visible = "\n".join(screen.display)
                if (
                    expected in visible
                    and (not ready or "Ready" in screen.display[-1])
                    and (recorded is None or recorded())
                ):
                    return visible
            if process.poll() is not None:
                break
        raise AssertionError(
            f"workspace did not show {expected!r}:\n" + "\n".join(screen.display)
        )

    def redraw() -> None:
        os.write(master, b"\x0c")

    def submit(source_text: str, expected: str, *, success: bool = True, execute_sequence: str = "\x1b[27;5;13~") -> None:
        before = len(
            HistoryStore(tmp_path / "state/clang_tools/history.jsonl").read_commands()
        )
        os.write(master, ("\x1b[200~" + source_text + "\x1b[201~" + execute_sequence).encode())
        # Wait for completion; recording occurs before native execution.
        redraw()
        read_until(
            expected,
            ready=success,
            recorded=lambda: (
                len(
                    HistoryStore(
                        tmp_path / "state/clang_tools/history.jsonl"
                    ).read_commands()
                )
                > before
            ),
        )

    try:
        read_until("Session open")
        assert screen.display[0].startswith(" CTK console | ")
        # Exercise the menu at a size that requires scrolling, with real SGR
        # mouse input rather than invoking its handlers directly.
        fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", 14, 100, 0, 0))
        screen.resize(lines=14, columns=100)
        os.kill(process.pid, signal.SIGWINCH)
        os.write(master, b"\x1bOQ")  # F2 Menu
        read_until("Browse local files")
        os.write(master, b"\x1b[<65;10;5M")
        read_until("> Pause following results")
        os.write(master, b"\x1b[F")
        read_until("> Quit  F10")
        os.write(master, b"\x1b[H")
        read_until("> Browse local files")
        os.write(master, b"\r")
        read_until("Local files")
        os.write(master, b"\x1bOR")  # F3 Close files
        fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", 28, 100, 0, 0))
        screen.resize(lines=28, columns=100)
        os.kill(process.pid, signal.SIGWINCH)
        expected = [
            "let inputs",
            "let tree",
            "let rows",
            "workspace_native",
            "INPUT_COUNT=2",
        ]
        source_session = None
        initial_expiry = None
        for index, (command, marker) in enumerate(zip(commands, expected, strict=True)):
            submit(command, marker, execute_sequence="\r" if index in {0, 3} else "\x1b[27;5;13~")
            if index == 1:
                with Client(server.endpoint) as observer:
                    info = next(
                        item
                        for item in observer.list_sessions().sessions
                        if item.row_count == 0
                    )
                    source_session = info.session_id
                    initial_expiry = (info.expires_at.seconds, info.expires_at.nanos)
        with Client(server.endpoint) as observer:
            info = next(
                item
                for item in observer.list_sessions().sessions
                if item.session_id == source_session
            )
            assert (info.expires_at.seconds, info.expires_at.nanos) > initial_expiry
        redraw()
        output = read_until("INPUT_COUNT=2")
        assert "workspace_native" in output
        (tmp_path / "workspace-compact.txt").write_text(output)
        # Ordinary expression and print output share the match outline widget.
        for command, title, child in (
            ("$inputs", "List", "[1] = 'two'"),
            ("print {x: 1, y: 3}", "Dictionary", "y = 3"),
        ):
            commands.append(command)
            submit(command, "▸ " + title)
            row = next(i for i, line in enumerate(screen.display) if "▸ " + title in line)
            column = screen.display[row].index("▸") + 1
            os.write(master, f"\x1b[<0;{column};{row + 1}M\x1b[<0;{column};{row + 1}m".encode())
            # Expansion retains the selected parent; move to the last child
            # to bring it into this deliberately compact results viewport.
            read_until("▾ " + title)
            os.write(master, b"\x1b[B\x1b[B")
            read_until(child)
            os.write(master, b"\x1b[D\x1b[D")
            read_until("▸ " + title, recorded=lambda: not any(child in line for line in screen.display))
            os.write(master, b"\x1b[1;5F\x1b[17~\x1b[17~")
        (tmp_path / "workspace-collection-tree.txt").write_text("\n".join(screen.display))
        # Typed results expand inside the existing results pane.
        commands.append("print $rows")
        submit(commands[-1], "▸ Matches")
        row = next(i for i, line in enumerate(screen.display) if "▸ Matches" in line)
        column = screen.display[row].index("▸") + 1
        os.write(master, f"\x1b[<0;{column};{row + 1}M\x1b[<0;{column};{row + 1}m".encode())
        read_until("[0] · MatchRow")
        link_row = next(i for i, line in enumerate(screen.display) if "[0] · MatchRow" in line)
        link_column = screen.display[link_row].index("[0] · MatchRow")
        assert screen.buffer[link_row][link_column].underscore
        assert not screen.buffer[link_row][link_column - 1].underscore
        link_end = len(screen.display[link_row].rstrip())
        assert not screen.buffer[link_row][link_end + 1].underscore
        os.write(master, b"\x1b[C\x1b[C\x1b[C")
        read_until("f - workspace_native")
        os.write(master, b"\x1b[C\x1b[C")
        read_until("decl_name = 'workspace_native'")
        assert not any(
            "source_match_index =" in line or "BindingMapView" in line
            for line in screen.display
        )
        (tmp_path / "workspace-match-tree.txt").write_text("\n".join(screen.display))
        # A binding link opens a separate C++ source window, preserving the
        # existing console panes and returning to the same tree on close.
        os.write(master, b"\x1b[D")
        read_until("f - workspace_native")
        row = next(i for i, line in enumerate(screen.display) if "f - workspace_native" in line)
        column = screen.display[row].index("f - workspace_native") + 1
        os.write(master, f"\x1b[<0;{column};{row + 1}M\x1b[<0;{column};{row + 1}m".encode())
        read_until("Matches [1]")
        outline_row = next(i for i, line in enumerate(screen.display) if "[0] sample.cpp:" in line)
        outline_column = screen.display[outline_row].index("[0] sample.cpp:")
        assert screen.buffer[outline_row][outline_column].underscore
        assert not screen.buffer[outline_row][outline_column - 1].underscore
        assert not screen.display[0].startswith(" CTK console | ")
        read_until("int workspace_native")
        assert any("1│" in line and "int workspace_native" in line for line in screen.display)
        row = next(i for i, line in enumerate(screen.display) if "int workspace_native" in line)
        column = screen.display[row].index("int workspace_native")
        assert screen.buffer[row][column].fg != screen.buffer[row][column + 4].fg
        read_until("const int result")
        for index in range(5):
            code_line = screen.display[row + index]
            assert f"▶{index + 1}│" in code_line  # One screen row per original source line.
            marker_column = code_line.index("▶")
            assert screen.buffer[row + index][marker_column].fg in {"ff8080", "ff8787"}
        assert screen.buffer[row][column].underscore
        assert column - screen.display[row].index("▶") == 4
        assert screen.buffer[row][column].bg != "315d80"
        (tmp_path / "workspace-source-window.txt").write_text("\n".join(screen.display))
        os.write(master, b"\t\r")
        read_until("f — workspace_native")
        os.write(master, b"\x1b")
        read_until("f - workspace_native", recorded=lambda: not any("Matches in file" in line for line in screen.display))
        os.write(master, b"\x1b[D" * 6)
        read_until("▸ Matches", recorded=lambda: not any("decl_name =" in line for line in screen.display))
        os.write(master, b"\x1b[1;5F\x1b[17~\x1b[17~")  # Resume following; cycle through help to input.
        # A real AST expression selects only the middle of its statement.
        commands.append('let expressions = match binaryOperator(hasOperatorName("*"), isExpansionInMainFile()).bind("expr") in $tree')
        submit(commands[-1], "Ready")
        commands.append('print $expressions')
        submit(commands[-1], "▸ Matches")
        row = max(i for i, line in enumerate(screen.display) if "▸ Matches" in line)
        column = screen.display[row].index("▸") + 1
        os.write(master, f"\x1b[<0;{column};{row + 1}M\x1b[<0;{column};{row + 1}m".encode())
        read_until("sample.cpp:3:")
        row = next(i for i, line in enumerate(screen.display) if "[0] · MatchRow" in line and "sample.cpp:3:" in line)
        column = screen.display[row].index("[0] · MatchRow") + 1
        os.write(master, f"\x1b[<0;{column};{row + 1}M\x1b[<0;{column};{row + 1}m".encode())
        read_until("lines 3–3")
        expression = "(value + 5) * 3"
        code_row = next(i for i, line in enumerate(screen.display) if expression in line)
        column = screen.display[code_row].index(expression)
        assert "▶3│" in screen.display[code_row]
        assert all(screen.buffer[code_row][column + offset].underscore for offset in range(len(expression)))
        assert not screen.buffer[code_row][column - 1].underscore
        assert not screen.buffer[code_row][column + len(expression)].underscore  # The semicolon is outside the AST range.
        (tmp_path / "workspace-source-expression.txt").write_text("\n".join(screen.display))
        os.write(master, b"\x1b")
        read_until("CTK console", recorded=lambda: not any("Matches in file" in line for line in screen.display))
        os.write(master, b"\x1b[1;5F\x1b[17~\x1b[17~")
        commands.append('binding drop $expressions')
        submit(commands[-1], "Ready")
        commands.append("session list")
        submit(commands[-1], "▸ Sessions")
        row = next(i for i, line in enumerate(screen.display) if "▸ Sessions" in line)
        column = screen.display[row].index("▸") + 1
        os.write(master, f"\x1b[<0;{column};{row + 1}M\x1b[<0;{column};{row + 1}m".encode())
        read_until("sample.cpp")
        os.write(master, b"\x1b[C" * 3)
        read_until("session_id =")
        os.write(master, b"\x1b[B" * 3)
        read_until("row_count =")
        (tmp_path / "workspace-session-tree.txt").write_text("\n".join(screen.display))
        os.write(master, b"\x1b[1;5F\x1b[17~\x1b[17~")
        commands.append("server status")
        submit(commands[-1], "Resident memory")
        row = next(i for i, line in enumerate(screen.display) if "Resident memory" in line)
        column = screen.display[row].index("Resident memory")
        assert screen.buffer[row][column].bg != "default"
        (tmp_path / "workspace-command-output.txt").write_text("\n".join(screen.display))
        # Foreground progress is a single updated bar, backed by native work.
        second_source = tmp_path / "second.cc"
        second_source.write_text("int second() {\n    return 2;\n}\n")
        commands.append(f'let batch_inputs = files ["{source}", "{second_source}"]')
        submit(commands[-1], "Ready")
        commands.append('batch part in $batch_inputs size 1 do { match functionDecl() in $part; }')
        submit(commands[-1], "State: completed")
        progress_row = next(i for i, line in enumerate(screen.display) if "2/2 files" in line and "Batch " in line)
        assert "State:" not in screen.display[progress_row]
        assert "State: completed" in screen.display[progress_row + 1]
        assert sum("Batch " in line and "2/2 files" in line for line in screen.display) == 1
        assert not any("group 1 started:" in line for line in screen.display)
        (tmp_path / "workspace-batch-progress.txt").write_text("\n".join(screen.display))
        commands.append('binding drop $batch_inputs')
        submit(commands[-1], "Ready")
        # Read live server data and expand actual retained bindings in a wide
        # terminal. Every panel shares the existing draft and command runtime.
        fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", 28, 140, 0, 0))
        screen.resize(lines=28, columns=140)
        os.kill(process.pid, signal.SIGWINCH)
        os.write(master, b"\x1b[20~")  # F9 live server status.
        read_until("Resident memory")
        assert "RSS" in screen.display[-1]
        # Click the actual title's close button through SGR mouse input.
        title = next(i for i, line in enumerate(screen.display) if "[×]" in line)
        column = screen.display[title].index("×") + 1
        os.write(
            master,
            f"\x1b[<0;{column};{title + 1}M\x1b[<0;{column};{title + 1}m".encode(),
        )
        read_until(
            "Command · 1 line",
            recorded=lambda: not any("[×]" in line for line in screen.display),
        )
        os.write(master, b"\x1b[18~")  # F7 binding outline.
        read_until("$rows · MatchValue")
        # Replace a focused help Window while Actions remembers it, then close.
        os.write(master, b"\x1bOS\x1bOQ")
        read_until("Browse local files")
        os.write(master, b"\x1b[18~\x1bOQ")
        read_until("$rows · MatchValue")
        assert "does not appear in the layout" not in "\n".join(screen.display)
        os.write(master, b"\x1b[B\r")  # Expand rows.
        read_until("[0] · MatchRow")
        os.write(master, b"\x1b[B\r")  # Expand first row.
        read_until("f - workspace_native")
        os.write(master, b"\x1b[B\r")  # Expand readable node properties.
        read_until("decl_name = 'workspace_native'")
        (tmp_path / "workspace-outline.txt").write_text("\n".join(screen.display))
        os.write(master, b"\x1b[19~")  # F8 resource inventory.
        read_until("Retained sessions")
        os.write(master, b"\x1b[H\x1b[C")
        read_until("sample.cpp")
        os.write(master, b"\x1b[F\x1b[C")
        read_until("rows ·")
        assert "sample.cpp" in "\n".join(screen.display)
        # Choose a retained cursor; a prepares an attachment for user review.
        cursor_row = next(
            i
            for i, line in enumerate(screen.display)
            if re.search(r"[0-9a-f-]{12} · \d+ rows", line)
        )
        os.write(
            master,
            f"\x1b[<0;100;{cursor_row + 1}M\x1b[<0;100;{cursor_row + 1}ma".encode(),
        )
        read_until("session attach")
        attach_command = next(
            line for line in screen.display if "│ session attach" in line
        )
        assert "into $attached1" in attach_command
        commands.append(
            re.search(
                r'session attach "[0-9a-f-]+" into \$attached1', attach_command
            ).group()
        )
        # Close the panel to keep the submitted command unwrapped for history.
        os.write(master, b"\x1b[19~\x1b[27;5;13~")
        read_until(
            "Ready",
            ready=True,
            recorded=lambda: len(
                HistoryStore(
                    tmp_path / "state/clang_tools/history.jsonl"
                ).read_commands()
            )
            == len(commands),
        )
        commands.append("print $attached1.path")
        submit(commands[-1], "sample.cpp")
        os.write(master, b"\x1b[19~")
        read_until("Retained sessions")
        cursor_row = next(
            i
            for i, line in enumerate(screen.display)
            if re.search(r"[0-9a-f-]{12} · \d+ rows", line)
        )
        os.write(
            master,
            f"\x1b[<0;100;{cursor_row + 1}M\x1b[<0;100;{cursor_row + 1}mc".encode(),
        )
        read_until("│ session close")
        close_line = next(line for line in screen.display if "│ session close" in line)
        commands.append(re.search(r'session close "[0-9a-f-]+"', close_line).group())
        os.write(master, b"\x1b[19~\x1b[27;5;13~")
        read_until(
            "Ready",
            ready=True,
            recorded=lambda: len(
                HistoryStore(
                    tmp_path / "state/clang_tools/history.jsonl"
                ).read_commands()
            )
            == len(commands),
        )
        # Long local lists page lazily; long properties scroll using the mouse.
        commands.extend(
            [
                "let zpages = [" + ", ".join(map(str, range(125))) + "]",
                'let zwide = "' + "x" * 180 + 'TAIL"',
            ]
        )
        for command in commands[-2:]:
            submit(command, "Ready")
        os.write(master, b"\x1b[18~")
        read_until("Bindings")
        os.write(master, b"\x1b[F")
        read_until("$zwide")
        bar_row = next(
            i for i, line in enumerate(screen.display) if "‹" in line and "━" in line
        )
        bar_column = screen.display[bar_row].rindex("›")
        os.write(
            master,
            f"\x1b[<0;{bar_column};{bar_row + 1}M\x1b[<0;{bar_column};{bar_row + 1}m".encode(),
        )
        read_until(
            "TAIL", recorded=lambda: any("TAIL" in line[92:] for line in screen.display)
        )
        bar_column = screen.display[bar_row].index("‹") + 1
        os.write(
            master,
            f"\x1b[<0;{bar_column};{bar_row + 1}M\x1b[<0;{bar_column};{bar_row + 1}m".encode(),
        )
        os.write(master, b"\x1b[1;5D" * 40 + b"\x1b[F\x1b[A\r")
        read_until("Items 1–50")
        os.write(master, b"\x1b[F\x1b[A\r")
        read_until("[99] = 99")
        os.write(master, b"\x1b[F\x1b[A\r")
        read_until("[124] = 124")
        (tmp_path / "workspace-pages.txt").write_text("\n".join(screen.display))
        os.write(master, b"\x1bOS")  # F4 shows help again.
        read_until("Command help")
        os.write(master, b"\x1b[17~")  # F6 help -> command.
        # Resize to the original dimensions for multiline expansion checks.
        fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", 28, 100, 0, 0))
        screen.resize(lines=28, columns=100)
        os.kill(process.pid, signal.SIGWINCH)
        os.write(master, ("\x1b[200~" + commands[0] + "\x1b[201~").encode())
        read_until("Command · 4 lines")
        expanded = read_until("   4 │ ]")
        assert "...>" not in expanded
        assert any(
            cell.fg != "default"
            for line in screen.buffer.values()
            for cell in line.values()
        )
        keyword_row = next(
            i for i, line in enumerate(screen.display) if "│ let inputs" in line
        )
        keyword_column = screen.display[keyword_row].index("let inputs")
        assert screen.buffer[keyword_row][keyword_column].fg != "default"
        os.write(master, b"\x1bOR")
        expanded = read_until("Local files")
        (tmp_path / "workspace-expanded.txt").write_text(expanded)
        os.write(master, b"\x1bOR\x03")
        read_until("Draft cleared")
        long_draft = "let inputs = [\n" + ",\n".join(str(i) for i in range(25))
        os.write(master, ("\x1b[200~" + long_draft + "\x1b[201~").encode())
        read_until("Command · 26 lines")
        capped = read_until("  26 │ 24")
        assert "  26 │ 24" in capped
        (tmp_path / "workspace-capped.txt").write_text(capped)
        os.write(master, b"\x03\x1bOS")  # Clear draft; close help for full-width code.
        read_until("Draft cleared")
        commands.append("help parse")
        submit(commands[-1], "examples/parse_match.cc")
        help_frame = "\n".join(screen.display)
        assert "Examples" in help_frame
        assert (
            "```" not in help_frame
            and "###" not in help_frame
            and "Usage:" not in help_frame
        )
        example_row = next(
            i
            for i, line in enumerate(screen.display)
            if 'let tree = parse "examples/' in line
        )
        example_line = screen.display[example_row]
        assert (
            len(
                {
                    screen.buffer[example_row][example_line.index(token)].fg
                    for token in ("let", "tree", "parse", '"examples/')
                }
            )
            == 3
        )
        assert screen.buffer[example_row][example_line.index("let")].bg != "default"
        (tmp_path / "workspace-help.txt").write_text(help_frame)
        # Exercise real typing, not bracketed paste: pairs keep the cursor inside.
        os.write(master, b"let smart = [")
        read_until("let smart = []")
        assert screen.buffer[screen.cursor.y][screen.cursor.x].data == "]"
        os.write(master, b"\x7f")
        read_until("let smart = ")
        os.write(master, b"[\r1,\r2")
        smart_frame = read_until("Command · 4 lines")
        assert "    2" in smart_frame
        (tmp_path / "workspace-editing.txt").write_text(smart_frame)
        commands.append("let smart = [\n    1,\n    2\n]")
        os.write(master, b"\r]\x1b[27;5;13~")
        redraw()
        read_until(
            "Ready",
            ready=True,
            recorded=lambda: len(
                HistoryStore(
                    tmp_path / "state/clang_tools/history.jsonl"
                ).read_commands()
            )
            == len(commands),
        )
        os.write(master, b'print "')
        read_until('print ""')
        assert screen.buffer[screen.cursor.y][screen.cursor.x].data == '"'
        commands.append('print "PAIRED"')
        os.write(master, b'PAIRED"\x1b[27;5;13~')
        read_until(
            "PAIRED",
            ready=True,
            recorded=lambda: len(
                HistoryStore(
                    tmp_path / "state/clang_tools/history.jsonl"
                ).read_commands()
            )
            == len(commands),
        )
        # A selected nested matcher gets its own closer before both outer ones.
        prefix = "let paired = functionDecl(\n    unless(\n        isImp"
        suffix = "\n    )\n)"
        os.write(master, ("\x1b[200~" + prefix + suffix + "\x1b[201~").encode())
        read_until("isImp")
        os.write(master, b"\x1b[A\x1b[A\x05\t")
        pair_frame = read_until("isImplicit()")
        assert screen.buffer[screen.cursor.y][screen.cursor.x].data == ")"
        assert any(line.lstrip().startswith("4 │     )") for line in screen.display), (
            pair_frame
        )
        assert any(line.lstrip().startswith("5 │ )") for line in screen.display), (
            pair_frame
        )
        (tmp_path / "workspace-smart-pairs.txt").write_text(pair_frame)
        commands.append(prefix[:-5] + "isImplicit()" + suffix)
        os.write(master, b")\x1b[B\x1b[B\x05\x1b[27;5;13~")
        read_until(
            "Ready",
            ready=True,
            recorded=lambda: len(
                HistoryStore(
                    tmp_path / "state/clang_tools/history.jsonl"
                ).read_commands()
            )
            == len(commands),
        )
        # Typed parentheses and either quote also insert before an outer closer.
        for name, quote in [("paired_double", '"'), ("paired_single", "'")]:
            prefix = f"let {name} = functionDecl(hasName"
            os.write(master, ("\x1b[200~" + prefix + ")\x1b[201~\x1b[D(").encode())
            read_until(prefix + "())")
            assert screen.buffer[screen.cursor.y][screen.cursor.x].data == ")"
            os.write(master, quote.encode())
            read_until(prefix + "(" + quote + quote + "))")
            assert screen.buffer[screen.cursor.y][screen.cursor.x].data == quote
            commands.append(prefix + "(" + quote + "paired" + quote + "))")
            os.write(master, ("paired" + quote + "))\x1b[27;5;13~").encode())
            read_until(
                "Ready",
                ready=True,
                recorded=lambda: len(
                    HistoryStore(
                        tmp_path / "state/clang_tools/history.jsonl"
                    ).read_commands()
                )
                == len(commands),
            )
        semantic_code = 'let display = memberExpr(member(hasName("first")))'
        commands.append(semantic_code)
        submit(semantic_code, semantic_code)
        code_row = next(
            i for i, line in enumerate(screen.display) if semantic_code in line
        )
        line = screen.display[code_row]
        colors = {
            screen.buffer[code_row][line.index(token)].fg
            for token in (
                "let",
                "display",
                "=",
                "memberExpr",
                "member(",
                "hasName",
                '"first"',
                "(",
            )
        }
        assert len(colors) == 8
        background = screen.buffer[code_row][line.index("let")].bg
        assert background != "default"
        assert screen.buffer[code_row][98].bg == background
        assert "CTK command" not in "\n".join(screen.display)
        commands.append('let long_code = "' + "x" * 260 + 'TAIL"')
        submit(commands[-1], "Ready")
        start_row = next(
            i for i, line in enumerate(screen.display) if "let long_code = " in line
        )
        tail_row = max(
            i for i, line in enumerate(screen.display) if line.rstrip().endswith('IL"')
        )
        rebuilt = "".join(
            line.split("│ ", 1)[1].rstrip()
            for line in screen.display[start_row : tail_row + 1]
        )
        assert rebuilt == commands[-1]
        assert "│ " in screen.display[tail_row]
        assert screen.buffer[tail_row][98].bg == background
        (tmp_path / "workspace-code.txt").write_text("\n".join(screen.display))
        commands.append('let a_manifest = files "*.cpp"')
        submit(commands[-1], "Ready")
        # File paths are immediate children, with useful declaration titles.
        fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", 28, 140, 0, 0))
        screen.resize(lines=28, columns=140)
        os.kill(process.pid, signal.SIGWINCH)
        os.write(master, b"\x1b[18~")
        read_until("Bindings")
        os.write(master, b"\x1b[H")
        read_until("$a_manifest · FileSet [1]")
        os.write(master, b"\x1b[H\r")
        read_until(str(source.parent)[:25])
        os.write(master, b"\x1b[C\x1b[C")
        read_until("[0] · sample.cpp")
        os.write(master, b"\x1b[1;5C" * ((len(str(source)) + 25 - 44 + 7) // 8))
        read_until(
            "sample.cpp",
            recorded=lambda: any("sample.cpp" in line[92:] for line in screen.display),
        )
        (tmp_path / "workspace-fileset.txt").write_text("\n".join(screen.display))
        os.write(master, b"\x1b[18~")
        fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", 28, 100, 0, 0))
        screen.resize(lines=28, columns=100)
        os.kill(process.pid, signal.SIGWINCH)
        for failed, explanation, marked_token in [
            (";et bad = 1", "syntax error at line 1, column 1", ";"),
            ("print $missing", "error: unknown variable: missing", "$missing"),
            ("print $a_manifest[0]", "value does not support indexing", "0"),
        ]:
            commands.append(failed)
            submit(failed, explanation, success=False)
            read_until(
                "Command failed",
                recorded=lambda: any("^" in line for line in screen.display),
            )
            row = next(
                i for i, line in enumerate(screen.display) if "│ " + failed in line
            )
            col = screen.display[row].index(marked_token)
            assert screen.buffer[row][col].underscore
            assert screen.display[row + 1].index("^") == col
            (tmp_path / "workspace-errors.txt").write_text("\n".join(screen.display))
        commands.append('print "RECOVERED"')
        submit(commands[-1], "RECOVERED")
        os.write(master, b"\x1b[21~")
        # Drain terminal writes while the application restores its screen on exit.
        deadline = time.monotonic() + 10
        while process.poll() is None and time.monotonic() < deadline:
            if select.select([master], [], [], 0.05)[0]:
                try:
                    os.read(master, 65_536)
                except OSError as exc:
                    if exc.errno != errno.EIO:
                        raise
        code = process.wait(timeout=10)
        return (
            code,
            output,
            HistoryStore(tmp_path / "state/clang_tools/history.jsonl").read_commands(),
            commands,
        )
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        os.close(master)


@then("the workspace shows native results and records each command once")
def verify_workspace(workspace_run: tuple[int, str, list[str], list[str]]) -> None:
    code, output, history, commands = workspace_run
    assert code == 1, output  # Deliberate failed commands are reflected on exit.
    assert history == commands
    assert "Command failed" not in output


@when("I request the workspace with a piped script", target_fixture="piped_workspace")
def request_piped_workspace() -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--ui", "workspace"],
        input='print "piped"\n',
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
    )


@then("the command explains that the workspace requires interactive input")
def verify_piped_workspace(piped_workspace: subprocess.CompletedProcess[str]) -> None:
    assert piped_workspace.returncode == 2
    assert "requires interactive input" in piped_workspace.stderr
