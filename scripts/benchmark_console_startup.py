"""Measure library preparation and compiled expression execution.

Run with: uv run python scripts/benchmark_console_startup.py
Use --library-dir to measure an installed helper library. Each invocation uses
an empty temporary cache; warm samples retain it, but create fresh runtimes.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path
from statistics import median
from time import perf_counter
from unittest.mock import Mock

from clang_toolkit.cli.runtime.imports import preload_libraries
from clang_toolkit.cli.runtime.prototype.compiler import compile_program
from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
from clang_toolkit.cli.runtime.prototype.semantics import Context, Node


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library-dir", type=Path)
    parser.add_argument("--iterations", type=int, default=20_000)
    args = parser.parse_args()
    if args.iterations <= 0:
        parser.error("--iterations must be positive")
    with tempfile.TemporaryDirectory(prefix="ctk-startup-benchmark-") as temporary:
        root = Path(temporary)
        os.environ["XDG_CACHE_HOME"] = str(root / "cache")
        library = args.library_dir
        if library is None:
            library = root / "lib"
            library.mkdir()
            (library / "helpers.ctk").write_text(
                'let scale(value) = { value * 2 + 1 }\n'
                'let greet(name) = { "Hi {name}" }\n'
                'let enabled(value) = { value > 0 and value < 100 }\n'
                'let first(values) = { values[0] }\n', encoding="utf-8",
            )
        startup = []
        for _ in range(4):
            start = perf_counter()
            runtime = PrototypeRuntime(Mock(), cwd=Path.cwd(), environment={})
            try:
                preload_libraries(runtime, library.resolve())
                startup.append(perf_counter() - start)
            finally:
                runtime.close()
        program = Node("binary", "+", (
            Node("binary", "*", (Node("ref", "x"), Node("literal", 2))),
            Node("literal", 1),
        ))
        execute = compile_program(program)
        execution = []
        for _ in range(7):
            context = Context({"x": 7}, max_steps=args.iterations * 10)
            start = perf_counter()
            for _ in range(args.iterations):
                execute(context)
            execution.append(perf_counter() - start)
        print(json.dumps({"cold_preload_seconds": startup[0],
                          "warm_preload_seconds": median(startup[1:]),
                          "expression_iterations": args.iterations,
                          "expression_seconds": median(execution)}, indent=2))


if __name__ == "__main__":
    main()
