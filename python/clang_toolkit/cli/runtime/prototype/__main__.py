"""Run the isolated scripting-runtime experiment."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from clang_toolkit.cli.runtime.values import render

from . import run_source
from .compiler import compile_program
from .syntax import parse


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default="-", help="script file, or - for stdin")
    parser.add_argument("--source", help="script text instead of a file")
    parser.add_argument("--engine", choices=("tree", "compiled"), default="compiled")
    parser.add_argument("--show-python", action="store_true", help="show generated Python without executing")
    parser.add_argument("--server", help="enable ctk(command) against this existing CTK endpoint")
    parser.add_argument("--max-steps", type=int, default=1_000_000)
    parser.add_argument("--max-items", type=int, default=10_000)
    args = parser.parse_args(argv)
    client = runtime = None
    try:
        source = args.source if args.source is not None else (
            sys.stdin.read() if args.path == "-" else Path(args.path).read_text()
        )
        if args.show_python:
            executable = compile_program(parse(source))
            print(executable.__ctk_source__)
            return 0
        functions = {}
        if args.server:
            from clang_toolkit.client import Client
            from clang_toolkit.cli.runtime import Runtime
            from .bridge import ctk_function

            client = Client(args.server)
            runtime = Runtime(client, cwd=Path.cwd())
            functions["ctk"] = ctk_function(runtime)
        result = run_source(
            source, engine=args.engine, functions=functions,
            max_steps=args.max_steps, max_items=args.max_items,
        )
        for value in result.output:
            print(render(value))
        if not result.output and result.value is not None:
            print(render(result.value))
        return 0
    except KeyboardInterrupt:
        print("Prototype execution cancelled.", file=sys.stderr)
        return 130
    except Exception as error:
        print(f"Prototype error: {error}", file=sys.stderr)
        return 1
    finally:
        if runtime is not None:
            runtime.close()
        if client is not None:
            client.close()


if __name__ == "__main__":
    raise SystemExit(main())
