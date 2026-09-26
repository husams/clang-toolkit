"""Interactive console (prompt_toolkit) for the clang-toolkit server."""

from __future__ import annotations

import argparse

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter

from clang_toolkit.client import Client

COMMANDS = ["match", "traverse", "cfg", "callgraph", "script", "help", "quit"]


def dispatch(client: Client, line: str) -> str | None:
    cmd, _, arg = line.strip().partition(" ")
    if cmd in ("quit", "exit"):
        return None
    if cmd == "help" or not cmd:
        return "commands: " + ", ".join(COMMANDS)
    if cmd == "match":
        return "\n".join(client.match(arg))
    if cmd == "cfg":
        return client.cfg(arg)
    if cmd == "callgraph":
        return client.callgraph()
    return f"unknown command: {cmd}"


def main() -> None:
    parser = argparse.ArgumentParser(prog="ctk")
    parser.add_argument("--server", default="127.0.0.1:7878")
    args = parser.parse_args()

    client = Client(args.server)
    session: PromptSession[str] = PromptSession(completer=WordCompleter(COMMANDS))
    while True:
        try:
            line = session.prompt("ctk> ")
        except (EOFError, KeyboardInterrupt):
            break
        try:
            out = dispatch(client, line)
        except NotImplementedError as exc:
            out = f"error: {exc}"
        if out is None:
            break
        print(out)


if __name__ == "__main__":
    main()
