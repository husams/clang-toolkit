from __future__ import annotations

import asyncio
import json
from unittest.mock import Mock
from uuid import uuid4

from clang_toolkit.cli.app import _load_prompt_history, dispatch
from clang_toolkit.cli.prompt import PersistentPromptHistory, create_session
from clang_toolkit.cli.runtime import Runtime
from clang_toolkit.cli.runtime.history import HistoryStore
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput


def _write_record(path, command: str, label: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {"command": command, "session_id": "session", "label": label}
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(record) + "\n")


def test_prompt_history_restores_multiline_commands_newest_first(tmp_path):
    store = HistoryStore(tmp_path / "history.jsonl")
    _write_record(store.path, 'match functionDecl(\n    hasName("f")\n)')
    _write_record(store.path, "print $functions")

    history = PersistentPromptHistory(store)

    assert list(history.load_history_strings()) == [
        "print $functions",
        'match functionDecl(\n    hasName("f")\n)',
    ]


def test_history_store_respects_xdg_state_home(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))

    assert HistoryStore().path == tmp_path / "state/clang_tools/history.jsonl"


def test_history_preserves_unicode_line_separators_inside_a_command(tmp_path):
    from uuid import uuid4

    store = HistoryStore(tmp_path / "history.jsonl")
    command = 'print "before\u2028after\u2029end"'
    store.append(command, uuid4(), None)

    assert store.read_commands() == [command]


def test_prompt_history_submission_does_not_write_a_duplicate(tmp_path):
    store = HistoryStore(tmp_path / "history.jsonl")
    runtime = Runtime(Mock(), cwd=tmp_path, environment={}, history=store)
    prompt_history = PersistentPromptHistory(store)
    command = "let answer = true"

    prompt_history.append_string(command)
    assert dispatch(runtime.client, command, runtime) == ""

    records = [json.loads(line) for line in store.path.read_text().splitlines()]
    assert [record["command"] for record in records] == [command]
    assert prompt_history.get_strings() == [command]
    runtime.close()


def test_ctrl_r_search_accepts_then_submits_the_full_multiline_entry(tmp_path):
    async def run():
        with create_pipe_input() as pipe:
            store = HistoryStore(tmp_path / "history.jsonl")
            command = 'match functionDecl(\n    hasName("needle")\n)'
            _write_record(store.path, command)
            session = create_session(
                input=pipe,
                output=DummyOutput(),
                history=PersistentPromptHistory(store),
            )
            task = asyncio.create_task(session.prompt_async("ctk> "))
            for _ in range(100):
                loader = session.default_buffer._load_history_task
                if loader is not None and loader.done():
                    break
                await asyncio.sleep(0.01)

            pipe.send_text("\x12needle")
            for _ in range(100):
                if session.app.layout.search_target_buffer_control is not None:
                    break
                await asyncio.sleep(0.01)
            pipe.send_text("\r")
            for _ in range(100):
                if session.app.layout.search_target_buffer_control is None:
                    break
                await asyncio.sleep(0.01)

            assert session.default_buffer.text == command
            assert session.default_buffer.cursor_position == len(command)
            pipe.send_text("\r")
            return await asyncio.wait_for(task, 2)

    assert asyncio.run(run()) == 'match functionDecl(\n    hasName("needle")\n)'


def test_syntax_failure_is_persisted_once_with_current_session_label(tmp_path):
    store = HistoryStore(tmp_path / "history.jsonl")
    runtime = Runtime(Mock(), cwd=tmp_path, environment={}, history=store)
    dispatch(runtime.client, 'session label "debugging"', runtime)

    result = dispatch(runtime.client, "let answer = true trailing", runtime)

    assert "syntax error" in result
    records = [json.loads(line) for line in store.path.read_text().splitlines()]
    assert [record["command"] for record in records] == [
        'session label "debugging"',
        "let answer = true trailing",
    ]
    assert records[0]["label"] is None
    assert records[1]["label"] == "debugging"
    runtime.close()


def test_clear_history_also_clears_prompt_recall_cache(tmp_path):
    store = HistoryStore(tmp_path / "history.jsonl")
    runtime = Runtime(Mock(), cwd=tmp_path, environment={}, history=store)
    prompt_history = PersistentPromptHistory(store)
    prompt_history.append_string("previous command")
    dispatch(runtime.client, "let answer = true", runtime)

    assert dispatch(runtime.client, "history clear", runtime) == ""

    assert store.path.read_text() == ""
    assert prompt_history.get_strings() == []
    runtime.close()


def test_clear_history_removes_entries_from_the_reused_prompt_buffer(tmp_path):
    async def run():
        with create_pipe_input() as pipe:
            store = HistoryStore(tmp_path / "history.jsonl")
            runtime = Runtime(Mock(), cwd=tmp_path, environment={}, history=store)
            history = PersistentPromptHistory(store)
            session = create_session(input=pipe, output=DummyOutput(), history=history)

            first = asyncio.create_task(session.prompt_async("ctk> "))
            pipe.send_text("help\r")
            assert await asyncio.wait_for(first, 2) == "help"
            dispatch(runtime.client, "help", runtime)
            assert "help" in session.default_buffer._working_lines
            dispatch(runtime.client, "history clear", runtime)

            second = asyncio.create_task(session.prompt_async("ctk> "))
            for _ in range(100):
                loader = session.default_buffer._load_history_task
                if loader is not None and loader.done():
                    break
                await asyncio.sleep(0.01)
            pipe.send_text("\x1b[A")
            await asyncio.sleep(0.05)
            assert session.default_buffer.text == ""
            pipe.send_text("exit\r")
            assert await asyncio.wait_for(second, 2) == "exit"
            runtime.close()

    asyncio.run(run())


def test_read_skips_malformed_or_truncated_records_but_keeps_valid_ones(tmp_path):
    store = HistoryStore(tmp_path / "history.jsonl")
    _write_record(store.path, "first")
    with store.path.open("a", encoding="utf-8") as stream:
        stream.write('{"command":"truncated"\nnot-json\n')
    _write_record(store.path, "last")

    assert store.read_commands() == ["first", "last"]


def test_append_separates_new_record_from_unterminated_truncated_tail(tmp_path):
    store = HistoryStore(tmp_path / "history.jsonl")
    store.path.parent.mkdir(parents=True, exist_ok=True)
    old_bytes = b'{"command":"old"}\n{"command":"broken'
    store.path.write_bytes(old_bytes)
    session_id = uuid4()

    store.append("new command", session_id, "test-session")

    content = store.path.read_bytes()
    assert content.startswith(old_bytes + b"\n")
    records = [
        json.loads(line)
        for line in content.decode("utf-8").splitlines()
        if line.startswith("{") and line.endswith("}")
    ]
    assert [record["command"] for record in records] == ["old", "new command"]
    assert records[-1]["session_id"] == str(session_id)
    assert records[-1]["label"] == "test-session"
    assert store.read_commands() == ["old", "new command"]


def test_unreadable_history_is_reported_instead_of_being_treated_as_empty(
    tmp_path, monkeypatch, capsys
):
    store = HistoryStore(tmp_path / "history.jsonl")
    store.path.parent.mkdir(parents=True, exist_ok=True)
    store.path.touch()
    read_text = type(store.path).read_text

    def unreadable(path, *args, **kwargs):
        if path == store.path:
            raise PermissionError("permission denied")
        return read_text(path, *args, **kwargs)

    monkeypatch.setattr(type(store.path), "read_text", unreadable)

    assert _load_prompt_history(store) is None
    output = capsys.readouterr().out
    assert "cannot read history: permission denied" in output
    assert "persistent history disabled" in output
