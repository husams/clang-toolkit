"""Terminal loop for the standalone LLVM IR session."""

from __future__ import annotations

from collections.abc import Callable
from contextlib import ExitStack
import json
from pathlib import Path
from queue import Queue
import subprocess
import sys
from threading import Lock, Thread
from typing import Any, TextIO

from lark.exceptions import LarkError, UnexpectedEOF, UnexpectedToken

from .jit_compiler import LowerRequest, compiler_channel

_COMMAND_CACHE_SIZE = 128


def _read_replies(
    source: TextIO, replies: Queue[dict[str, Any] | Exception | None], output_lock: Lock
) -> None:
    try:
        for line in source:
            message = json.loads(line)
            if "event" in message:
                with output_lock:
                    print(message["event"], flush=True)
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
) -> int:
    interactive = sys.stdin.isatty()
    pending = ""
    had_error = False
    commands: dict[str, int] = {}
    command = [str(runner), "repl", str(target or ""), str(compdb or "")]
    if arguments:
        command.append(json.dumps(arguments))
    with ExitStack() as stack:
        options = stack.enter_context(compiler_channel(lower_request))
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
            reader = Thread(
                target=_read_replies,
                args=(process.stdout, replies, output_lock),
                name="ctk-jit-replies",
                daemon=True,
            )
            reader.start()
            while True:
                prompt = ("... " if pending else "ctk-jit> ") if interactive else ""
                try:
                    line = input(prompt)
                except EOFError:
                    if pending:
                        print(
                            "ctk-jit: incomplete statement at end of input",
                            file=sys.stderr,
                        )
                        had_error = True
                    break
                if not pending and line.strip().rstrip(";") in {
                    ":quit",
                    "quit",
                    "exit",
                }:
                    break
                if not pending and not line.strip():
                    continue
                pending += line + "\n"
                slot = commands.get(pending)
                evicted = None
                if slot is None:
                    # A cached multiline command already established which
                    # of its line prefixes need another line.
                    if any(command.startswith(pending) for command in commands):
                        continue
                    try:
                        program = lower(pending)
                    except (LarkError, ValueError, SyntaxError) as error:
                        if isinstance(error, UnexpectedEOF) or (
                            isinstance(error, UnexpectedToken)
                            and error.token.type == "$END"
                        ):
                            continue
                        print(f"ctk-jit: {error}", file=sys.stderr)
                        pending = ""
                        had_error = True
                        continue
                    if program is None:
                        pending = ""
                        continue
                    if len(commands) == _COMMAND_CACHE_SIZE:
                        evicted = next(iter(commands))
                    slot = len(commands) if evicted is None else commands[evicted]
                    request = {"slot": slot, "ir": program}
                else:
                    request = {"slot": slot}

                process.stdin.write(json.dumps(request) + "\n")
                process.stdin.flush()
                result = replies.get()
                if result is None:
                    return process.wait() or 1
                if isinstance(result, Exception):
                    raise result
                if result["compiled"]:
                    if evicted is not None:
                        del commands[evicted]
                    commands[pending] = slot
                pending = ""
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
            return status or int(had_error and not interactive)
        except KeyboardInterrupt:
            if process.poll() is None:
                process.terminate()
            raise
        finally:
            if not process.stdin.closed:
                process.stdin.close()
            if reader is not None and reader.is_alive():
                reader.join(timeout=1)
