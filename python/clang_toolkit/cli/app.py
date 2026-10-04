"""Interactive console (prompt_toolkit) for the clang-toolkit server."""

from __future__ import annotations

import argparse

from lark.exceptions import UnexpectedInput

from clang_toolkit.cli.language import lex
from clang_toolkit.cli.prompt import create_session
from clang_toolkit.cli.runtime import EvaluationError, Runtime
from clang_toolkit.cli.runtime.config import ConfigError
from clang_toolkit.cli.runtime.history import HistoryError, HistoryStore
from clang_toolkit.cli.runtime.output import OutputError
from clang_toolkit.cli.runtime.persistence import PersistenceError
from clang_toolkit.client import Client

COMMANDS = [
    "match",
    "let",
    "print",
    "foreach",
    "set",
    "clear",
    "save",
    "load",
    "add",
    "history",
    "session",
    "cfg",
    "callgraph",
    "script",
    "help",
    "quit",
]


def dispatch(client: Client, line: str, runtime: Runtime | None = None) -> str | None:
    """Validate one sentence and evaluate it in the active REPL runtime."""
    if not line.strip():
        return "commands: " + ", ".join(COMMANDS)
    runtime = runtime or Runtime(client)
    try:
        return runtime.execute(line)
    except UnexpectedInput as exc:
        first = next(token for token in lex(line) if token.type != "WS")
        if first.type == "NAME" and str(first) not in COMMANDS:
            return f"unknown command: {first}"
        return f"syntax error at line {exc.line}, column {exc.column}"
    except (
        EvaluationError,
        ConfigError,
        PersistenceError,
        OutputError,
        HistoryError,
    ) as exc:
        return f"error: {exc}"


def main() -> None:
    parser = argparse.ArgumentParser(prog="ctk")
    parser.add_argument("--server", default="127.0.0.1:7878")
    args = parser.parse_args()

    client = Client(args.server)
    try:
        runtime = Runtime(client, history=HistoryStore())
    except (ConfigError, OutputError) as exc:
        print(f"error: {exc}")
        return
    session = create_session(references=runtime.completion_references)
    try:
        while True:
            try:
                line = session.prompt("ctk> ")
            except EOFError:
                break
            except KeyboardInterrupt:
                continue
            try:
                out = dispatch(client, line, runtime)
            except NotImplementedError as exc:
                out = f"error: {exc}"
            if out is None:
                break
            if out:
                print(out)
    finally:
        runtime.close()


if __name__ == "__main__":
    main()
