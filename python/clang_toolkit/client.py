"""Async and synchronous gRPC clients for clang-toolkit query services."""

from __future__ import annotations

import asyncio
import concurrent.futures
from contextlib import aclosing
import inspect
import json
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import grpc
from google.protobuf.message import DecodeError

from clang_toolkit._generated.query.v1 import query_pb2, query_pb2_grpc
from clang_toolkit.configuration import NetworkConfig, load_network_config

QueryEvent = query_pb2.QueryEvent
EventCallback = Callable[[QueryEvent], Any | Awaitable[Any]]


class QueryError(RuntimeError):
    """Query failed after zero or more partial events had been received."""

    def __init__(
        self,
        message: str,
        *,
        partial_events: Sequence[QueryEvent] = (),
        rejected: query_pb2.Rejected | None = None,
    ) -> None:
        self.partial_events = tuple(partial_events)
        self.rejected = rejected
        self.violations = tuple(rejected.violations) if rejected is not None else ()
        if self.violations:
            message = f"{message}; " + "; ".join(
                _format_violation(item) for item in self.violations
            )
        super().__init__(message)


def _rejection_from_status(error: grpc.aio.AioRpcError) -> query_pb2.Rejected | None:
    for key, value in error.trailing_metadata() or ():
        if key == "grpc-status-details-bin":
            rejected = query_pb2.Rejected()
            try:
                rejected.ParseFromString(value)
            except DecodeError:
                return None
            return rejected
    return None


def _format_violation(violation: query_pb2.LimitViolation) -> str:
    text = (
        f"{violation.limit_name}: current {violation.current_value}, "
        f"requested +{violation.requested_increment}, projected {violation.projected_value}, "
        f"limit {violation.configured_limit}"
    )
    if "memory" in violation.limit_name:
        text += (
            f"; current {violation.current_value / (1024 ** 3):.2f} GiB"
            f"; requested {violation.requested_increment / (1024 ** 3):.2f} GiB"
            f"; projected {violation.projected_value / (1024 ** 3):.2f} GiB"
            f"; limit {violation.configured_limit / (1024 ** 3):.2f} GiB"
        )
    return text


def _file_inputs(
    files: Sequence[str | Path], *, working_directory: str | Path | None = None,
    compile_arguments: Sequence[str] = (),
) -> list[query_pb2.FileInput]:
    working = str(Path(working_directory or Path.cwd()).resolve())
    base = Path(working)
    return [
        query_pb2.FileInput(
            path=str((Path(path).expanduser() if Path(path).expanduser().is_absolute() else base / Path(path).expanduser()).resolve()),
            compile_arguments=compile_arguments,
            working_directory=working,
        )
        for path in files
    ]


