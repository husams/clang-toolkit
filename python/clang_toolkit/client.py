"""Async and synchronous gRPC clients for clang-toolkit query services."""

from __future__ import annotations
from clang_toolkit._generated.analysis.v1 import script_response_pb2
from clang_toolkit.scripting import script_request

import asyncio
import concurrent.futures
from contextlib import aclosing
import inspect
import json
import uuid
import weakref
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast, overload

import grpc
from google.protobuf.message import DecodeError

from clang_toolkit._generated.query.v1 import query_pb2, query_pb2_grpc
from clang_toolkit.configuration import NetworkConfig, load_network_config
from clang_toolkit.cursors import CursorError, file_request, retained_request
from clang_toolkit._generated.match.v1 import match_service_pb2, match_service_pb2_grpc
from clang_toolkit._generated.match.v1 import match_result_pb2
from clang_toolkit._generated.analysis.v1 import analysis_service_pb2_grpc, traverse_response_pb2, cfg_response_pb2, call_graph_response_pb2
from clang_toolkit.analysis_error import AnalysisError
from clang_toolkit.traversal import traversal_request
from clang_toolkit.control_flow import CfgOptions, cfg_request
from clang_toolkit.call_graph import call_graph_request
from clang_toolkit.match_values import (
    BindingSelection, MatchTarget, MatchValue, MatchValueError, ParsedTree,
)
from clang_toolkit._value_lifecycle import CursorOwner, OperationLease
from clang_toolkit._generated.match.v1 import parse_request_pb2, parse_response_pb2

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
    compilation_database: str | Path | None = None
    _channel: grpc.aio.Channel | None = field(default=None, init=False, repr=False)
    _stub: query_pb2_grpc.QueryServiceStub | None = field(default=None, init=False, repr=False)
    _loop: asyncio.AbstractEventLoop | None = field(default=None, init=False, repr=False)
    _background: set[asyncio.Task[list[QueryEvent]]] = field(
        default_factory=set, init=False, repr=False
    )
    _values: dict[str, weakref.ReferenceType[CursorOwner[AsyncClient]]] = field(
        default_factory=dict, init=False, repr=False)
    _value_cleanup: set[asyncio.Task[None]] = field(
        default_factory=set, init=False, repr=False)
    _value_cleanup_by_id: dict[str, asyncio.Task[None]] = field(
        default_factory=dict, init=False, repr=False)
    _pending_value_cleanup: set[str] = field(default_factory=set, init=False, repr=False)
    _expression_runtime: Any = field(default=None, init=False, repr=False)
    _expression_lock: asyncio.Lock | None = field(default=None, init=False, repr=False)
    _value_closing: bool = field(default=False, init=False, repr=False)
    _value_closed: bool = field(default=False, init=False, repr=False)
    _value_operation_count: int = field(default=0, init=False, repr=False)
    _value_idle: asyncio.Event | None = field(default=None, init=False, repr=False)
    _value_close_lock: asyncio.Lock | None = field(default=None, init=False, repr=False)

    def _compilation_request(self, request: Any) -> Any:
        """Select a server-side database for every file/profile RPC."""
        selected = str(self.compilation_database or "")
        if not selected:
            return request
        if hasattr(request, "compilation_database") and not request.compilation_database:
            request.compilation_database = selected
        if hasattr(request, "file") and request.HasField("file"):
            if not request.file.compilation_database:
                request.file.compilation_database = selected
        if hasattr(request, "profile") and request.HasField("profile"):
            if not request.profile.compilation_database:
                request.profile.compilation_database = selected
        for file in getattr(request, "files", ()):
            if not file.compilation_database:
                file.compilation_database = selected
        return request

    def _ensure_stub(self) -> query_pb2_grpc.QueryServiceStub:
        loop = asyncio.get_running_loop()
        if self._loop is not None and self._loop is not loop:
            raise RuntimeError("AsyncClient must be used from the event loop that created it")
        if self._stub is None:
            self.config = (load_network_config(self.config_path)
                           if self.config_path is not None else
                           self.config or load_network_config())
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
        call = stub.Query(self._compilation_request(request), timeout=self.config.rpc_timeout)
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

    @overload
    async def match(
        self, expression: str, files: Sequence[str | Path] = (), *,
        file: str | Path, working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (),
    ) -> MatchValue[AsyncClient]: ...

    @overload
    async def match(
        self, expression: str, files: Sequence[str | Path] = (), *,
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (), file: None = None,
    ) -> list[query_pb2.MatchEvent]: ...

    async def match(
        self,
        expression: str,
        files: Sequence[str | Path] = (),
        *,
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (),
        file: str | Path | None = None,
    ) -> list[query_pb2.MatchEvent] | MatchValue[AsyncClient]:
        """Collect typed match rows after successful terminal completion."""
        if file is not None:
            if files:
                raise ValueError("use either file or files, not both")
            return await self.match_in(expression, file,
                working_directory=working_directory, compile_arguments=compile_arguments)
        events = await self.query(
            expression, files, working_directory=working_directory,
            compile_arguments=compile_arguments,
        )
        return [event.match for event in events if event.WhichOneof("event") == "match"]

    async def _cursor_match(self, request: match_service_pb2.MatchRequest) -> match_service_pb2.MatchResponse:
        self._ensure_stub()
        assert self._channel is not None and self.config is not None
        stub = match_service_pb2_grpc.MatchServiceStub(self._channel)
        try:
            return await stub.Match(self._compilation_request(request), timeout=self.config.rpc_timeout)
        except grpc.aio.AioRpcError as error:
            raise CursorError(error.code(), error.details()) from error

    async def _parse_response(
        self, path: str | Path, *, working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (), compilation_database: str | Path | None = None,
    ) -> parse_response_pb2.ParseResponse:
        self._ensure_stub()
        assert self._channel is not None and self.config is not None
        request = parse_request_pb2.ParseRequest(
            file_path=str(path), compile_arguments=compile_arguments,
            compilation_database=str(compilation_database or ""),
            working_directory=str(Path(working_directory or Path.cwd()).resolve()),
        )
        try:
            return await match_service_pb2_grpc.MatchServiceStub(self._channel).Parse(
                self._compilation_request(request), timeout=self.config.rpc_timeout)
        except grpc.aio.AioRpcError as error:
            raise CursorError(error.code(), error.details()) from error

    def _own_value(self, response: Any) -> CursorOwner[AsyncClient]:
        owner = CursorOwner(cast(AsyncClient, self), response.session_id, response.result_revision,
                             self._release_value, loop=asyncio.get_running_loop())
        self._values[response.session_id] = weakref.ref(owner)
        return owner

    def _release_value(self, session_id: str) -> None:
        loop = self._loop
        def release_on_loop() -> None:
            self._pending_value_cleanup.add(session_id)
            self._values.pop(session_id, None)
            self._schedule_value_cleanup(session_id)

        if loop is None:
            self._pending_value_cleanup.add(session_id)
            self._values.pop(session_id, None)
            return
        if loop.is_closed():
            self._pending_value_cleanup.add(session_id)
            self._values.pop(session_id, None)
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is loop:
            release_on_loop()
        else:
            loop.call_soon_threadsafe(release_on_loop)

    def _cleanup_task_done(self, identifier: str, task: asyncio.Task[None]) -> None:
        if self._value_cleanup_by_id.get(identifier) is task:
            self._value_cleanup_by_id.pop(identifier, None)
        self._value_cleanup.discard(task)
        if not task.cancelled():
            # Finalizer-triggered cleanup has no caller to observe a failure.
            # Retrieve it here and leave the identifier pending for retry.
            task.exception()

    def _schedule_value_cleanup(self, identifier: str) -> asyncio.Task[None]:
        task = self._value_cleanup_by_id.get(identifier)
        if task is None or task.done():
            task = asyncio.create_task(self._close_value_cleanup_once(identifier))
            self._value_cleanup_by_id[identifier] = task
            self._value_cleanup.add(task)
            task.add_done_callback(lambda done, key=identifier: self._cleanup_task_done(key, done))
        return task

    async def _close_value_cleanup(self, identifier: str) -> None:
        if identifier not in self._pending_value_cleanup:
            return
        task = self._schedule_value_cleanup(identifier)
        await asyncio.shield(task)

    async def _close_value_cleanup_once(self, identifier: str) -> None:
        await self.close_match(identifier)
        self._pending_value_cleanup.discard(identifier)

    async def _flush_value_cleanup(self) -> None:
        tasks = tuple(self._value_cleanup)
        if tasks:
            outcomes = await asyncio.gather(
                *(asyncio.shield(task) for task in tasks), return_exceptions=True
            )
            _raise_cleanup_errors([outcome for outcome in outcomes
                                   if isinstance(outcome, BaseException)])

    def _begin_value_operation(self, lease: OperationLease | None = None) -> None:
        accepted = lease is not None and lease.client is self and lease.active
        if (self._value_closing or self._value_closed) and not accepted:
            raise MatchValueError("client is closing or closed")
        self._ensure_stub()
        for identifier in tuple(self._pending_value_cleanup):
            if identifier not in self._value_cleanup_by_id:
                self._schedule_value_cleanup(identifier)
        if self._value_idle is None:
            self._value_idle = asyncio.Event()
        self._value_operation_count += 1
        self._value_idle.clear()

    def _end_value_operation(self) -> None:
        self._value_operation_count -= 1
        if self._value_operation_count == 0 and self._value_idle is not None:
            self._value_idle.set()

    async def parse(
        self, path: str | Path, *, working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (), compilation_database: str | Path | None = None,
    ) -> ParsedTree[AsyncClient]:
        """Parse a file once and retain a reusable immutable native tree."""
        return await self._parse_with_lease(path, working_directory=working_directory,
                                            compile_arguments=compile_arguments, compilation_database=compilation_database, lease=None)

    async def _parse_with_lease(
        self, path: str | Path, *, working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (), compilation_database: str | Path | None = None, lease: OperationLease | None,
    ) -> ParsedTree[AsyncClient]:
        self._begin_value_operation(lease)
        try:
            response = await self._parse_response(path, working_directory=working_directory,
                compile_arguments=compile_arguments, compilation_database=compilation_database)
            return ParsedTree(str(path), self._own_value(response))
        finally:
            self._end_value_operation()

    async def match_in(
        self, query: str, target: MatchTarget | Path, *,
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (),
        traversal_mode: match_service_pb2.MatchTraversalMode = match_service_pb2.MATCH_TRAVERSAL_MODE_AS_IS,
    ) -> MatchValue[AsyncClient]:
        """Match a path, pinned tree or binding selection without changing it."""
        return await self._match_in_with_lease(query, target,
            working_directory=working_directory, compile_arguments=compile_arguments,
            traversal_mode=traversal_mode, lease=None)

    async def _match_in_with_lease(
        self, query: str, target: MatchTarget, *,
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (),
        traversal_mode: match_service_pb2.MatchTraversalMode = match_service_pb2.MATCH_TRAVERSAL_MODE_AS_IS,
        lease: OperationLease | None,
    ) -> MatchValue[AsyncClient]:
        self._begin_value_operation(lease)
        try:
            request = _value_request(self, query, target,
                working_directory=working_directory, compile_arguments=compile_arguments,
                traversal_mode=traversal_mode)
            response = await self._cursor_match(request)
            return MatchValue._from_response(response, self._own_value(response))
        finally:
            self._end_value_operation()

    async def execute(
        self, source: str, *, working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] | None = None,
    ) -> Any:
        """Evaluate the console's Lark expressions and return typed live values."""
        self._begin_value_operation()
        lease = OperationLease(self)
        try:
            if self._expression_lock is None:
                self._expression_lock = asyncio.Lock()
            async with self._expression_lock:
                adapter = _AsyncExpressionAdapter(self, lease)
                runtime = _expression_runtime(self, adapter,
                                              working_directory, compile_arguments)
                runtime.client = adapter
                worker = asyncio.create_task(asyncio.to_thread(runtime.evaluate, source))
                try:
                    return await asyncio.shield(worker)
                except asyncio.CancelledError:
                    adapter.cancel()
                    await asyncio.gather(worker, return_exceptions=True)
                    raise
        finally:
            lease.close()
            self._end_value_operation()

    async def traverse(
        self, path: str | Path, *, working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (), visit_implicit_code: bool = False,
        visit_template_instantiations: bool = False, max_depth: int | None = None,
        max_nodes: int | None = None,
    ) -> traverse_response_pb2.TraverseResponse:
        request = traversal_request(path, working_directory=working_directory,
            compile_arguments=compile_arguments, visit_implicit_code=visit_implicit_code,
            visit_template_instantiations=visit_template_instantiations, max_depth=max_depth,
            max_nodes=max_nodes)
        self._ensure_stub()
        assert self._channel is not None and self.config is not None
        try:
            return await analysis_service_pb2_grpc.AnalysisServiceStub(self._channel).Traverse(
                self._compilation_request(request), timeout=self.config.rpc_timeout)
        except grpc.aio.AioRpcError as error:
            raise AnalysisError(error.code(), error.details()) from error

    async def cfg(self, path: str | Path, function: str, *,
                  working_directory: str | Path | None = None,
                  compile_arguments: Sequence[str] = (), options: CfgOptions | None = None,
                  max_functions: int | None = None, max_blocks: int | None = None,
                  max_elements: int | None = None) -> cfg_response_pb2.CfgResponse:
        request = cfg_request(path, function, working_directory=working_directory,
            compile_arguments=compile_arguments, options=options, max_functions=max_functions,
            max_blocks=max_blocks, max_elements=max_elements)
        self._ensure_stub()
        assert self._channel is not None and self.config is not None
        try:
            return await analysis_service_pb2_grpc.AnalysisServiceStub(self._channel).Cfg(
                self._compilation_request(request), timeout=self.config.rpc_timeout)
        except grpc.aio.AioRpcError as error:
            raise AnalysisError(error.code(), error.details()) from error

    async def run_script(self, source: str, *, path: str | Path | None = None,
                         working_directory: str | Path | None = None,
                         compile_arguments: Sequence[str] = (), max_steps: int | None = None
                         ) -> script_response_pb2.ScriptResponse:
        request = script_request(source, path=path, working_directory=working_directory,
            compile_arguments=compile_arguments, max_steps=max_steps)
        self._ensure_stub()
        assert self._channel is not None and self.config is not None
        try:
            return await analysis_service_pb2_grpc.AnalysisServiceStub(self._channel).RunScript(
                self._compilation_request(request), timeout=self.config.rpc_timeout)
        except grpc.aio.AioRpcError as error:
            raise AnalysisError(error.code(), error.details()) from error

    async def callgraph(self, path: str | Path, *,
                        working_directory: str | Path | None = None,
                        compile_arguments: Sequence[str] = (), visit_implicit_code: bool | None = None,
                        visit_template_instantiations: bool | None = None, max_nodes: int | None = None,
                        max_edges: int | None = None) -> call_graph_response_pb2.CallGraphResponse:
        request = call_graph_request(path, working_directory=working_directory,
            compile_arguments=compile_arguments, visit_implicit_code=visit_implicit_code,
            visit_template_instantiations=visit_template_instantiations, max_nodes=max_nodes,
            max_edges=max_edges)
        self._ensure_stub()
        assert self._channel is not None and self.config is not None
        try:
            return await analysis_service_pb2_grpc.AnalysisServiceStub(self._channel).CallGraph(
                self._compilation_request(request), timeout=self.config.rpc_timeout)
        except grpc.aio.AioRpcError as error:
            raise AnalysisError(error.code(), error.details()) from error

    async def match_file(
        self, path: str | Path, query: str, *,
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (),
        traversal_mode: int = match_service_pb2.MATCH_TRAVERSAL_MODE_AS_IS,
    ) -> match_service_pb2.MatchResponse:
        """Acquire a validated AST and create an independent result cursor."""
        return await self._cursor_match(file_request(
            path, query, working_directory=working_directory,
            compile_arguments=compile_arguments, traversal_mode=traversal_mode,
        ))

    async def continue_match(
        self, session_id: str, bind: str, query: str, *,
        match_index: int | None = None,
        scope: int = match_result_pb2.BINDING_MATCH_SCOPE_SUBTREE,
        expected_result_revision: int | None = None,
        traversal_mode: int = match_service_pb2.MATCH_TRAVERSAL_MODE_AS_IS,
    ) -> match_service_pb2.MatchResponse:
        """Replace one cursor's result using roots in its latest revision."""
        return await self._cursor_match(retained_request(
            session_id, query, bind=bind, match_index=match_index, scope=scope,
            expected_result_revision=expected_result_revision, traversal_mode=traversal_mode,
        ))

    async def restart_match(
        self, session_id: str, query: str, *, expected_result_revision: int | None = None,
        traversal_mode: int = match_service_pb2.MATCH_TRAVERSAL_MODE_AS_IS,
    ) -> match_service_pb2.MatchResponse:
        """Run again from the cursor's pinned translation-unit root."""
        return await self._cursor_match(retained_request(
            session_id, query, expected_result_revision=expected_result_revision,
            traversal_mode=traversal_mode,
        ))

    async def close_match(self, session_id: str) -> None:
        """Release a cursor; closing an unavailable valid UUID is idempotent."""
        self._ensure_stub()
        assert self._channel is not None and self.config is not None
        stub = match_service_pb2_grpc.MatchServiceStub(self._channel)
        try:
            await stub.CloseSession(match_service_pb2.CloseSessionRequest(session_id=session_id),
                                    timeout=self.config.rpc_timeout)
        except grpc.aio.AioRpcError as error:
            raise CursorError(error.code(), error.details()) from error

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
        current_loop = asyncio.get_running_loop()
        if self._loop is not None and current_loop is not self._loop:
            raise RuntimeError("AsyncClient must be closed from its owning event loop")
        self._value_closing = True
        if self._value_idle is not None:
            await self._value_idle.wait()
        if self._value_close_lock is None:
            self._value_close_lock = asyncio.Lock()
        async with self._value_close_lock:
            try:
                await self._close_resources()
            finally:
                self._value_closed = True

    async def _close_resources(self) -> None:
        errors: list[BaseException] = []
        owners = tuple(self._values.items())
        for _, reference in owners:
            owner = reference()
            if owner is not None:
                owner.closed = True
        try:
            if self._expression_runtime is not None:
                try:
                    self._expression_runtime.close()
                except BaseException as error:
                    errors.append(error)
                finally:
                    self._expression_runtime = None
            for task in tuple(self._background):
                if not task.done():
                    task.cancel()
            if self._background:
                try:
                    await asyncio.gather(*self._background, return_exceptions=True)
                except BaseException as error:
                    errors.append(error)
                self._background.clear()
            identifiers = tuple(set(self._values) | self._pending_value_cleanup)
            self._pending_value_cleanup.update(identifiers)
            outcomes = await asyncio.gather(
                *(self._close_value_cleanup(identifier) for identifier in identifiers),
                return_exceptions=True,
            )
            for identifier, outcome in zip(identifiers, outcomes):
                if isinstance(outcome, BaseException):
                    errors.append(outcome)
                else:
                    self._values.pop(identifier, None)
        finally:
            if self._channel is not None:
                try:
                    await self._channel.close()
                except BaseException as error:
                    errors.append(error)
            self._channel = None
            self._stub = None
            self._loop = None
        _raise_cleanup_errors(errors)

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
            getattr(command, command_name).CopyFrom(self.client._compilation_request(value))
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
    config: NetworkConfig | None = None
    compilation_database: str | Path | None = None
    _resolved_config: NetworkConfig | None = field(default=None, init=False, repr=False)
    _async_client: AsyncClient | None = field(default=None, init=False, repr=False)
    _async_loop: asyncio.AbstractEventLoop | None = field(default=None, init=False, repr=False)
    _query_session: QuerySession | None = field(default=None, init=False, repr=False)
    _background_handles: dict[str, BackgroundQuery] = field(default_factory=dict, init=False, repr=False)
    _values: dict[str, weakref.ReferenceType[CursorOwner[Client]]] = field(
        default_factory=dict, init=False, repr=False)
    _pending_value_cleanup: set[str] = field(default_factory=set, init=False, repr=False)
    _expression_runtime: Any = field(default=None, init=False, repr=False)

    def _configuration(self) -> NetworkConfig:
        if self._resolved_config is None:
            self._resolved_config = (load_network_config(self.config_path)
                if self.config_path is not None else self.config or load_network_config())
            self.config = self._resolved_config
        return self._resolved_config

    def _own_value(self, response: Any) -> CursorOwner[Client]:
        owner = CursorOwner(cast(Client, self), response.session_id, response.result_revision,
                             self._release_value)
        self._values[response.session_id] = weakref.ref(owner)
        return owner

    def _release_value(self, session_id: str) -> None:
        self._values.pop(session_id, None)
        self._pending_value_cleanup.add(session_id)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            try:
                self._close_value_cleanup(session_id)
            except Exception:
                # Finalizers cannot propagate failures; retain the identifier
                # so the next explicit operation or close retries cleanup.
                pass

    def _flush_value_cleanup(self) -> None:
        errors: list[BaseException] = []
        for identifier in tuple(self._pending_value_cleanup):
            try:
                self.close_match(identifier)
            except Exception as error:
                errors.append(error)
            else:
                self._pending_value_cleanup.remove(identifier)
        _raise_cleanup_errors(errors)

    def _close_value_cleanup(self, identifier: str) -> None:
        if identifier not in self._pending_value_cleanup:
            return
        self.close_match(identifier)
        self._pending_value_cleanup.discard(identifier)

    def parse(self, path: str | Path, *, working_directory: str | Path | None = None,
              compile_arguments: Sequence[str] = (), compilation_database: str | Path | None = None) -> ParsedTree[Client]:
        """Parse a file and retain a tree with automatic native ownership."""
        response = self._cursor_call("_parse_response", path,
            working_directory=working_directory, compile_arguments=compile_arguments,
            compilation_database=compilation_database)
        return ParsedTree(str(path), self._own_value(response))

    def match_in(
        self, query: str, target: MatchTarget, *,
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (),
        traversal_mode: int = match_service_pb2.MATCH_TRAVERSAL_MODE_AS_IS,
    ) -> MatchValue[Client]:
        request = _value_request(self, query, target,
            working_directory=working_directory, compile_arguments=compile_arguments,
            traversal_mode=traversal_mode)
        response = self._cursor_call("_cursor_match", request)
        return MatchValue._from_response(response, self._own_value(response))

    def close(self) -> None:
        """Release every high-level retained value owned by this client."""
        errors: list[BaseException] = []
        for identifier, reference in tuple(self._values.items()):
            owner = reference()
            if owner is not None:
                owner.closed = True
            self._pending_value_cleanup.add(identifier)
        self._values.clear()
        if self._expression_runtime is not None:
            try:
                self._expression_runtime.close()
            except Exception as error:
                errors.append(error)
            finally:
                self._expression_runtime = None
        try:
            self._flush_value_cleanup()
        except Exception as error:
            errors.append(error)
        _raise_cleanup_errors(errors)

    def execute(
        self, source: str, *, working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] | None = None,
    ) -> Any:
        """Evaluate expressions/blocks, returning reusable typed values."""
        runtime = _expression_runtime(self, self, working_directory, compile_arguments)
        return runtime.evaluate(source)

    def __enter__(self) -> Client:
        self._configuration()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _cursor_call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            raise RuntimeError("synchronous cursor methods cannot run inside an active event loop")

        config = self._configuration()

        async def run() -> Any:
            async with AsyncClient(self.address, config=config, compilation_database=self.compilation_database) as client:
                return await getattr(client, method)(*args, **kwargs)
        return asyncio.run(run())

    def match_file(self, path: str | Path, query: str, **kwargs: Any) -> match_service_pb2.MatchResponse:
        return self._cursor_call("match_file", path, query, **kwargs)

    def continue_match(self, session_id: str, bind: str, query: str, **kwargs: Any) -> match_service_pb2.MatchResponse:
        return self._cursor_call("continue_match", session_id, bind, query, **kwargs)

    def restart_match(self, session_id: str, query: str, **kwargs: Any) -> match_service_pb2.MatchResponse:
        return self._cursor_call("restart_match", session_id, query, **kwargs)

    def close_match(self, session_id: str) -> None:
        self._cursor_call("close_match", session_id)

    def traverse(self, path: str | Path, **kwargs: Any) -> traverse_response_pb2.TraverseResponse:
        return self._cursor_call("traverse", path, **kwargs)

    def bind_async_client(self, client: AsyncClient) -> None:
        """Attach the active CLI loop for commands submitted by worker threads."""
        self._async_client = client
        self._async_loop = asyncio.get_running_loop()
        config = getattr(client, "config", None)
        if self.config_path is None and config is not None:
            self.config = self._resolved_config = config
        else:
            self._configuration()

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
            self._query_session.client.compilation_database = self.compilation_database
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

    @overload
    def match(
        self, matcher: str, *, file: str | Path,
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (),
    ) -> MatchValue[Client]: ...

    @overload
    def match(
        self, matcher: str, *, files: Sequence[str | Path] | None = None,
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (), file: None = None,
    ) -> list[str]: ...

    def match(
        self, matcher: str, *, files: Sequence[str | Path] | None = None,
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (),
        file: str | Path | None = None,
    ) -> list[str] | MatchValue[Client]:
        """Run a query synchronously; bindings are returned as JSON rows."""
        if file is not None:
            if files is not None:
                raise ValueError("use either file or files, not both")
            return self.match_in(matcher, file, working_directory=working_directory,
                                 compile_arguments=compile_arguments)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            raise RuntimeError("Client.match cannot run inside an active event loop")

        config = self._configuration()

        async def run() -> list[str]:
            async with AsyncClient(self.address, config=config, compilation_database=self.compilation_database) as client:
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

    def cfg(self, function: str, *, path: str | Path | None = None,
            **kwargs: Any) -> cfg_response_pb2.CfgResponse:
        if path is None:
            raise ValueError("CFG requires a file path; pass path=...")
        return self._cursor_call("cfg", path, function, **kwargs)

    def run_script(self, source: str, *, path: str | Path | None = None,
                   working_directory: str | Path | None = None,
                   compile_arguments: Sequence[str] = (),
                   max_steps: int | None = None) -> script_response_pb2.ScriptResponse:
        return self._cursor_call("run_script", source, path=path,
            working_directory=working_directory, compile_arguments=compile_arguments,
            max_steps=max_steps)

    def callgraph(self, path: str | Path | None = None,
                  **kwargs: Any) -> call_graph_response_pb2.CallGraphResponse:
        if path is None:
            raise ValueError("callgraph requires a file path")
        return self._cursor_call("callgraph", path, **kwargs)


