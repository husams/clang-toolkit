"""Measure local console startup and key redraws in fresh Python processes.

Run with: uv run python scripts/benchmark_console_input.py
Uses installed libraries unless --lib-dir is supplied. The real workspace runs
with pipe input and a headless output; server connections, uv startup, and terminal
rendering are excluded. Existing library caches are retained between runs.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path
from statistics import median
from time import perf_counter


async def measure(directory: Path | None, columns: int) -> dict[str, float]:
    started = perf_counter()
    from unittest.mock import Mock

    from prompt_toolkit.data_structures import Size
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    from clang_toolkit.cli.app import _load_prompt_history
    from clang_toolkit.cli.prompt import create_session
    from clang_toolkit.cli.runtime.history import HistoryStore
    from clang_toolkit.cli.runtime.imports import preload_libraries
    from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
    from clang_toolkit.cli.workspace import WorkspaceConsole

    class Screen(DummyOutput):
        def get_size(self):
            return Size(rows=32, columns=columns)

    async def execute(source):
        raise AssertionError("the input benchmark must not execute commands")

    timings = {}
    history = HistoryStore()
    prompt_history = _load_prompt_history(history)
    runtime = PrototypeRuntime(Mock(), cwd=Path.cwd(), environment={}, history=history)
    try:
        preload_libraries(runtime, directory)
        with create_pipe_input() as pipe:
            screen = Screen()
            session = create_session(
                input=pipe, output=screen, history=prompt_history, script_engine="compiled",
                references=runtime.completion_references,
                field_resolver=runtime.completion_suggestions,
                presence_resolver=runtime.completion_presence_fields,
                matcher_functions=runtime.matcher_function_names,
                function_help=runtime.callable_help,
                cwd=runtime.cwd,
            )
            workspace = WorkspaceConsole(session, runtime.cwd, execute, input=pipe, output=screen)

            def rendered(app):
                if app.is_done:
                    return
                if "first_frame_seconds" not in timings:
                    timings["first_frame_seconds"] = perf_counter() - started
                    pipe.send_text("m")
                elif workspace.buffer.text == "m" and "first_key_seconds" not in timings:
                    timings["first_key_seconds"] = perf_counter() - started
                    pipe.send_text("a")
                elif workspace.buffer.text == "ma":
                    timings["second_key_seconds"] = perf_counter() - started
                    workspace.request_exit()

            workspace.app.after_render += rendered
            await workspace.run()
    finally:
        runtime.close()
    assert len(timings) == 3, "workspace closed before both keystrokes were displayed"
    return timings


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lib-dir", type=Path)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--columns", type=int, default=140)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.samples < 1 or args.columns < 20:
        parser.error("samples must be positive and columns must be at least 20")
    if args.worker:
        print(json.dumps(asyncio.run(measure(args.lib_dir, args.columns))))
        return
    command = [sys.executable, str(Path(__file__).resolve()), "--worker", "--columns", str(args.columns)]
    if args.lib_dir is not None:
        command.extend(["--lib-dir", str(args.lib_dir.expanduser().resolve())])
    samples = []
    for _ in range(args.samples):
        result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=300)
        samples.append(json.loads(result.stdout))
    print(json.dumps({
        "samples": samples,
        "median": {key: median(sample[key] for sample in samples) for key in samples[0]},
    }, indent=2))


if __name__ == "__main__":
    main()