@dataclass
class AsyncClient:
    """Loop-owned ``grpc.aio`` client with collecting and streaming APIs."""

    address: str | None = None
    config_path: str | Path | None = None
    config: NetworkConfig | None = None
    _channel: grpc.aio.Channel | None = field(default=None, init=False, repr=False)
    _stub: query_pb2_grpc.QueryServiceStub | None = field(default=None, init=False, repr=False)
    _loop: asyncio.AbstractEventLoop | None = field(default=None, init=False, repr=False)
    _background: set[asyncio.Task[list[QueryEvent]]] = field(
        default_factory=set, init=False, repr=False
    )

    def _ensure_stub(self) -> query_pb2_grpc.QueryServiceStub:
        loop = asyncio.get_running_loop()
        if self._loop is not None and self._loop is not loop:
            raise RuntimeError("AsyncClient must be used from the event loop that created it")
        if self._stub is None:
            self.config = self.config or load_network_config(self.config_path)
            self._loop = loop
            target = self.address or self.config.target
            self._channel = grpc.aio.insecure_channel(target, options=self.config.client_options)
            self._stub = query_pb2_grpc.QueryServiceStub(self._channel)
        return self._stub

    async def iter_events(
        self,
        query: str,
        files: Sequence[str | Path] = (),
        *,
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (),
    ) -> AsyncIterator[QueryEvent]:
        """Yield events, requiring both a Completed event and terminal OK."""
        stub = self._ensure_stub()
        assert self.config is not None
        request = query_pb2.QueryRequest(
            query=query,
            files=_file_inputs(
                files, working_directory=working_directory,
                compile_arguments=compile_arguments,
            ),
        )
        call = stub.Query(request, timeout=self.config.rpc_timeout)
        received: list[QueryEvent] = []
        completed = False
        consumed = False
        rejected_event: query_pb2.Rejected | None = None
        try:
            async for event in call:
                received.append(event)
                if event.WhichOneof("event") == "completed":
                    completed = True
                if event.WhichOneof("event") == "rejected":
                    rejected_event = event.rejected
                yield event
            if not completed:
                raise QueryError("query stream ended without Completed", partial_events=received)
            if rejected_event is not None:
                raise QueryError(
                    f"query rejected ({rejected_event.code}): {rejected_event.message}",
                    partial_events=received,
                    rejected=rejected_event,
                )
            consumed = True
        except grpc.aio.AioRpcError as exc:
            raise QueryError(
                f"query RPC failed: {exc.code().name}: {exc.details()}",
                partial_events=received,
                rejected=_rejection_from_status(exc) or rejected_event,
            ) from exc
        except asyncio.CancelledError as exc:
            if asyncio.current_task() and asyncio.current_task().cancelling():
                raise
            raise QueryError("query RPC cancelled: CANCELLED", partial_events=received) from exc
        finally:
            if not consumed and not call.done():
                call.cancel()

    async def query(
        self,
        expression: str,
        files: Sequence[str | Path] = (),
        *,
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (),
        on_event: EventCallback | None = None,
    ) -> list[QueryEvent]:
        """Collect an entire successful query stream or raise with partials."""
        events: list[QueryEvent] = []
        stream = self.iter_events(
            expression, files, working_directory=working_directory,
            compile_arguments=compile_arguments,
        )
        async with aclosing(stream):
            async for event in stream:
                events.append(event)
                if on_event is not None:
                    outcome = on_event(event)
                    if inspect.isawaitable(outcome):
                        await outcome
        return events

    async def match(
        self,
        expression: str,
        files: Sequence[str | Path] = (),
        *,
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (),
    ) -> list[query_pb2.MatchEvent]:
        """Collect typed match rows after successful terminal completion."""
        events = await self.query(
            expression, files, working_directory=working_directory,
            compile_arguments=compile_arguments,
        )
        return [event.match for event in events if event.WhichOneof("event") == "match"]

    def start_background_query(
        self,
        expression: str,
        files: Sequence[str | Path] = (),
        *,
        on_event: EventCallback | None = None,
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (),
        on_error: Callable[[QueryError], Any] | None = None,
    ) -> "BackgroundQuery":
        """Start consuming immediately and return a retained task handle."""
        async def consume() -> list[QueryEvent]:
            try:
                return await self.query(
                    expression, files, on_event=on_event,
                    working_directory=working_directory,
                    compile_arguments=compile_arguments,
                )
            except QueryError as exc:
                if on_error is not None:
                    result = on_error(exc)
                    if inspect.isawaitable(result):
                        await result
                raise

        task = asyncio.create_task(consume(), name=f"ctk-query-{uuid.uuid4().hex[:8]}")
        self._background.add(task)
        task.add_done_callback(lambda done: done.exception() if not done.cancelled() else None)
        return BackgroundQuery(task)

    async def query_session(self) -> "QuerySession":
        """Open a serialized bidirectional interactive query session."""
        return await QuerySession.open(self)

    async def wait_background(self) -> list[list[QueryEvent]]:
        """Wait for every retained background stream to reach terminal status."""
        tasks = tuple(self._background)
        if not tasks:
            return []
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)
        failures = [item for item in outcomes if isinstance(item, BaseException)]
        self._background.difference_update(tasks)
        if failures:
            raise failures[0]
        return [item for item in outcomes if isinstance(item, list)]

    async def aclose(self) -> None:
        for task in tuple(self._background):
            if not task.done():
                task.cancel()
        if self._background:
            await asyncio.gather(*self._background, return_exceptions=True)
            self._background.clear()
        if self._channel is not None:
            await self._channel.close()
            self._channel = None
            self._stub = None
            self._loop = None

    async def __aenter__(self) -> "AsyncClient":
        self._ensure_stub()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()