def _raise_cleanup_errors(errors: Sequence[BaseException]) -> None:
    if len(errors) == 1:
        raise errors[0]
    if errors:
        raise BaseExceptionGroup("client resource cleanup failed", list(errors))


class _AsyncExpressionAdapter:
    """Run the shared synchronous evaluator with calls on its owner's loop."""

    def __init__(self, client: AsyncClient, lease: OperationLease) -> None:
        self.client = client
        self.lease = lease
        self._cancelled = False
        self._future: concurrent.futures.Future[Any] | None = None

    def cancel(self) -> None:
        self._cancelled = True
        if self._future is not None:
            self._future.cancel()

    def _call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        if self._cancelled:
            raise asyncio.CancelledError
        future = asyncio.run_coroutine_threadsafe(
            getattr(self.client, method)(*args, **kwargs), self.client._loop)
        self._future = future
        if self._cancelled:
            future.cancel()
        try:
            return future.result()
        finally:
            self._future = None

    @property
    def compilation_database(self) -> str | Path | None:
        return self.client.compilation_database

    @compilation_database.setter
    def compilation_database(self, value: str | Path | None) -> None:
        self.client.compilation_database = value

    def parse(self, path: str | Path, *, working_directory: str | Path | None = None,
              compile_arguments: Sequence[str] = ()) -> ParsedTree[AsyncClient]:
        return self._call("_parse_with_lease", path,
            working_directory=working_directory, compile_arguments=compile_arguments,
            lease=self.lease)

    def match_in(self, query: str, target: MatchTarget, *,
                 working_directory: str | Path | None = None,
                 compile_arguments: Sequence[str] = (),
                 traversal_mode: match_service_pb2.MatchTraversalMode = match_service_pb2.MATCH_TRAVERSAL_MODE_AS_IS
                 ) -> MatchValue[AsyncClient]:
        return self._call("_match_in_with_lease", query, target,
            working_directory=working_directory, compile_arguments=compile_arguments,
            traversal_mode=traversal_mode, lease=self.lease)

    def match(self, query: str, *, files: Sequence[str] | None = None,
              **kwargs: Any) -> list[Any]:
        return self._call("match", query, files or (), **kwargs)


