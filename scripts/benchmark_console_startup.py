"""Measure library preparation and compiled expression execution.

Run with: uv run python scripts/benchmark_console_startup.py
Use --library-dir to measure an installed helper library. Each invocation uses
an empty temporary cache; every sample starts a fresh Python process.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from statistics import median
from time import perf_counter
from unittest.mock import Mock

from clang_toolkit.cli.runtime.imports import preload_libraries
from clang_toolkit.cli.runtime.prototype.compiler import compile_program
from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
from clang_toolkit.cli.runtime.prototype.semantics import Context, Node


def preload_once(library: Path) -> float:
    start = perf_counter()
    runtime = PrototypeRuntime(Mock(), cwd=Path.cwd(), environment={})
    try:
        preload_libraries(runtime, library.resolve())
        return perf_counter() - start
    finally:
        runtime.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library-dir", type=Path)
    parser.add_argument("--iterations", type=int, default=20_000)
    parser.add_argument("--preload-once", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.preload_once is not None:
        print(json.dumps(preload_once(args.preload_once)))
        return
    if args.iterations <= 0:
        parser.error("--iterations must be positive")
    with tempfile.TemporaryDirectory(prefix="ctk-startup-benchmark-") as temporary:
        root = Path(temporary)
        environment = dict(os.environ, XDG_CACHE_HOME=str(root / "cache"))
        library = args.library_dir.expanduser() if args.library_dir is not None else None
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
        process_startup = []
        for _ in range(4):
            start = perf_counter()
            worker = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--preload-once", str(library.resolve())],
                env=environment, capture_output=True, text=True, check=True,
            )
            process_startup.append(perf_counter() - start)
            startup.append(json.loads(worker.stdout))
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
        print(json.dumps({"cold_process_seconds": process_startup[0],
                          "warm_process_seconds": median(process_startup[1:]),
                          "cold_preload_seconds": startup[0],
                          "warm_preload_seconds": median(startup[1:]),
                          "expression_iterations": args.iterations,
                          "expression_seconds": median(execution)}, indent=2))


if __name__ == "__main__":
    main()
