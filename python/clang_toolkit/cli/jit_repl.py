"""Terminal loop for the standalone LLVM IR session."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from contextlib import ExitStack
import json
from pathlib import Path
from queue import Queue
import signal
import subprocess
import sys
from threading import Lock, Thread
from typing import Any, TextIO
from uuid import uuid4

from lark.exceptions import LarkError, UnexpectedEOF, UnexpectedToken
from prompt_toolkit.patch_stdout import patch_stdout

from .jit_compiler import LowerRequest, compiler_channel
from .prompt import PersistentPromptHistory, create_session
from .runtime.history import HistoryError, HistoryStore

_COMMAND_CACHE_SIZE = 128
_EXIT_COMMANDS = {":quit", "quit", "exit"}


class _RunnerClosed(OSError):
    pass


def _read_replies(
    source: TextIO,
    replies: Queue[dict[str, Any] | Exception | None],
    emit: Callable[[str], None],
    progress: Callable[[dict[str, Any]], None] | None = None,
) -> None:
    try:
        for line in source:
            message = json.loads(line)
            if "event" in message:
                emit(message["event"])
            elif "progress" in message or "durable" in message:
                if progress is not None:
                    progress(message)
            else:
                replies.put(message)
    except (OSError, ValueError) as error:
        replies.put(error)
    finally:
        replies.put(None)


def run_repl(
    runner: Path,
    target: Path | None,
    compdb: Path | None,
    lower: Callable[[str], str | None],
    arguments: dict[str, str] | None = None,
    lower_request: LowerRequest | None = None,
    *,
    workspace: bool = False,
) -> int:
    interactive = sys.stdin.isatty()
    if workspace and not interactive:
        raise ValueError("workspace requires an interactive terminal")
    pending = ""
    had_error = False
    history = HistoryStore()
    session_id = uuid4()
    label: str | None = None

    def record(source: str) -> None:
        try:
            history.append(source.removesuffix("\n"), session_id, label)
        except HistoryError as error:
            print(f"ctk-jit: {error}", file=sys.stderr)

    def history_request(action: str, value: str | None) -> None:
        nonlocal label
        if action == "save" and value is not None:
            history.save(Path.cwd() / value)
        elif action == "clear":
            history.clear()
        elif action == "label":
            label = value
        else:
            raise ValueError(f"invalid history request: {action}")

    commands: dict[str, int] = {}
    command = [str(runner), "repl", str(target or ""), str(compdb or "")]
    if arguments:
        command.append(json.dumps(arguments))
    with ExitStack() as stack:
        prompt_session = None
        if interactive:
            try:
                prompt_history = PersistentPromptHistory(history)
            except HistoryError as error:
                print(f"ctk-jit: {error}", file=sys.stderr)
                prompt_history = None
            prompt_session = create_session(
                script_engine="compiled",
                history=prompt_history,
                cwd=Path.cwd(),
                known_complete=lambda source: (
                    source + "\n" in commands
                    or source.strip().rstrip(";") in _EXIT_COMMANDS
                ),
            )
            if not workspace:
                stack.enter_context(patch_stdout(raw=True))
        options = stack.enter_context(compiler_channel(lower_request, history_request))
        process = stack.enter_context(
            subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                start_new_session=True,
                **options,
            )
        )
        assert process.stdin is not None and process.stdout is not None
        reader = None
        try:
            ready = process.stdout.readline()
            if not ready:
                return process.wait() or 1
            if ready != '{"ready":true,"protocol":3}\n':
                raise ValueError("unexpected response from native REPL runner")
            replies: Queue[dict[str, Any] | Exception | None] = Queue()
            output_lock = Lock()

            def exchange(request: dict[str, Any]) -> dict[str, Any]:
                process.stdin.write(json.dumps(request) + "\n")
                process.stdin.flush()
                result = replies.get()
                if result is None:
                    raise _RunnerClosed("native REPL runner closed")
                if isinstance(result, Exception):
                    raise result
                return result

            def submit(source: str) -> dict[str, Any] | None:
                slot = commands.get(source)
                evicted = None
                if slot is None:
                    program = lower(source)
                    if program is None:
                        record(source)
                        return None
                    if len(commands) == _COMMAND_CACHE_SIZE:
                        evicted = next(iter(commands))
                    slot = len(commands) if evicted is None else commands[evicted]
                    request = {"slot": slot, "ir": program}
                else:
                    request = {"slot": slot}
                record(source)
                if workspace:
                    request["workspace"] = True
                result = exchange(request)
                if result["compiled"]:
                    if evicted is not None:
                        del commands[evicted]
                    commands[source] = slot
                return result

            def emit_event(event: str) -> None:
                with output_lock:
                    print(event, flush=True)

            console = None
            progress_callback = None
            if workspace:
                from .jit_workspace import (
                    NativeWorkspace,
                    Outcome,
                    command_outcome,
                    batch_progress,
                )
                from .workspace import WorkspaceConsole
                from .workspace_source_data import source_snapshot

                assert prompt_session is not None
                lock = asyncio.Lock()
                native = NativeWorkspace(exchange, lock)

                async def execute(source: str) -> Outcome:
                    if source.strip().rstrip(";") in _EXIT_COMMANDS:
                        record(source)
                        return Outcome(None)
                    try:
                        async with lock:
                            result = await asyncio.to_thread(submit, source + "\n")
                    except (LarkError, ValueError, SyntaxError):
                        record(source)
                        raise
                    return (
                        command_outcome(result) if result is not None else Outcome("")
                    )

                async def read_source(target):
                    return await asyncio.to_thread(source_snapshot, target, Path.cwd())

                async def read_resources():
                    return await native.resources(frozenset(console.resources.expanded))

                async def cancel_batch(run_id):
                    return await native.batch(run_id, cancel=True)

                async def cancel():
                    process.send_signal(signal.SIGUSR1)
                    return "Cancellation requested."

                console = WorkspaceConsole(
                    prompt_session,
                    Path.cwd(),
                    execute,
                    source_reader=read_source,
                    outline=native.outline,
                    resources=read_resources,
                    result_outline=native.result,
                    server_status=native.status,
                    status_title="Local runtime",
                    batch_status=native.batch,
                    batch_cancel=cancel_batch,
                    cancel=cancel,
                )

                def progress_callback(message: dict[str, Any]) -> None:
                    console.show_batch_progress(batch_progress(message))

            reader = Thread(
                target=_read_replies,
                args=(
                    process.stdout,
                    replies,
                    console.write_output if console else emit_event,
                    progress_callback,
                ),
                name="ctk-jit-replies",
                daemon=True,
            )
            reader.start()
            if console:
                had_error = bool(asyncio.run(console.run()))
            while console is None:
                try:
                    line = (
                        prompt_session.prompt("ctk-jit> ")
                        if prompt_session
                        else input()
                    )
                except KeyboardInterrupt:
                    if not interactive:
                        raise
                    pending = ""
                    continue
                except EOFError:
                    if pending:
                        print(
                            "ctk-jit: incomplete statement at end of input",
                            file=sys.stderr,
                        )
                        had_error = True
                    break
                if not pending and line.strip().rstrip(";") in _EXIT_COMMANDS:
                    record(line)
                    break
                if not pending and not line.strip():
                    continue
                pending += line + "\n"
                # A cached multiline command already established which of its
                # line prefixes need another line.
                if pending not in commands and any(
                    command.startswith(pending) for command in commands
                ):
                    continue
                try:
                    result = submit(pending)
                except _RunnerClosed:
                    return process.wait() or 1
                except (LarkError, ValueError, SyntaxError) as error:
                    if isinstance(error, UnexpectedEOF) or (
                        isinstance(error, UnexpectedToken)
                        and error.token.type == "$END"
                    ):
                        continue
                    record(pending)
                    print(f"ctk-jit: {error}", file=sys.stderr)
                    had_error = True
                    result = None
                pending = ""
                if result is None:
                    continue
                if result["error"]:
                    print(f"ctk-jit: {result['error']}", file=sys.stderr)
                    had_error = True
                with output_lock:
                    sys.stdout.write(result["output"])
                    sys.stdout.flush()
                if result.get("exit"):
                    break

            process.stdin.close()
            status = process.wait()
            reader.join()
            return status or int(had_error and (workspace or not interactive))
        except KeyboardInterrupt:
            if process.poll() is None:
                process.terminate()
            raise
        finally:
            if not process.stdin.closed:
                process.stdin.close()
            if reader is not None and reader.is_alive():
                reader.join(timeout=1)
