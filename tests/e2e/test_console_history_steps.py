"""Key-driven persistent command-history checks with real prompt sessions."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import Mock

from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput
from pytest_bdd import given, scenarios, then, when

from clang_toolkit.cli.app import dispatch
from clang_toolkit.cli.prompt import PersistentPromptHistory, create_session
from clang_toolkit.cli.runtime import Runtime
from clang_toolkit.cli.runtime.history import HistoryStore
from clang_toolkit.client import Client

scenarios("console_history.feature")


async def _wait_for_text(session, expected: str) -> None:
    for _ in range(300):
        if session.default_buffer.text == expected:
            return
        await asyncio.sleep(0.01)
    raise AssertionError(
        f"expected prompt text {expected!r}, got {session.default_buffer.text!r}"
    )


async def _submit_prompt_command(
    runtime: Runtime, store: HistoryStore, command: str
) -> str:
    with create_pipe_input() as pipe:
        session = create_session(
            input=pipe,
            output=DummyOutput(),
            history=PersistentPromptHistory(store),
        )
        task = asyncio.create_task(session.prompt_async("ctk> "))
        try:
            expected = ""
            for index, part in enumerate(command.split("\n")):
                if index:
                    pipe.send_text("\r")
                    expected += "\n"
                    await _wait_for_text(session, expected)
                pipe.send_text(part)
                expected += part
                await _wait_for_text(session, expected)
            pipe.send_text("\r")
            submitted = await asyncio.wait_for(task, 3)
            assert submitted == command
            output = dispatch(runtime.client, submitted, runtime)
            assert output is not None
            assert not output.startswith(("error:", "syntax error")), output
            return submitted
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)


async def _navigate_history(store: HistoryStore, draft: str):
    with create_pipe_input() as pipe:
        session = create_session(
            input=pipe,
            output=DummyOutput(),
            history=PersistentPromptHistory(store),
        )
        task = asyncio.create_task(session.prompt_async("ctk> "))
        try:
            pipe.send_text(draft)
            await _wait_for_text(session, draft)
            pipe.send_text("\x1b[A")
            latest = store.read_commands()[-1]
            await _wait_for_text(session, latest)
            pipe.send_text("\x1b[A")
            older = store.read_commands()[-2]
            await _wait_for_text(session, older)
            pipe.send_text("\x1b[B")
            await _wait_for_text(session, latest)
            pipe.send_text("\x1b[B")
            await _wait_for_text(session, draft)
            return latest, older, session.default_buffer.text
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)


async def _accept_up_history(store: HistoryStore) -> str:
    with create_pipe_input() as pipe:
        session = create_session(
            input=pipe,
            output=DummyOutput(),
            history=PersistentPromptHistory(store),
        )
        task = asyncio.create_task(session.prompt_async("ctk> "))
        try:
            command = store.read_commands()[-1]
            pipe.send_text("\x1b[A")
            await _wait_for_text(session, command)
            pipe.send_text("\r")
            return await asyncio.wait_for(task, 3)
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)


async def _reverse_search_and_submit(store: HistoryStore, query: str) -> str:
    with create_pipe_input() as pipe:
        session = create_session(
            input=pipe,
            output=DummyOutput(),
            history=PersistentPromptHistory(store),
        )
        task = asyncio.create_task(session.prompt_async("ctk> "))
        try:
            pipe.send_text("\x12")
            pipe.send_text(query)
            command = next(
                item
                for item in reversed(store.read_commands())
                if query in item
            )
            # First Enter accepts the reverse-search result; the second submits it.
            pipe.send_text("\r")
            await _wait_for_text(session, command)
            pipe.send_text("\r")
            return await asyncio.wait_for(task, 3)
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)


async def _up_keeps_draft(store: HistoryStore, draft: str) -> str:
    with create_pipe_input() as pipe:
        session = create_session(
            input=pipe,
            output=DummyOutput(),
            history=PersistentPromptHistory(store),
        )
        task = asyncio.create_task(session.prompt_async("ctk> "))
        try:
            pipe.send_text(draft)
            await _wait_for_text(session, draft)
            pipe.send_text("\x1b[A")
            await asyncio.sleep(0.05)
            return session.default_buffer.text
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)


def _records(store: HistoryStore) -> list[dict[str, object]]:
    return [json.loads(line) for line in store.path.read_text().splitlines()]


@given("an isolated console history file", target_fixture="history_file")
def history_file(tmp_path: Path) -> Path:
    return tmp_path / "console-history.jsonl"


@when(
    "I submit commands and navigate history after restarting the prompt",
    target_fixture="navigation_result",
)
def submit_and_navigate(history_file: Path):
    store = HistoryStore(history_file)
    first_runtime = Runtime(
        Mock(spec=Client), cwd=history_file.parent, environment={}, history=store
    )
    commands = ['print "older entry"', 'print "newest distinctive entry"']
    try:
        for command in commands:
            assert asyncio.run(_submit_prompt_command(first_runtime, store, command)) == command
        records = _records(store)
    finally:
        first_runtime.close()

    restarted_store = HistoryStore(history_file)
    restarted_runtime = Runtime(
        Mock(spec=Client),
        cwd=history_file.parent,
        environment={},
        history=restarted_store,
    )
    try:
        recalled = asyncio.run(_navigate_history(restarted_store, 'print "editing draft"'))
        return records, recalled
    finally:
        restarted_runtime.close()


@then("history returns commands newest first and restores the draft")
def verify_navigation(navigation_result):
    records, recalled = navigation_result
    commands = [record["command"] for record in records]
    assert commands == ['print "older entry"', 'print "newest distinctive entry"']
    assert all(commands.count(command) == 1 for command in commands)
    assert recalled == (commands[1], commands[0], 'print "editing draft"')


@when(
    "I save and recall a multiline command through fresh prompts",
    target_fixture="multiline_history_result",
)
def save_and_recall_multiline(history_file: Path):
    command = 'let values = [1,\n2]'
    store = HistoryStore(history_file)
    runtime = Runtime(
        Mock(spec=Client), cwd=history_file.parent, environment={}, history=store
    )
    try:
        submitted = asyncio.run(_submit_prompt_command(runtime, store, command))
        records = _records(store)
    finally:
        runtime.close()
    restarted_store = HistoryStore(history_file)
    recalled = asyncio.run(_accept_up_history(restarted_store))
    return command, submitted, recalled, records, restarted_store.read_commands()


@then("history preserves the exact multiline command as one record")
def verify_multiline_history(multiline_history_result):
    command, submitted, recalled, records, restored = multiline_history_result
    assert submitted == recalled == command
    assert restored == [command]
    assert [record["command"] for record in records] == [command]


@when(
    "I reverse-search history and accept the matching command",
    target_fixture="reverse_search_result",
)
def reverse_search_history(history_file: Path):
    store = HistoryStore(history_file)
    runtime = Runtime(
        Mock(spec=Client), cwd=history_file.parent, environment={}, history=store
    )
    commands = ['print "older marker"', 'print "unique-recall-marker-2026"']
    try:
        for command in commands:
            asyncio.run(_submit_prompt_command(runtime, store, command))
    finally:
        runtime.close()

    restarted_store = HistoryStore(history_file)
    restarted_runtime = Runtime(
        Mock(spec=Client),
        cwd=history_file.parent,
        environment={},
        history=restarted_store,
    )
    try:
        recalled = asyncio.run(
            _reverse_search_and_submit(restarted_store, "unique-recall-marker")
        )
        dispatch(restarted_runtime.client, recalled, restarted_runtime)
        records = [record["command"] for record in _records(restarted_store)]
        return commands, recalled, records
    finally:
        restarted_runtime.close()


@then("the prompt submits the exact saved command")
def verify_reverse_search(reverse_search_result):
    commands, recalled, records = reverse_search_result
    assert recalled == commands[-1]
    assert records == [*commands, commands[-1]]
    assert records.count(commands[0]) == 1
    assert records.count(commands[-1]) == 2  # one initial entry and one resubmission


@when("I clear history and restart the prompt", target_fixture="clear_history_result")
def clear_history_and_restart(history_file: Path):
    store = HistoryStore(history_file)
    runtime = Runtime(
        Mock(spec=Client), cwd=history_file.parent, environment={}, history=store
    )
    try:
        asyncio.run(_submit_prompt_command(runtime, store, 'print "to be cleared"'))
        cached_history = PersistentPromptHistory(store)
        assert dispatch(runtime.client, "history clear", runtime) == ""
        assert cached_history.get_strings() == []
    finally:
        runtime.close()

    restarted_store = HistoryStore(history_file)
    restarted_runtime = Runtime(
        Mock(spec=Client),
        cwd=history_file.parent,
        environment={},
        history=restarted_store,
    )
    try:
        assert restarted_store.read_commands() == []
        return asyncio.run(_up_keeps_draft(restarted_store, 'print "fresh draft"'))
    finally:
        restarted_runtime.close()


@then("Up has no saved command to recall")
def verify_cleared_history(clear_history_result):
    assert clear_history_result == 'print "fresh draft"'
