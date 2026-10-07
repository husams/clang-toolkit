"""Interactive console (prompt_toolkit) for the clang-toolkit server."""

from __future__ import annotations

import argparse
import asyncio
import inspect

from lark.exceptions import UnexpectedInput

from clang_toolkit.cli.language import lex, parser as command_parser
from clang_toolkit.cli.help import COMMANDS, render_help
from clang_toolkit.cli.prompt import create_session
from clang_toolkit.cli.runtime import EvaluationError, Runtime
from clang_toolkit.cli.runtime.config import ConfigError
from clang_toolkit.cli.runtime.history import HistoryError, HistoryStore
from clang_toolkit.cli.runtime.output import OutputError
from clang_toolkit.cli.runtime.persistence import PersistenceError
from clang_toolkit.client import AsyncClient, Client, QueryError, _format_event
from clang_toolkit.cursors import CursorError
from clang_toolkit.match_values import MatchValueError
from clang_toolkit.analysis_error import AnalysisError
from clang_toolkit.configuration import ConfigurationError, load_network_config


def dispatch(client: Client, line: str, runtime: Runtime | None = None) -> str | None:
    """Validate one sentence and evaluate it in the active REPL runtime."""
    if not line.strip():
        line = "help"
    try:
        statement = command_parser().parse(line).children[0]
        if statement.data in {"help", "help_shortcut"}:
            if runtime is not None and runtime.history is not None:
                runtime.history.append(line, runtime.session_id, runtime.label)
            return render_help(statement)
        runtime = runtime or Runtime(client)
        return runtime.execute(line)
    except UnexpectedInput as exc:
        first = next(token for token in lex(line) if token.type != "WS")
        if first.type == "NAME" and str(first) not in COMMANDS:
            return f"unknown command: {first}"
        return f"syntax error at line {exc.line}, column {exc.column}"
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
    ) as exc:
        return f"error: {exc}"


async def _prompt(session, prompt: str) -> str:
    prompt_async = getattr(session, "prompt_async", None)
    if prompt_async is not None and inspect.iscoroutinefunction(prompt_async):
        return await prompt_async(prompt)
    return await asyncio.to_thread(session.prompt, prompt)


async def _run() -> int:
    parser = argparse.ArgumentParser(prog="ctk")
    parser.add_argument("--server", help="override the configured gRPC endpoint")
    parser.add_argument("-c", "--cofing", "--config-path", dest="config_path")
    parser.add_argument("--print-config", action="store_true")
    parser.add_argument("--query", help="run one query expression")
    parser.add_argument("--file", action="append", default=[], help="query input file (repeatable)")
    parser.add_argument("--background", action="store_true", help="run --query while the prompt remains active")
    parser.add_argument("--session", action="store_true", help="enable bidirectional session REPL commands")
    args = parser.parse_args()

    try:
        network_config = load_network_config(args.config_path)
    except ConfigurationError as exc:
        print(f"error: {exc}")
        return 1
    if args.print_config:
        print(args.server or network_config.target)
        return 0
    if args.background and not args.query:
        parser.error("--background requires --query")

    client = (
        Client(args.server)
        if args.config_path is None
        else Client(args.server, args.config_path)
    )
    try:
        runtime = Runtime(client, history=HistoryStore())
    except (ConfigError, OutputError) as exc:
        print(f"error: {exc}")
        return 1
    session = create_session(references=runtime.completion_references, cwd=runtime.cwd)
    query_session = None
    session_reader = None
    exit_code = 0
    try:
        async with AsyncClient(args.server, args.config_path, network_config) as async_client:
            client.bind_async_client(async_client)
            if args.session:
                query_session = await async_client.query_session()
                client.bind_query_session(query_session)
                async def print_session_events():
                    try:
                        async for event in query_session.events():
                            print(_format_event(event))
                    except QueryError as exc:
                        print(f"error: {exc}")
                session_reader = asyncio.create_task(print_session_events())
            if args.query and not args.background:
                try:
                    await async_client.query(
                        args.query, args.file, on_event=lambda event: print(_format_event(event))
                    )
                except QueryError as exc:
                    print(f"error: {exc}")
                    return 1
                return 0
            if args.query:
                async_client.start_background_query(
                    args.query, args.file, on_event=lambda event: print(_format_event(event)),
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
                    out = await asyncio.to_thread(dispatch, client, line, runtime)
                except (NotImplementedError, CursorError, AnalysisError) as exc:
                    out = f"error: {exc}"
                except (QueryError, ConfigurationError) as exc:
                    out = f"error: {exc}"
                if out is None:
                    break
                if out:
                    print(out)
            try:
                await async_client.wait_background()
            except QueryError:
                exit_code = 1
            if query_session is not None:
                await query_session.aclose()
                if session_reader is not None:
                    try:
                        await asyncio.wait_for(session_reader, timeout=5)
                    except TimeoutError:
                        await query_session.cancel()
                        session_reader.cancel()
                    except QueryError as exc:
                        print(f"error: {exc}")
                        exit_code = 1
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
