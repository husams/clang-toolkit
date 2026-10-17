from __future__ import annotations

import errno
import fcntl
import json
import os
import pty
import select
import signal
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
scenarios("pipe_filters.feature")


def _example_source():
    return (Path(__file__).resolve().parents[2] / "examples/pipe_filters.ctk").read_text()


@given("an isolated pipe-filter console and class fixture", target_fixture="pipe_console")
def pipe_console(tmp_path, request, monkeypatch):
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "pipe-storage"))
    server = _launch_server("unix", tmp_path, request)
    source = tmp_path / "classes.cc"
    source.write_text(
        "namespace demo { struct Widget { int width; int height; }; "
        "struct Empty {}; struct Other { int depth; }; }\n"
    )
    library = tmp_path / "empty-lib"
    library.mkdir()
    return server, source, library


def _command(server, library, *args):
    return [str(Path(sys.executable).with_name("ctk")), "--server", server.endpoint,
            "-c", str(server.config), "--lib-dir", str(library), *args]


@when(parsers.parse('I execute syntax composition using the "{engine}" engine'),
      target_fixture="composition_output")
def composition_output(pipe_console, tmp_path, engine):
    server, source, library = pipe_console
    example = Path(__file__).resolve().parents[2] / "examples/syntax_composition.ctk"
    script = tmp_path / "composition.ctk"
    script.write_text(example.read_text() + '\n'
        'let makers = [() cxxRecordDecl(isDefinition(), hasName("demo::Widget")).bind("c")]\n'
        f'let tree = parse ({json.dumps(str(source))} + "")\n'
        'let selected = match makers[0]() in (if true then tree else null)\n'
        'print "NATIVE={selected[0].c.decl_name}"\n')
    destination = tmp_path / "composition.json"
    result = subprocess.run(
        _command(server, library, "--script-engine", engine, "--script", str(script),
                 f"output={destination}"),
        cwd=tmp_path, text=True, capture_output=True, timeout=90,
        env=dict(os.environ, NO_COLOR="1"),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout, json.loads(destination.read_text())


@then("composition prints the expected calls and saved records")
def verify_composition_output(composition_output):
    output, records = composition_output
    lines = output.splitlines()
    assert lines[:2] == ["RETURNED=42", "INDEXED=42"]
    expected = [{"name": "Other", "count": 1}, {"name": "Widget", "count": 2}]
    assert records == expected
    assert json.loads(lines[-2]) == expected
    assert lines[-1] == "NATIVE=demo::Widget"


@when(parsers.parse('I execute the complete filter script using the "{engine}" engine'),
      target_fixture="pipe_script_output")
def pipe_script_output(pipe_console, tmp_path, engine):
    server, source, library = pipe_console
    script = tmp_path / "pipeline.ctk"
    script.write_text(
        'print "BEGIN_REPORT"\n' + _example_source() + '\nprint "END_REPORT"\n'
        f'let tree = parse {json.dumps(str(source))}\n'
        'let classes = match cxxRecordDecl(isDefinition(), '
        'isExpansionInMainFile(), unless(isImplicit())).bind("class") in tree\n'
        'let names = classes | map((row) = row.class.qualified_name) | sort\n'
        'print "BEGIN_NAMES"\nprint names | json\nprint "END_NAMES"\n'
        'let fields = match fieldDecl().bind("field") in classes.class\n'
        'print "BEGIN_FIELDS"\n'
        'print fields | map((row) = row.field.decl_name) | sort | json\n'
        'print "END_FIELDS"\n'
        'foreach (index, (name, count)) in (names | zip([0, 1, 2]) | enumerate) do {\n'
        '  print "INDEX_{index}_{count}"\n}\n'
    )
    result = subprocess.run(
        _command(server, library, "--script-engine", engine, "--script", str(script)),
        cwd=Path(__file__).resolve().parents[2], text=True, capture_output=True,
        timeout=90, env=dict(os.environ, NO_COLOR="1"),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


@then("the script prints the expected records and native names")
def verify_pipe_script(pipe_script_output):
    text = pipe_script_output
    def value(section):
        return json.loads(text.split(f"BEGIN_{section}\n", 1)[1].split(f"END_{section}", 1)[0])
    assert value("REPORT") == [{"name": "Widget", "count": 5}, {"name": "Other", "count": 2}]
    assert value("NAMES") == ["demo::Empty", "demo::Other", "demo::Widget"]
    assert value("FIELDS") == [
        "demo::Other::depth", "demo::Widget::height", "demo::Widget::width"
    ]
    assert all(f"INDEX_{i}_{i}" in text for i in range(3))
    assert "error:" not in text


@when(parsers.parse('I execute list selection using the "{engine}" engine'),
      target_fixture="selection_output")
def selection_output(pipe_console, tmp_path, engine):
    server, source, library = pipe_console
    script = tmp_path / "selection.ctk"
    example = Path(__file__).resolve().parents[2] / "examples/list_selection.ctk"
    script.write_text(
        example.read_text() + '\n'
        f'let tree = parse {json.dumps(str(source))}\n'
        'let classes = match cxxRecordDecl(isDefinition(), '
        'isExpansionInMainFile(), unless(isImplicit())).bind("class") in tree\n'
        'let selected = classes[::-1]\n'
        'let row = selected[0]\n'
        'let fields = match fieldDecl().bind("field") in row.class\n'
        'print fields | map((r) = r.field.decl_name) | json\n'
        'let final = classes[-1]\n'
        'print final.class.decl_name\n'
        'let tail = classes | last(1)\n'
        'let tailrow = tail[0]\n'
        'print tailrow.class.decl_name\n'
        'print classes | length\n'
        'let direct = match fieldDecl().bind("field") in classes[-1].class\n'
        'print direct | map((r) = r.field.decl_name) | json\n'
    )
    result = subprocess.run(
        _command(server, library, "--script-engine", engine, "--script", str(script)),
        cwd=Path(__file__).resolve().parents[2], text=True, capture_output=True,
        timeout=90, env=dict(os.environ, NO_COLOR="1"),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


@then("selection prints the expected lists and retained field")
def verify_selection_output(selection_output):
    lines = selection_output.splitlines()
    assert [json.loads(line) for line in lines[:15]] == [
        50, [20, 30, 40], [30, 40, 50], [10, 30, 50],
        [50, 40, 30, 20, 10], [40, 30, 20, 10], [], 10, 50,
        [10, 20], [40, 50], [], None, None, [50, 40],
    ]
    assert lines[15:] == ['["demo::Other::depth"]', 'demo::Other', 'demo::Other', '3',
                         '["demo::Other::depth"]']


@when("I paste the tuple pipeline into the real console terminal", target_fixture="pipe_terminal")
def pipe_terminal(pipe_console, tmp_path):
    return _run_pipe_terminal(pipe_console, tmp_path)


@when(parsers.parse('I type a multiline pipeline with "{shortcut}" in the "{ui}" console'),
      target_fixture="typed_pipeline_terminal")
def typed_pipeline_terminal(pipe_console, tmp_path, shortcut, ui):
    sequence = b"\x1b[13;5u" if shortcut == "Ctrl+Enter" else b"\x1b\r"
    return _run_pipe_terminal(pipe_console, tmp_path, ui=ui, newline_sequence=sequence)


@then("the pipeline runs once with the expected result")
def verify_typed_pipeline_terminal(typed_pipeline_terminal):
    assert "KEY_PIPELINE_6_2" in typed_pipeline_terminal
    assert "error:" not in typed_pipeline_terminal


def _run_pipe_terminal(pipe_console, tmp_path, *, ui="prompt", newline_sequence=None):
    server, _, library = pipe_console
    master, slave = pty.openpty()
    fcntl.ioctl(master, termios.TIOCSWINSZ, struct.pack("HHHH", 35, 120, 0, 0))
    process = subprocess.Popen(
        _command(server, library, "--script-engine", "compiled", "--ui", ui),
        stdin=slave, stdout=slave, stderr=slave,
        cwd=Path(__file__).resolve().parents[2], close_fds=True,
        env=dict(os.environ, TERM="xterm-256color", NO_COLOR="1",
                 XDG_STATE_HOME=str(tmp_path / "state")),
    )
    os.close(slave)
    screen = pyte.Screen(120, 35)
    stream = pyte.ByteStream(screen)
    transcript = bytearray()

    def wait_for(marker, timeout=30):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if select.select([master], [], [], 0.05)[0]:
                try:
                    payload = os.read(master, 65_536)
                except OSError as error:
                    if error.errno != errno.EIO:
                        raise
                    break
                transcript.extend(payload)
                stream.feed(payload)
                if b"\x1b[6n" in payload:
                    os.write(master, f"\x1b[{screen.cursor.y + 1};{screen.cursor.x + 1}R".encode())
            elif marker in "\n".join(screen.display):
                visible = "\n".join(screen.display)
                return visible
            if process.poll() is not None:
                break
        raise AssertionError(f"Console did not show {marker!r}:\n" + "\n".join(screen.display))

    try:
        wait_for("Session open" if ui == "workspace" else "ctk>")
        if newline_sequence is not None:
            history = HistoryStore(tmp_path / "state/clang_tools/history.jsonl")
            stages = ["let key_result = [1, 2, 3]", "    | map((x) x * 2)", "    | reverse"]
            os.write(master, stages[0].encode())
            wait_for(stages[0])
            for stage in stages[1:]:
                # The editor copies the current line's indentation.
                os.write(master, newline_sequence + stage.lstrip().encode())
                wait_for(stage.strip())
                assert not history.read_commands()
            os.write(master, b"\r")
            wait_for("Ready" if ui == "workspace" else "ctk>")
            os.write(master, b'print "KEY_PIPELINE_{key_result[0]}_{key_result[2]}"\x0a')
            visible = wait_for("KEY_PIPELINE_6_2")
            commands = history.read_commands()
            assert commands[0] == "\n".join(stage.lstrip() for stage in stages)
            assert len(commands) == 2
            return visible
        script = (_example_source() + '\n'
                  + (Path(__file__).resolve().parents[2] / "examples/list_selection.ctk").read_text()
                  + '\nprint "PIPELINE_PTY_{report[0].count}_{report[1].count}"')
        os.write(master, ("\x1b[200~" + script + "\x1b[201~").encode())
        wait_for("PIPELINE_PTY_{report")
        os.write(master, b"\x0a")
        visible = wait_for("PIPELINE_PTY_5_2")
        (tmp_path / "pipe-terminal.txt").write_bytes(transcript)
        return visible
    finally:
        (tmp_path / "pipe-terminal.txt").write_bytes(transcript)
        if process.poll() is None:
            process.send_signal(signal.SIGTERM)
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        os.close(master)


@then("the terminal prints the verified tuple pipeline result")
def verify_pipe_terminal(pipe_terminal):
    assert "PIPELINE_PTY_5_2" in pipe_terminal
    assert '"Widget"' in pipe_terminal and '"Other"' in pipe_terminal
    assert "error:" not in pipe_terminal
