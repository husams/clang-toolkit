"""Interactive console (prompt_toolkit) for the clang-toolkit server."""

from __future__ import annotations

import argparse
import asyncio
import inspect
import signal
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import FrameType
from typing import Any

from lark.exceptions import UnexpectedInput

from clang_toolkit.cli.language import lex, parser as command_parser
from clang_toolkit.cli.help import COMMANDS, render_help
from clang_toolkit.cli.syntax_diagnostics import (
    syntax_diagnostic,
    unknown_command_diagnostic,
)
from clang_toolkit.cli.batch import batch_requirements, execute_batch
from clang_toolkit.cli.runtime.batch_execution import BatchInterrupted
from clang_toolkit.cli.prompt import PersistentPromptHistory, create_session
from clang_toolkit.cli.runtime import EvaluationError, Runtime
from clang_toolkit.cli.runtime.imports import script_source
from clang_toolkit.cli.runtime.config import ConfigError
from clang_toolkit.cli.runtime.history import HistoryError, HistoryStore
from clang_toolkit.cli.runtime.output import OutputError
from clang_toolkit.cli.runtime.persistence import PersistenceError
from clang_toolkit.client import AsyncClient, Client, QueryError, _format_event
from clang_toolkit.cursors import CursorError
from clang_toolkit.match_values import MatchValueError
from clang_toolkit.analysis_error import AnalysisError
from clang_toolkit.configuration import ConfigurationError, load_network_config
from clang_toolkit.version import client_version

_SESSION_CLOSE_TIMEOUT = 5.0
_BATCH_RUNNER_CANCEL_TIMEOUT = 30.0


@dataclass(frozen=True)
class DispatchResult:
    output: str | None
    success: bool


class _SessionCompletionTracker:
    """Correlate session commands with their response events."""

    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._controls: dict[str, object] = {}
        self._rejections: dict[str, object] = {}
        self._latest_progress: dict[str, object] = {}
        self._ready: dict[str, asyncio.Event] = {}
        self.accepted_files = 0
        self._error: BaseException | None = None
        self._finished = False

    def observe(self, event: object) -> None:
        kind = event.WhichOneof("event")
        request_id = event.request_id
        if kind == "control" and event.control.action == "files-accepted":
            self.accepted_files += 1
        if kind == "control":
            self._controls[request_id] = event
        elif kind == "rejected":
            self._rejections[request_id] = event
        elif kind == "progress":
            self._latest_progress[request_id] = event
        else:
            # Match rows can carry large semantic payloads. They are rendered
            # by the reader and are never needed for command completion.
            return
        ready = self._ready.get(request_id)
        if ready is not None:
            ready.set()

    def fail(self, error: BaseException) -> None:
        self._error = error
        self._finished = True
        for ready in self._ready.values():
            ready.set()

    def finish(self) -> None:
        self._finished = True
        for ready in self._ready.values():
            ready.set()

    async def wait_for(self, request_id: str, command: str) -> object:
        ready = self._ready.setdefault(request_id, asyncio.Event())
        try:
            while True:
                if self._error is not None:
                    raise self._error
                rejection = self._rejections.get(request_id)
                if rejection is not None:
                    return rejection
                control = self._controls.get(request_id)
                if command == "match":
                    if (
                        self.accepted_files == 0
                        and control is not None
                        and control.control.action == "matching"
                    ):
                        return control
                    progress = self._latest_progress.get(request_id)
                    if (
                        progress is not None
                        and progress.progress.completed_files
                        >= progress.progress.accepted_files
                    ):
                        return progress
                elif control is not None:
                    return control
                if self._finished:
                    raise QueryError(
                        f"query session ended before {command} request {request_id} received completion evidence"
                    )
                ready.clear()
                await ready.wait()
        finally:
            self._controls.pop(request_id, None)
            self._rejections.pop(request_id, None)
            self._latest_progress.pop(request_id, None)
            self._ready.pop(request_id, None)

    def wait_from_thread(self, request_id: str, command: str) -> object:
        future = asyncio.run_coroutine_threadsafe(
            self.wait_for(request_id, command), self._loop
        )
        return future.result()