@dataclass
class BackgroundQuery:
    """A running background query whose task keeps the RPC stream consumed."""

    task: asyncio.Task[list[QueryEvent]]

    @property
    def done(self) -> bool:
        return self.task.done()

    async def result(self) -> list[QueryEvent]:
        return await self.task

    def cancel(self) -> bool:
        return self.task.cancel()


class QuerySession:
    """Bidirectional session with serialized command writes and live receives."""

    def __init__(self, client: AsyncClient) -> None:
        self.client = client
        self._commands: asyncio.Queue[query_pb2.QueryCommand | None] = asyncio.Queue()
        self._call: Any = None
        self._events: list[QueryEvent] = []
        self._reading = False
        self._input_closed = False
        self._matching_started = False

    @classmethod
    async def open(cls, client: AsyncClient) -> "QuerySession":
        instance = cls(client)
        stub = client._ensure_stub()
        assert client.config is not None
        async def commands() -> AsyncIterator[query_pb2.QueryCommand]:
            while True:
                command = await instance._commands.get()
                if command is None:
                    return
                yield command
        instance._call = stub.QuerySession(commands(), timeout=client.config.rpc_timeout)
        return instance

    def _send(self, command_name: str, value: Any = None) -> str:
        if self._input_closed:
            raise RuntimeError("query session input is already closed")
        command = query_pb2.QueryCommand(request_id=uuid.uuid4().hex)
        if value is None:
            getattr(command, command_name).SetInParent()
        else:
            getattr(command, command_name).CopyFrom(value)
        self._commands.put_nowait(command)
        return command.request_id

    async def start_query(self, query: str) -> str:
        return self._send("start_query", query_pb2.StartQuery(query=query))

    async def add_files(
        self, files: Sequence[str | Path], *, working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (),
    ) -> str:
        return self._send("add_files", query_pb2.AddFiles(files=_file_inputs(
            files, working_directory=working_directory, compile_arguments=compile_arguments
        )))

    async def match(self) -> str:
        self._matching_started = True
        return self._send("match")

    async def pause(self) -> str:
        return self._send("pause")

    async def resume(self) -> str:
        return self._send("resume")

    async def events(self) -> AsyncIterator[QueryEvent]:
        """Read response events until half-close or server completion."""
        consumed = False
        completed = False
        self._reading = True
        try:
            async for event in self._call:
                self._events.append(event)
                completed = completed or event.WhichOneof("event") == "completed"
                yield event
            if not completed:
                raise QueryError("query session ended without Completed", partial_events=self._events)
            consumed = True
        except grpc.aio.AioRpcError as exc:
            raise QueryError(
                f"query session failed: {exc.code().name}: {exc.details()}",
                partial_events=self._events,
                rejected=_rejection_from_status(exc),
            ) from exc
        except asyncio.CancelledError as exc:
            if asyncio.current_task() and asyncio.current_task().cancelling():
                raise
            raise QueryError("query session cancelled: CANCELLED", partial_events=self._events) from exc
        finally:
            self._reading = False
            if not consumed and not self._call.done():
                self._call.cancel()
                self._commands.put_nowait(None)

    async def half_close(self) -> None:
        if not self._input_closed:
            self._input_closed = True
            self._commands.put_nowait(None)

    async def cancel(self) -> None:
        self._call.cancel()
        if not self._input_closed:
            self._input_closed = True
            self._commands.put_nowait(None)

    async def aclose(self) -> None:
        if self._call is not None and not self._call.done():
            if not self._matching_started:
                await self.cancel()
            else:
                await self.half_close()
                if self._reading:
                    await self._call.code()
                else:
                    async for _ in self.events():
                        pass

    async def __aenter__(self) -> "QuerySession":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()


