"""Measure both prototype engines with identical guarded semantics and source."""

from __future__ import annotations

import argparse
import json
import platform
import statistics
import sys
from pathlib import Path
from time import perf_counter_ns
from typing import Any, Callable

from clang_toolkit.cli.runtime.prototype.compiler import compile_program
from clang_toolkit.cli.runtime.prototype.semantics import Context
from clang_toolkit.cli.runtime.prototype.syntax import parse
from clang_toolkit.cli.runtime.prototype.tree import evaluate


def timing(operation: Callable[[], Any], repetitions: int) -> dict[str, float]:
    samples = []
    for _ in range(repetitions):
        start = perf_counter_ns()
        operation()
        samples.append((perf_counter_ns() - start) / 1_000_000)
    return {"median_ms": statistics.median(samples), "min_ms": min(samples), "max_ms": max(samples)}


def cases(items: int) -> dict[str, str]:
    return {
        "arithmetic": f"""let total = 0
foreach item in range({items}) do $total += $item * 3
$total
""",
        "conditional": f"""let total = 0
foreach item in range({items}) do $total += $item % 2 == 0 ? 1 : 3
$total
""",
        "structured": f"""let rows = foreach item in range({items}) do ({{
    index: $item,
    label: $item % 2 == 0 ? "even" : "odd",
    scaled: $item * 3
}})
{{length: $rows.length, last: $rows[{items - 1}].scaled}}
""",
        "registered_host": f"""let total = 0
foreach item in range({items}) do $total += touch($item)
$total
""",
    }


def measure(source: str, items: int, repeats: int) -> dict[str, Any]:
    start = perf_counter_ns()
    program = parse(source)
    first_parse_ms = (perf_counter_ns() - start) / 1_000_000
    start = perf_counter_ns()
    generated = compile_program(program)
    first_compile_ms = (perf_counter_ns() - start) / 1_000_000

    def context() -> Context:
        return Context(functions={"touch": lambda item: item}, max_steps=max(1_000_000, items * 100), max_items=max(10_000, items))

    outcomes = {}
    engines = {}
    for engine, execute in (("tree", lambda ctx: evaluate(program, ctx)), ("compiled", generated)):
        state = context()
        start = perf_counter_ns()
        result = execute(state)
        first_execution_ms = (perf_counter_ns() - start) / 1_000_000
        outcomes[engine] = (result, state.bindings, state.output, state.steps)
        engines[engine] = {"first_execution_ms": first_execution_ms, "execution": timing(lambda: execute(context()), repeats)}

    assert outcomes["tree"] == outcomes["compiled"], "engines disagree on values, bindings, output or counted steps"

    def end_to_end(engine: str) -> None:
        ast = parse(source)
        state = context()
        if engine == "tree":
            evaluate(ast, state)
        else:
            compile_program(ast)(state)

    for engine in engines:
        engines[engine]["parse_and_execute"] = timing(lambda engine=engine: end_to_end(engine), repeats)
    tree_ms = engines["tree"]["execution"]["median_ms"]
    compiled_ms = engines["compiled"]["execution"]["median_ms"]
    return {
        "first_parse_ms": first_parse_ms,
        "first_compile_ms": first_compile_ms,
        "parse": timing(lambda: parse(source), repeats),
        "compile": timing(lambda: compile_program(program), repeats),
        "engines": engines,
        "tree_over_compiled_execution_ratio": tree_ms / compiled_ms,
        "checked_steps": outcomes["tree"][3],
        "result": outcomes["tree"][0],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--items", type=int, nargs="+", default=[1_000, 10_000])
    parser.add_argument("--repeats", type=int, default=7)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.repeats < 1 or any(count < 1 for count in args.items):
        parser.error("items and repeats must be positive")
    report = {
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "method": "Same source, AST, checked operations and budgets; fresh state per run. Cached parser construction; parse and compile reported separately. Registered host callback is local, not a network or Clang benchmark.",
        "repeats": args.repeats,
        "matrices": {str(count): {name: measure(source, count, args.repeats) for name, source in cases(count).items()} for count in args.items},
    }
    data = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(data)
    print(data)


if __name__ == "__main__":
    main()