def dispatch_result(
    client: Client, line: str, runtime: Runtime | None = None
) -> DispatchResult:
    """Validate one sentence and evaluate it in the active REPL runtime."""
    if not line.strip():
        return DispatchResult("", True)
    try:
        statement = command_parser().parse(line).children[0]
        if statement.data in {"help", "help_shortcut"}:
            if runtime is not None and runtime.history is not None:
                runtime.history.append(line, runtime.session_id, runtime.label)
            return DispatchResult(render_help(statement), True)
        runtime = runtime or Runtime(client)
        return DispatchResult(runtime.execute(line), True)
    except UnexpectedInput as exc:
        if runtime is not None and runtime.history is not None:
            try:
                runtime.history.append(line, runtime.session_id, runtime.label)
            except HistoryError as history_error:
                return DispatchResult(f"error: {history_error}", False)
        first = next(token for token in lex(line) if token.type != "WS")
        if first.type == "NAME" and str(first) not in COMMANDS:
            return DispatchResult(
                unknown_command_diagnostic(line, str(first), COMMANDS), False
            )
        return DispatchResult(syntax_diagnostic(line, exc), False)
    except (
        EvaluationError,
        ConfigError,
        ConfigurationError,
        QueryError,
        PersistenceError,
        OutputError,
        HistoryError,
        CursorError,
        MatchValueError,
        NotImplementedError,
        AnalysisError,
    ) as exc:
        return DispatchResult(f"error: {exc}", False)


def dispatch(client: Client, line: str, runtime: Runtime | None = None) -> str | None:
    """Backward-compatible display-only dispatcher."""
    return dispatch_result(client, line, runtime).output


def _load_prompt_history(store: HistoryStore) -> PersistentPromptHistory | None:
    try:
        return PersistentPromptHistory(store)
    except HistoryError as exc:
        print(f"error: {exc}; persistent history disabled for this session")
        return None


async def _run_batch_with_interrupts(
    runtime: Runtime,
    runner: Callable[[], Any],
    *,
    async_client: AsyncClient | None = None,
    on_interrupt: Callable[[], Any] | None = None,
) -> tuple[Any | None, bool]:
    """Run sync SDK work off-loop while the main thread owns SIGINT handling."""
    loop = asyncio.get_running_loop()
    previous_handler = signal.getsignal(signal.SIGINT)
    cancel_task: asyncio.Task[None] | None = None

    def interrupt_once(signum: int, frame: FrameType | None) -> None:
        nonlocal cancel_task
        runtime.request_batch_cancel()
        if cancel_task is None or cancel_task.done():
            cancel_task = loop.create_task(cancel_active_scope())

    async def cancel_active_scope() -> None:
        if on_interrupt is not None:
            try:
                interrupted = on_interrupt()
                if inspect.isawaitable(interrupted):
                    await interrupted
            except Exception as exc:
                print(f"error: batch session cancellation was not confirmed: {exc}")
        # Scope creation is atomic, but SIGINT can arrive while admission is
        # still in flight. Wait briefly for its acknowledged scope handle.
        deadline = loop.time() + _SESSION_CLOSE_TIMEOUT
        while runtime._active_resource_scope is None and loop.time() < deadline:
            if runner_task.done():
                return
            await asyncio.sleep(0.02)
        scope = runtime._active_resource_scope
        if scope is None:
            return
        try:
            async with asyncio.timeout(_SESSION_CLOSE_TIMEOUT):
                if async_client is not None:
                    await async_client.cancel_resource_scope(
                        scope.resource_scope_id
                    )
                else:
                    await asyncio.to_thread(scope.cancel)
        except Exception as exc:
            print(f"error: batch scope cancellation was not confirmed: {exc}")

    signal.signal(signal.SIGINT, interrupt_once)
    runner_task = asyncio.create_task(asyncio.to_thread(runner))
    interrupted = False
    try:
        try:
            result = await asyncio.shield(runner_task)
        except BatchInterrupted:
            result = None
            interrupted = True
        if runtime._batch_cancel_requested.is_set():
            interrupted = True
        if cancel_task is not None:
            await asyncio.gather(cancel_task, return_exceptions=True)
        return result, interrupted
    except asyncio.CancelledError:
        # Protect the worker-owned Runtime stacks from asyncio's cancellation
        # path too (for example, a caller cancelling _run() directly).
        runtime.request_batch_cancel()
        if cancel_task is None:
            cancel_task = loop.create_task(cancel_active_scope())
        # asyncio.Runner may receive SIGINT just before our temporary handler
        # is installed. Run the same service/scope cancellation hook before
        # joining the worker in that race too.
        await asyncio.gather(cancel_task, return_exceptions=True)
        try:
            await asyncio.wait_for(
                asyncio.shield(runner_task), timeout=_BATCH_RUNNER_CANCEL_TIMEOUT
            )
        except asyncio.TimeoutError:
            print(
                "batch cancellation is still draining; waiting for the runner "
                "to finish before releasing local state"
            )
            await asyncio.shield(runner_task)
        except BatchInterrupted:
            pass
        if cancel_task is not None:
            await asyncio.gather(cancel_task, return_exceptions=True)
        return None, True
    finally:
        # Joining must precede Runtime.close(), which mutates the same lexical
        # stacks the runner owns. Do not falsely report a successful join.
        if not runner_task.done():
            runtime.request_batch_cancel()
            if cancel_task is None:
                cancel_task = loop.create_task(cancel_active_scope())
            try:
                await asyncio.shield(runner_task)
            except BatchInterrupted:
                pass
        if cancel_task is not None and not cancel_task.done():
            await asyncio.gather(cancel_task, return_exceptions=True)
        signal.signal(signal.SIGINT, previous_handler)


