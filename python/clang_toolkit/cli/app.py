"""Interactive console (prompt_toolkit) for the clang-toolkit server."""

from __future__ import annotations

import argparse
import asyncio
import inspect

from lark.exceptions import UnexpectedInput

from clang_toolkit.cli.language import lex, parser as command_parser
from clang_toolkit.cli.help import COMMANDS, render_help
from clang_toolkit.cli.syntax_diagnostics import (
    syntax_diagnostic,
    unknown_command_diagnostic,
)
from clang_toolkit.cli.prompt import PersistentPromptHistory, create_session
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
from clang_toolkit.version import client_version

_SESSION_CLOSE_TIMEOUT = 5.0


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
        if runtime is not None and runtime.history is not None:
            try:
                runtime.history.append(line, runtime.session_id, runtime.label)
            except HistoryError as history_error:
                return f"error: {history_error}"
        first = next(token for token in lex(line) if token.type != "WS")
        if first.type == "NAME" and str(first) not in COMMANDS:
            return unknown_command_diagnostic(line, str(first), COMMANDS)
        return syntax_diagnostic(line, exc)
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


def _load_prompt_history(store: HistoryStore) -> PersistentPromptHistory | None:
    try:
        return PersistentPromptHistory(store)
    except HistoryError as exc:
        print(f"error: {exc}; persistent history disabled for this session")
        return None


async def _prompt(session, prompt: str) -> str:
    prompt_async = getattr(session, "prompt_async", None)
    if prompt_async is not None and inspect.iscoroutinefunction(prompt_async):
        return await prompt_async(prompt)
    return await asyncio.to_thread(session.prompt, prompt)


async def _run() -> int:
    parser = argparse.ArgumentParser(prog="ctk")
    parser.add_argument("--version", action="version", version=client_version().format("ctk"))
    parser.add_argument("--server-version", action="store_true", help="print the connected server version and exit")
    parser.add_argument("--compile-commands", help="server-side compile_commands.json file or directory")
    parser.add_argument("--server", help="override the configured gRPC endpoint")
    parser.add_argument("-c", "--cofing", "--config-path", dest="config_path")
    parser.add_argument("--print-config", action="store_true")
    parser.add_argument("--query", help="run one query expression")
    parser.add_argument("--file", action="append", default=[], help="query input file (repeatable)")
    parser.add_argument("--background", action="store_true", help="run --query while the prompt remains active")
    parser.add_argument("--session", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()

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
            async with AsyncClient(args.server, args.config_path, network_config) as client:
                print((await client.server_version()).format("ctk-server"))
        except QueryError as exc:
            print(f"error: {exc}")
            return 1
        return 0
    if args.background and not args.query:
        parser.error("--background requires --query")

    compilation_options = ({"compilation_database": args.compile_commands}
                           if args.compile_commands is not None else {})
    client = (
        Client(args.server, **compilation_options)
        if args.config_path is None
        else Client(args.server, args.config_path, **compilation_options)
    )
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
        compilation_options["compilation_database"] = runtime.config_store.effective["compile_commands"]
    query_session = None
    session_reader = None
    exit_code = 0
    try:
        async with AsyncClient(args.server, args.config_path, network_config, **compilation_options) as async_client:
            client.bind_async_client(async_client)
            try:
                if args.query and not args.background:
                    try:
                        await async_client.query(
                            args.query, args.file, on_event=lambda event: print(_format_event(event))
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
                        if cancel_stream or (session_reader is not None and not session_reader.done()):
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