def _expression_runtime(owner: Client | AsyncClient, adapter: Any,
                        working_directory: str | Path | None,
                        compile_arguments: Sequence[str] | None) -> Any:
    from clang_toolkit.cli.runtime.evaluator import Runtime
    if owner._expression_runtime is None:
        owner._expression_runtime = Runtime(adapter, cwd=Path(working_directory)
                                            if working_directory is not None else None)
    runtime = owner._expression_runtime
    if working_directory is not None and Path(working_directory).resolve() != runtime.cwd:
        raise ValueError("expression execution uses one working directory per client")
    if compile_arguments is not None:
        runtime.config_store.effective["extra_args"] = list(compile_arguments)
    return runtime


def _value_request(
    client: Client | AsyncClient, query: str, target: MatchTarget | Path, *,
    working_directory: str | Path | None = None,
    compile_arguments: Sequence[str] = (),
    traversal_mode: int = match_service_pb2.MATCH_TRAVERSAL_MODE_AS_IS,
) -> match_service_pb2.MatchRequest:
    if isinstance(target, str | Path):
        return file_request(target, query, working_directory=working_directory,
                            compile_arguments=compile_arguments,
                            traversal_mode=traversal_mode)
    if not isinstance(target, ParsedTree | MatchValue | BindingSelection):
        raise TypeError("match target must be a file path, parsed tree or binding selection")
    target._owner.check(client)
    options: dict[str, Any] = {}
    if isinstance(target, BindingSelection):
        options.update(bind=target.name, match_index=target._index, scope=target.scope)
    request = retained_request(target._owner.session_id, query,
        expected_result_revision=target._owner.revision,
        traversal_mode=traversal_mode, **options)
    request.preserve_source = True
    return request


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