async def _prompt(session, prompt: str) -> str:
    prompt_async = getattr(session, "prompt_async", None)
    if prompt_async is not None and inspect.iscoroutinefunction(prompt_async):
        return await prompt_async(prompt)
    return await asyncio.to_thread(session.prompt, prompt)


async def _run() -> int:
    parser = argparse.ArgumentParser(
        prog="ctk",
        description="Interactive console or noninteractive console-script runner.",
        epilog=(
            "With a nonterminal stdin and no --query, input runs as a batch script. "
            "Batch commands may be separated by newlines or semicolons; execution "
            "stops at the first failed command unless --continue-on-error is set."
        ),
    )
    parser.add_argument(
        "--version", action="version", version=client_version().format("ctk")
    )
    parser.add_argument(
        "--server-version",
        action="store_true",
        help="print the connected server version and exit",
    )
    parser.add_argument(
        "--compile-commands", help="server-side compile_commands.json file or directory"
    )
    parser.add_argument("--server", help="override the configured gRPC endpoint")
    parser.add_argument("-c", "--cofing", "--config-path", dest="config_path")
    parser.add_argument("--print-config", action="store_true")
    parser.add_argument("--query", help="run one query expression")
    batch_args = parser.add_mutually_exclusive_group()
    batch_args.add_argument(
        "-e",
        "--execute",
        dest="execute_text",
        help="execute console script text and exit",
    )
    batch_args.add_argument(
        "--script", help="execute commands from a script file and exit"
    )
    parser.add_argument(
        "--continue-on-error",
        action="store_true",
        help="continue a batch after failed commands (batch input only)",
    )
    parser.add_argument(
        "--file", action="append", default=[], help="query input file (repeatable)"
    )
    parser.add_argument(
        "--background",
        action="store_true",
        help="run --query while the prompt remains active",
    )
    parser.add_argument("--session", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

    batch_source: str | None = None
    batch_source_path: Path | None = None
    if args.execute_text is not None:
        batch_source = args.execute_text
    elif args.script is not None:
        try:
            batch_source_path = Path(args.script).resolve()
            batch_source = batch_source_path.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"error: cannot read script {args.script}: {exc}")
            return 1
    elif not sys.stdin.isatty() and args.query is None:
        try:
            batch_source = sys.stdin.read()
        except OSError:
            # Test harnesses often install a non-readable stdin sentinel; a
            # real redirected stream remains a batch input source.
            batch_source = None
    if args.continue_on_error and batch_source is None:
        parser.error(
            "--continue-on-error requires --execute, --script, or nonterminal stdin"
        )
    if batch_source is not None and args.query is not None:
        parser.error("batch input cannot be combined with --query")

    try:
        network_config = load_network_config(args.config_path)
    except ConfigurationError as exc:
        print(f"error: {exc}")
        return 1
    if args.print_config:
        print(args.server or network_config.target)
        return 0
    if args.server_version:
        try:
            async with AsyncClient(
                args.server, args.config_path, network_config
            ) as client:
                print((await client.server_version()).format("ctk-server"))
        except QueryError as exc:
            print(f"error: {exc}")
            return 1
        return 0
    if args.background and not args.query:
        parser.error("--background requires --query")

    compilation_options = (
        {"compilation_database": args.compile_commands}
        if args.compile_commands is not None
        else {}
    )
    client = (
        Client(args.server, **compilation_options)
        if args.config_path is None
        else Client(args.server, args.config_path, **compilation_options)
    )
    if batch_source is not None:
        runtime = None
        try:
            runtime = Runtime(client)
            if args.compile_commands is not None:
                runtime.config_store.effective["compile_commands"] = (
                    args.compile_commands
                )
            if runtime.config_store.effective["compile_commands"] is not None:
                compilation_options["compilation_database"] = (
                    runtime.config_store.effective["compile_commands"]
                )
            requirements = batch_requirements(batch_source)

            def runner():
                with script_source(runtime, batch_source_path):
                    return execute_batch(
                        batch_source,
                        lambda command: dispatch_result(client, command, runtime),
                        continue_on_error=args.continue_on_error,
                    )

            if not requirements.query_session and not requirements.background_query:
                runtime.clear_batch_cancel()
                result, interrupted = await _run_batch_with_interrupts(
                    runtime, runner
                )
                if interrupted:
                    return 130
                for output in result.outputs:
                    print(output)
                return result.exit_code

            session_errors: list[str] = []
            async with AsyncClient(
                args.server, args.config_path, network_config, **compilation_options
            ) as async_client:
                client.bind_async_client(async_client)
                query_session = None
                session_reader = None
                completion_tracker = None
                if requirements.query_session:
                    query_session = await async_client.query_session()
                    client.bind_query_session(query_session)
                    completion_tracker = _SessionCompletionTracker(
                        asyncio.get_running_loop()
                    )

                    async def print_batch_session_events() -> None:
                        try:
                            async for event in query_session.events():
                                completion_tracker.observe(event)
                                print(_format_event(event))
                        except QueryError as exc:
                            completion_tracker.fail(exc)
                            if not query_session.closing:
                                session_errors.append(str(exc))
                                print(f"error: {exc}")
                        except Exception as exc:
                            completion_tracker.fail(exc)
                            if not query_session.closing:
                                session_errors.append(str(exc))
                                print(f"error: {exc}")
                        else:
                            completion_tracker.finish()

                    session_reader = asyncio.create_task(print_batch_session_events())

                def dispatch_batch_command(command: str) -> DispatchResult:
                    if runtime._batch_cancel_requested.is_set():
                        raise BatchInterrupted("batch cancellation requested")
                    client._last_session_command = None
                    client._last_session_command_request_id = None
                    outcome = dispatch_result(client, command, runtime)
                    request_id = client._last_session_command_request_id
                    session_command = client._last_session_command
                    if (
                        request_id is None
                        or session_command is None
                        or completion_tracker is None
                    ):
                        return outcome
                    try:
                        event = completion_tracker.wait_from_thread(
                            request_id, session_command
                        )
                    except Exception as exc:
                        if runtime._batch_cancel_requested.is_set():
                            raise BatchInterrupted(
                                "batch interrupted while awaiting session completion"
                            ) from exc
                        return DispatchResult(f"error: {exc}", False)
                    if runtime._batch_cancel_requested.is_set():
                        raise BatchInterrupted("batch cancellation requested")
                    if event.WhichOneof("event") == "rejected":
                        return DispatchResult(f"error: {event.rejected.message}", False)
                    return outcome

                def run_batch():
                    with script_source(runtime, batch_source_path):
                        return execute_batch(
                            batch_source,
                            dispatch_batch_command,
                            continue_on_error=args.continue_on_error,
                        )

                runtime.clear_batch_cancel()

                async def cancel_batch_services() -> None:
                    if completion_tracker is not None:
                        completion_tracker.fail(QueryError("batch interrupted"))
                    if query_session is not None:
                        await query_session.cancel()
                    background = tuple(getattr(async_client, "_background", ()))
                    for task in background:
                        if not task.done():
                            task.cancel()
                    if background:
                        await asyncio.gather(*background, return_exceptions=True)

                try:
                    result, interrupted = await _run_batch_with_interrupts(
                        runtime,
                        run_batch,
                        async_client=async_client,
                        on_interrupt=cancel_batch_services,
                    )
                    if interrupted:
                        return 130
                    assert result is not None
                finally:
                    if query_session is not None:
                        cancel_stream = False
                        try:
                            async with asyncio.timeout(_SESSION_CLOSE_TIMEOUT):
                                await query_session.aclose()
                                if session_reader is not None:
                                    await session_reader
                        except TimeoutError:
                            cancel_stream = True
                        except QueryError as exc:
                            session_errors.append(str(exc))
                            print(f"error: {exc}")
                        finally:
                            if cancel_stream or (
                                session_reader is not None and not session_reader.done()
                            ):
                                await query_session.cancel()
                            if session_reader is not None and not session_reader.done():
                                session_reader.cancel()
                            if session_reader is not None:
                                await asyncio.gather(
                                    session_reader, return_exceptions=True
                                )
                if requirements.background_query:
                    try:
                        await async_client.wait_background()
                    except QueryError as exc:
                        session_errors.append(str(exc))
            for output in result.outputs:
                print(output)
            return 1 if result.exit_code or session_errors else 0
        finally:
            if runtime is not None:
                await asyncio.to_thread(runtime.close)
            await asyncio.to_thread(client.close)
    history_store: HistoryStore | None = HistoryStore()
    prompt_history = _load_prompt_history(history_store)
    if prompt_history is None:
        history_store = None
    runtime = None
    try:
        runtime = Runtime(client, history=history_store)
        session = create_session(
            references=runtime.completion_references,
            field_resolver=runtime.completion_suggestions,
            presence_resolver=runtime.completion_presence_fields,
            matcher_functions=runtime.matcher_function_names,
            history=prompt_history,
            cwd=runtime.cwd,
        )
    except (ConfigError, OutputError) as exc:
        print(f"error: {exc}")
        if runtime is not None:
            runtime.close()
        client.close()
        return 1
    if args.compile_commands is not None:
        runtime.config_store.effective["compile_commands"] = args.compile_commands
    if runtime.config_store.effective["compile_commands"] is not None:
        compilation_options["compilation_database"] = runtime.config_store.effective[
            "compile_commands"
        ]
    query_session = None
    session_reader = None
    exit_code = 0
    try:
        async with AsyncClient(
            args.server, args.config_path, network_config, **compilation_options
        ) as async_client:
            client.bind_async_client(async_client)
            try:
                if args.query and not args.background:
                    try:
                        await async_client.query(
                            args.query,
                            args.file,
                            on_event=lambda event: print(_format_event(event)),
                        )
                    except QueryError as exc:
                        print(f"error: {exc}")
                        return 1
                    return 0
                query_session = await async_client.query_session()
                client.bind_query_session(query_session)

                async def print_session_events():
                    try:
                        async for event in query_session.events():
                            print(_format_event(event))
                    except QueryError as exc:
                        if not query_session.closing:
                            print(f"error: {exc}")
                    except Exception as exc:
                        if not query_session.closing:
                            print(f"error: {exc}")

                session_reader = asyncio.create_task(print_session_events())
                if args.query:
                    async_client.start_background_query(
                        args.query,
                        args.file,
                        on_event=lambda event: print(_format_event(event)),
                        on_error=lambda error: print(f"error: {error}"),
                    )
                    print("background query started; enter REPL commands while it runs")
                while True:
                    try:
                        line = await _prompt(session, "ctk> ")
                    except EOFError:
                        break
                    except KeyboardInterrupt:
                        continue
                    try:
                        outcome = await asyncio.to_thread(
                            dispatch_result, client, line, runtime
                        )
                    except (NotImplementedError, CursorError, AnalysisError) as exc:
                        outcome = DispatchResult(f"error: {exc}", False)
                    except (QueryError, ConfigurationError) as exc:
                        outcome = DispatchResult(f"error: {exc}", False)
                    if not outcome.success:
                        exit_code = 1
                    out = outcome.output
                    if out is None:
                        break
                    if out:
                        print(out)
                try:
                    await async_client.wait_background()
                except QueryError:
                    exit_code = 1
            finally:
                if query_session is not None:
                    cancel_stream = False
                    try:
                        async with asyncio.timeout(_SESSION_CLOSE_TIMEOUT):
                            await query_session.aclose()
                            if session_reader is not None:
                                await session_reader
                    except TimeoutError:
                        cancel_stream = True
                    except QueryError as exc:
                        print(f"error: {exc}")
                        exit_code = 1
                    finally:
                        if cancel_stream or (
                            session_reader is not None and not session_reader.done()
                        ):
                            await query_session.cancel()
                        if session_reader is not None and not session_reader.done():
                            session_reader.cancel()
                        if session_reader is not None:
                            await asyncio.gather(session_reader, return_exceptions=True)
    finally:
        await asyncio.to_thread(runtime.close)
        await asyncio.to_thread(client.close)
    return exit_code


def main() -> None:
    result = asyncio.run(_run())
    if result:
        raise SystemExit(result)


if __name__ == "__main__":
    main()