@dataclass
class Client:
    """Synchronous compatibility facade used by the existing REPL runtime."""

    address: str | None = None
    config_path: str | Path | None = None
    _async_client: AsyncClient | None = field(default=None, init=False, repr=False)
    _async_loop: asyncio.AbstractEventLoop | None = field(default=None, init=False, repr=False)
    _query_session: QuerySession | None = field(default=None, init=False, repr=False)
    _background_handles: dict[str, BackgroundQuery] = field(default_factory=dict, init=False, repr=False)

    def bind_async_client(self, client: AsyncClient) -> None:
        """Attach the active CLI loop for commands submitted by worker threads."""
        self._async_client = client
        self._async_loop = asyncio.get_running_loop()

    def bind_query_session(self, session: QuerySession) -> None:
        self._query_session = session

    def send_session_command(
        self, command: str, value: str | None = None, *,
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (),
    ) -> str:
        if self._query_session is None or self._async_loop is None:
            raise RuntimeError("bidirectional session requires --session")

        async def send() -> None:
            if command == "start":
                await self._query_session.start_query(value or "")
            elif command == "add":
                await self._query_session.add_files(
                    [value or ""], working_directory=working_directory,
                    compile_arguments=compile_arguments,
                )
            elif command == "match":
                await self._query_session.match()
            elif command == "pause":
                await self._query_session.pause()
            elif command == "resume":
                await self._query_session.resume()
            elif command == "close":
                await self._query_session.half_close()

        self._async_loop.call_soon_threadsafe(asyncio.create_task, send())
        return f"session {command} command sent"

    def start_background_query(
        self,
        expression: str,
        files: Sequence[str | Path] = (),
        *,
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (),
    ) -> str:
        """Schedule an interactive query while the CLI continues prompting."""
        if self._async_client is None or self._async_loop is None:
            raise RuntimeError("background query requires the interactive async client")
        query_id = uuid.uuid4().hex[:8]
        ready: concurrent.futures.Future[BackgroundQuery] = concurrent.futures.Future()

        def start() -> None:
            try:
                handle = self._async_client.start_background_query(
                    expression, files, on_event=lambda event: print(_format_event(event)),
                    working_directory=working_directory,
                    compile_arguments=compile_arguments,
                    on_error=lambda error: print(f"error: {error}"),
                )
                self._background_handles[query_id] = handle
                ready.set_result(handle)
            except BaseException as exc:
                ready.set_exception(exc)

        self._async_loop.call_soon_threadsafe(start)
        ready.result(timeout=2)
        return f"background query {query_id} started"

    def match(
        self, matcher: str, *, files: list[str] | None = None,
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (),
    ) -> list[str]:
        """Run a query synchronously; bindings are returned as JSON rows."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            raise RuntimeError("Client.match cannot run inside an active event loop")

        async def run() -> list[str]:
            async with AsyncClient(self.address, self.config_path) as client:
                events = await client.query(
                    matcher, files or (), working_directory=working_directory,
                    compile_arguments=compile_arguments,
                )
            rows: list[str] = []
            for event in events:
                if event.WhichOneof("event") != "match":
                    continue
                values = {
                    name: {
                        "kind": binding.kind,
                        "name": binding.name,
                        "type": binding.type,
                    }
                    for name, binding in event.match.bindings.items()
                }
                rows.append(json.dumps(values, sort_keys=True))
            return rows

        return asyncio.run(run())

    def cfg(self, function: str) -> str:
        raise NotImplementedError("CFG queries are not yet exposed by the server")

    def callgraph(self) -> str:
        raise NotImplementedError("call graph queries are not yet exposed by the server")


def _format_event(event: QueryEvent) -> str:
    kind = event.WhichOneof("event")
    if kind == "progress":
        return f"[{event.request_id}] {event.progress.file}: {event.progress.completed_files}/{event.progress.accepted_files} files"
    if kind == "match":
        values = {
            key: {"kind": value.kind, "name": value.name, "type": value.type}
            for key, value in event.match.bindings.items()
        }
        return f"[{event.request_id}] {json.dumps(values, sort_keys=True)}"
    if kind == "completed":
        return f"[{event.request_id}] completed: {event.completed.match_count} matches"
    if kind == "rejected":
        message = f"[{event.request_id}] rejected: {event.rejected.message}"
        if event.rejected.violations:
            message += "; " + "; ".join(
                _format_violation(item) for item in event.rejected.violations
            )
        return message
    return f"[{event.request_id}] {kind}"
