"""Terminal loop for the standalone LLVM IR session."""

from __future__ import annotations

from collections.abc import Callable
import json
from pathlib import Path
import subprocess
import sys

from lark.exceptions import LarkError, UnexpectedEOF, UnexpectedToken


def run_repl(
    runner: Path,
    target: Path,
    compdb: Path,
    lower: Callable[[str], str | None],
) -> int:
    interactive = sys.stdin.isatty()
    pending = ""
    had_error = False
    with subprocess.Popen(
        [str(runner), "repl", str(target), str(compdb)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        start_new_session=True,
    ) as process:
        assert process.stdin is not None and process.stdout is not None
        try:
            ready = process.stdout.readline()
            if not ready:
                return process.wait() or 1
            if ready != '{"ready":true}\n':
                raise ValueError("unexpected response from native REPL runner")
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
                if line.strip() == ":quit":
                    break
                if not pending and not line.strip():
                    continue
                pending += line + "\n"
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
                pending = ""
                if program is None:
                    continue

                process.stdin.write(json.dumps(program) + "\n")
                process.stdin.flush()
                response = process.stdout.readline()
                if not response:
                    return process.wait() or 1
                result = json.loads(response)
                if result["error"]:
                    print(f"ctk-jit: {result['error']}", file=sys.stderr)
                    had_error = True
                sys.stdout.write(result["output"])
                sys.stdout.flush()

            process.stdin.close()
            return process.wait() or int(had_error and not interactive)
        except KeyboardInterrupt:
            if process.poll() is None:
                process.terminate()
            raise
