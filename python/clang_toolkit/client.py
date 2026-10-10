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
from threading import Lock
from collections.abc import AsyncIterator, Awaitable, Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, cast, overload

import grpc
from google.protobuf.message import DecodeError

from clang_toolkit._generated.query.v1 import query_pb2, query_pb2_grpc
from clang_toolkit.configuration import NetworkConfig, load_network_config
from clang_toolkit.version import VersionInfo
from clang_toolkit.cursors import CursorError, file_request, retained_request
from clang_toolkit._generated.match.v1 import match_service_pb2, match_service_pb2_grpc
from clang_toolkit._generated.match.v1 import match_result_pb2
from clang_toolkit._generated.match.v1 import match_stream_pb2
from clang_toolkit._generated.match.v1 import resources_pb2
from clang_toolkit._generated.analysis.v1 import analysis_service_pb2_grpc, traverse_response_pb2, cfg_response_pb2, call_graph_response_pb2
from clang_toolkit._generated.analysis.v1 import batch_pb2
from clang_toolkit.batches import BatchRun, batch_run, start_batch_request
from clang_toolkit.analysis_error import AnalysisError
from clang_toolkit.traversal import traversal_request
from clang_toolkit.control_flow import CfgOptions, cfg_request
from clang_toolkit.call_graph import call_graph_request
from clang_toolkit.match_values import (
    BindingSelection, MatchTarget, MatchValue, MatchValueError, ParsedTree,
)
from clang_toolkit.matchers import MatcherInput, matcher_query
from clang_toolkit.resources import (
    FileHandle,
    FileSet,
    InputDescriptor,
    ResourceScope,
    _preserve_cleanup_error,
)
from clang_toolkit._value_lifecycle import CursorOwner, OperationLease
from clang_toolkit._row_store import RowStore
from clang_toolkit._generated.match.v1 import parse_request_pb2, parse_response_pb2

QueryEvent = query_pb2.QueryEvent
EventCallback = Callable[[QueryEvent], Any | Awaitable[Any]]
AsyncMatchRowCallback = Callable[[match_result_pb2.MatchResult], Any | Awaitable[Any]]
MatchRowCallback = Callable[[match_result_pb2.MatchResult], None]


async def _invoke_sync_callback(callback: MatchRowCallback,
                                row: match_result_pb2.MatchResult) -> None:
    """Run blocking row work outside the RPC loop and join it on cancellation."""
    def invoke() -> None:
        outcome = callback(row)
        if inspect.isawaitable(outcome):
            if inspect.iscoroutine(outcome):
                outcome.close()
            raise TypeError("synchronous on_row callbacks must not return awaitables")

    worker = asyncio.create_task(asyncio.to_thread(invoke))
    try:
        await asyncio.shield(worker)
    except asyncio.CancelledError:
        await asyncio.gather(worker, return_exceptions=True)
        raise


class _MatchStreamCall(Protocol):
    def __aiter__(self) -> AsyncIterator[match_stream_pb2.MatchStreamEvent]: ...

    def code(self) -> grpc.StatusCode | Awaitable[grpc.StatusCode]: ...

    def details(self) -> str | Awaitable[str]: ...

    def cancel(self) -> bool: ...


class _MatchStreamStub(Protocol):
    def StreamMatch(
        self, request: match_service_pb2.MatchRequest, *, timeout: float | None = None,
    ) -> _MatchStreamCall: ...


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
    _file_leases: set[str] = field(default_factory=set, init=False, repr=False)
    _resource_scopes: dict[str, ResourceScope[AsyncClient]] = field(default_factory=dict, init=False, repr=False)
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
        if (hasattr(request, "compilation_database") and not request.compilation_database
                and not getattr(request, "frozen_profile", False)):
            request.compilation_database = selected
        if hasattr(request, "file") and request.HasField("file"):
            if not request.file.compilation_database and not getattr(request.file, "frozen_profile", False):
                request.file.compilation_database = selected
        if hasattr(request, "profile") and request.HasField("profile"):
            if (not request.profile.compilation_database
                    and not getattr(request.profile, "frozen", False)):
                request.profile.compilation_database = selected
        if hasattr(request, "input") and request.HasField("input"):
            if (not request.input.profile.compilation_database
                    and not request.input.profile.frozen):
                request.input.profile.compilation_database = selected
        for input_descriptor in getattr(request, "inputs", ()):
            if (not input_descriptor.profile.compilation_database
                    and not input_descriptor.profile.frozen):
                input_descriptor.profile.compilation_database = selected
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

    async def server_version(self) -> VersionInfo:
        """Return the connected server binary's build identity."""
        stub = self._ensure_stub()
        assert self.config is not None
        try:
            response = await stub.GetVersion(query_pb2.VersionRequest(), timeout=self.config.rpc_timeout or 5.0)
        except grpc.aio.AioRpcError as error:
            if error.code() == grpc.StatusCode.UNIMPLEMENTED:
                raise QueryError("connected server does not support version reporting; update and restart it") from error
            raise QueryError(f"server version request failed: {error.code().name}: {error.details()}") from error
        return VersionInfo(response.version, response.revision)

    async def _resource_call(self, method: str, request: Any) -> Any:
        self._ensure_stub()
        assert self._channel is not None and self.config is not None
        stub = match_service_pb2_grpc.MatchServiceStub(self._channel)
        try:
            return await getattr(stub, method)(
                self._compilation_request(request), timeout=self.config.rpc_timeout
            )
        except grpc.aio.AioRpcError as error:
            raise CursorError(error.code(), error.details()) from error

    async def discover_files(
        self,
        paths: Sequence[str | Path] = (),
        *,
        inputs: Sequence[InputDescriptor] = (),
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (),
        compilation_database: str | Path | None = None,
        max_inputs: int | None = None,
        max_metadata_bytes: int | None = None,
    ) -> FileSet:
        """Discover server-side paths as frozen metadata without parsing ASTs."""
        if paths and inputs:
            raise ValueError("provide paths or inputs, not both")
        profile = resources_pb2.CompilationProfile(
            compile_arguments=compile_arguments,
            working_directory=str(working_directory) if working_directory is not None else str(Path.cwd()),
            compilation_database=str(compilation_database or self.compilation_database or ""),
        )
        request = resources_pb2.DiscoverFilesRequest(
            paths=[str(path) for path in paths],
            profile=profile,
            inputs=[item.to_proto() for item in inputs],
        )
        if max_inputs is not None:
            request.max_inputs = max_inputs
        if max_metadata_bytes is not None:
            request.max_metadata_bytes = max_metadata_bytes
        response = await self._resource_call("DiscoverFiles", request)
        return FileSet(
            tuple(InputDescriptor.from_proto(item) for item in response.inputs),
            tuple(response.diagnostics),
            response.metadata_bytes,
        )

    async def open_file(
        self,
        value: str | Path | InputDescriptor,
        *,
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (),
        compilation_database: str | Path | None = None,
        scope: ResourceScope[AsyncClient] | str | None = None,
    ) -> FileHandle[AsyncClient]:
        descriptor = value if isinstance(value, InputDescriptor) else InputDescriptor.from_path(
            value, working_directory=working_directory, compile_arguments=compile_arguments,
            compilation_database=compilation_database or self.compilation_database,
        )
        request = resources_pb2.OpenFileRequest(
            input=descriptor.to_proto(), resource_scope_id=_scope_id(scope)
        )
        info = await self._resource_call("OpenFile", request)
        handle = _file_handle(self, info)
        if scope is None:
            self._file_leases.add(handle.lease_id)
        return handle

    async def list_files(self) -> tuple[Any, ...]:
        response = await self._resource_call("ListFiles", resources_pb2.ListFilesRequest())
        return tuple(response.files)

    async def file_info(self, handle: FileHandle[AsyncClient] | ParsedTree[AsyncClient]) -> Any:
        request = resources_pb2.DescribeFileRequest()
        if isinstance(handle, FileHandle):
            request.lease_id = handle.lease_id
        else:
            request.session_id = handle._owner.session_id
        return await self._resource_call("DescribeFile", request)

    async def close_file(
        self, handle: FileHandle[AsyncClient] | ParsedTree[AsyncClient] | str,
    ) -> Any:
        request = resources_pb2.CloseFileRequest()
        if isinstance(handle, FileHandle):
            request.lease_id = handle.lease_id
        elif isinstance(handle, str):
            request.lease_id = handle
        else:
            request.session_id = handle._owner.session_id
        try:
            response = await self._resource_call("CloseFile", request)
        except CursorError as error:
            if (
                request.WhichOneof("handle") != "lease_id"
                or error.code != grpc.StatusCode.NOT_FOUND
            ):
                raise
            # Closing a lease is idempotent. NOT_FOUND means it was already
            # released or expired; it must not remain in shutdown tracking.
            response = resources_pb2.CloseFileResponse()
        if request.WhichOneof("handle") == "lease_id":
            self._file_leases.discard(request.lease_id)
        return response

    async def close_all_files(self) -> Any:
        response = await self._resource_call("CloseAllFiles", resources_pb2.CloseAllFilesRequest())
        self._file_leases.clear()
        return response

    async def refresh_file(
        self,
        handle: FileHandle[AsyncClient] | ParsedTree[AsyncClient],
        *,
        scope: ResourceScope[AsyncClient] | str | None = None,
    ) -> FileHandle[AsyncClient]:
        request = resources_pb2.RefreshFileRequest(resource_scope_id=_scope_id(scope))
        if isinstance(handle, FileHandle):
            request.lease_id = handle.lease_id
        else:
            request.session_id = handle._owner.session_id
        refreshed = _file_handle(self, await self._resource_call("RefreshFile", request))
        if scope is None:
            self._file_leases.add(refreshed.lease_id)
        return refreshed

    async def open_resource_scope(
        self,
        *,
        inputs: Sequence[InputDescriptor] = (),
        memory_bytes: int | None = None,
        jobs: int | None = None,
        transient: bool = False,
        ttl_ms: int | None = None,
    ) -> ResourceScope[AsyncClient]:
        request = resources_pb2.OpenResourceScopeRequest(
            inputs=[item.to_proto() for item in inputs], transient=transient
        )
        if memory_bytes is not None:
            request.memory_bytes = memory_bytes
        if jobs is not None:
            request.jobs = jobs
        if ttl_ms is not None:
            request.ttl_ms = ttl_ms
        info = await self._resource_call("OpenResourceScope", request)
        if not info.resource_scope_id:
            raise CursorError(grpc.StatusCode.DATA_LOSS, "resource scope reply has no scope ID")
        scope = ResourceScope(info.resource_scope_id, info, self)
        self._resource_scopes[scope.resource_scope_id] = scope
        return scope

    async def describe_resource_scope(
        self, scope: ResourceScope[AsyncClient] | str,
    ) -> Any:
        return await self._resource_call(
            "DescribeResourceScope",
            resources_pb2.ResourceScopeRequest(resource_scope_id=_scope_id(scope)),
        )

    async def cancel_resource_scope(
        self, scope: ResourceScope[AsyncClient] | str,
    ) -> Any:
        return await self._resource_call(
            "CancelResourceScope",
            resources_pb2.ResourceScopeRequest(resource_scope_id=_scope_id(scope)),
        )

    async def release_resource_scope(
        self, scope: ResourceScope[AsyncClient] | str,
    ) -> Any:
        info = await self._resource_call(
            "ReleaseResourceScope",
            resources_pb2.ResourceScopeRequest(resource_scope_id=_scope_id(scope)),
        )
        if info.cleanup_acknowledged:
            self._resource_scopes.pop(_scope_id(scope), None)
        return info

    async def resource_status(self) -> Any:
        return await self._resource_call(
            "ResourceStatus", resources_pb2.ResourceStatusRequest()
        )

    async def iter_events(
        self,
        query: MatcherInput,
        files: Sequence[str | Path] = (),
        *,
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (),
    ) -> AsyncIterator[QueryEvent]:
        """Yield events, requiring both a Completed event and terminal OK."""
        stub = self._ensure_stub()
        assert self.config is not None
        request = query_pb2.QueryRequest(
            query=matcher_query(query),
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
        expression: MatcherInput,
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
        self, expression: MatcherInput, files: Sequence[str | Path] = (), *,
        file: str | Path, working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (),
    ) -> MatchValue[AsyncClient]: ...

    @overload
    async def match(
        self, expression: MatcherInput, files: Sequence[str | Path] = (), *,
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (), file: None = None,
    ) -> list[query_pb2.MatchEvent]: ...

    async def match(
        self,
        expression: MatcherInput,
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

    async def _stream_cursor_match(
        self,
        request: match_service_pb2.MatchRequest,
        *,
        on_row: AsyncMatchRowCallback | None = None,
        source_session_id: str | None = None,
    ) -> tuple[match_stream_pb2.MatchStreamCompleted, RowStore]:
        """Consume provisional rows and return them only after a valid terminal OK."""
        self._ensure_stub()
        assert self._channel is not None and self.config is not None
        stub = cast(
            _MatchStreamStub,
            match_service_pb2_grpc.MatchServiceStub(self._channel),
        )
        store = RowStore()
        call: _MatchStreamCall | None = None
        completed: match_stream_pb2.MatchStreamCompleted | None = None
        row_count = 0
        succeeded = False
        try:
            call = stub.StreamMatch(
                self._compilation_request(request), timeout=self.config.rpc_timeout
            )
            async for event in call:
                kind = event.WhichOneof("event")
                if kind == "row":
                    if completed is not None:
                        raise CursorError(grpc.StatusCode.DATA_LOSS,
                                          "match stream delivered a row after completion")
                    row_bytes = event.row.SerializeToString()
                    store.append(row_bytes, binding_names=event.row.bindings)
                    row_count += 1
                    if on_row is not None:
                        detached = match_result_pb2.MatchResult()
                        detached.ParseFromString(row_bytes)
                        outcome = on_row(detached)
                        if inspect.isawaitable(outcome):
                            await outcome
                elif kind == "completed":
                    if completed is not None:
                        raise CursorError(grpc.StatusCode.DATA_LOSS,
                                          "match stream delivered duplicate completion")
                    completed = match_stream_pb2.MatchStreamCompleted()
                    completed.CopyFrom(event.completed)
                    if (not completed.session_id or completed.result_revision <= 0
                            or completed.row_count < 0 or not completed.HasField("expires_at")):
                        raise CursorError(grpc.StatusCode.DATA_LOSS,
                                          "match stream completion metadata is invalid")
                    if completed.row_count != row_count:
                        raise CursorError(
                            grpc.StatusCode.DATA_LOSS,
                            f"match stream row count mismatch: expected {completed.row_count}, received {row_count}",
                        )
                else:
                    raise CursorError(grpc.StatusCode.DATA_LOSS,
                                      "match stream delivered an unknown event")

            if completed is None:
                raise CursorError(grpc.StatusCode.DATA_LOSS,
                                  "match stream ended without completion")
            assert call is not None
            status_result = call.code()
            status = await status_result if inspect.isawaitable(status_result) else status_result
            if status != grpc.StatusCode.OK:
                details_result = call.details()
                details = (await details_result if inspect.isawaitable(details_result)
                           else details_result)
                raise CursorError(status, details or "match stream did not finish with OK")
            store.flush()
            succeeded = True
            return completed, store
        except grpc.aio.AioRpcError as error:
            raise CursorError(error.code(), error.details() or "match stream RPC failed") from error
        finally:
            if not succeeded:
                if call is not None:
                    try:
                        call.cancel()
                    except BaseException:
                        pass
                try:
                    store.close()
                except BaseException:
                    pass
                if (completed is not None and completed.session_id
                        and completed.session_id != source_session_id):
                    try:
                        cleanup = asyncio.create_task(self.close_match(completed.session_id))
                        cleanup.add_done_callback(
                            lambda task: task.exception() if not task.cancelled() else None
                        )
                        await asyncio.shield(cleanup)
                    except BaseException:
                        # Cleanup is best effort; preserve the original stream failure.
                        pass

    async def _parse_response(
        self, path: str | Path | InputDescriptor, *, working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (), compilation_database: str | Path | None = None,
        scope: ResourceScope[AsyncClient] | str | None = None,
    ) -> parse_response_pb2.ParseResponse:
        self._ensure_stub()
        assert self._channel is not None and self.config is not None
        descriptor = path if isinstance(path, InputDescriptor) else None
        source_path = descriptor.path if descriptor is not None else str(path)
        request = parse_request_pb2.ParseRequest(
            file_path=source_path,
            compile_arguments=(descriptor.compile_arguments if descriptor else compile_arguments),
            compilation_database=(descriptor.compilation_database if descriptor else
                                  str(compilation_database or "")),
            working_directory=(descriptor.working_directory if descriptor and descriptor.working_directory else
                               str(working_directory) if working_directory is not None else str(Path.cwd())),
            resource_scope_id=_scope_id(scope),
        )
        if descriptor is not None and descriptor.profile_id:
            request.expected_profile_id = descriptor.profile_id
        if descriptor is not None:
            request.frozen_profile = descriptor.frozen_profile
        try:
            return await match_service_pb2_grpc.MatchServiceStub(self._channel).Parse(
                self._compilation_request(request), timeout=self.config.rpc_timeout)
        except grpc.aio.AioRpcError as error:
            raise CursorError(error.code(), error.details()) from error

    def _own_value(self, response: Any) -> CursorOwner[AsyncClient]:
        current = self._values.get(response.session_id)
        existing = current() if current else None
        if existing is not None and not existing.closed and existing.revision == response.result_revision:
            return existing
        holder: list[Any] = [None]
        def release(session_id: str) -> None:
            if self._values.get(session_id) is holder[0]:
                self._release_value(session_id)
        owner = CursorOwner(cast(AsyncClient, self), response.session_id, response.result_revision,
                             release, loop=asyncio.get_running_loop())
        holder[0] = self._values[response.session_id] = weakref.ref(owner)
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
        self, path: str | Path | InputDescriptor, *, working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (), compilation_database: str | Path | None = None,
        scope: ResourceScope[AsyncClient] | str | None = None,
    ) -> ParsedTree[AsyncClient]:
        """Parse a file once and retain a reusable immutable native tree."""
        return await self._parse_with_lease(path, working_directory=working_directory,
                                            compile_arguments=compile_arguments, compilation_database=compilation_database,
                                            lease=None, scope=scope)

    async def _parse_with_lease(
        self, path: str | Path | InputDescriptor, *, working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (), compilation_database: str | Path | None = None,
        lease: OperationLease | None, scope: ResourceScope[AsyncClient] | str | None = None,
    ) -> ParsedTree[AsyncClient]:
        self._begin_value_operation(lease)
        try:
            response = await self._parse_response(path, working_directory=working_directory,
                compile_arguments=compile_arguments, compilation_database=compilation_database,
                scope=scope)
            return ParsedTree(
                path.path if isinstance(path, InputDescriptor) else str(path), self._own_value(response),
                _absolute_source_file(path, working_directory),
            )
        finally:
            self._end_value_operation()

    async def match_in(
        self, query: MatcherInput, target: MatchTarget | Path, *,
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (),
        traversal_mode: match_service_pb2.MatchTraversalMode = match_service_pb2.MATCH_TRAVERSAL_MODE_AS_IS,
        on_row: AsyncMatchRowCallback | None = None,
        scope: ResourceScope[AsyncClient] | str | None = None,
    ) -> MatchValue[AsyncClient]:
        """Match a path, pinned tree or binding selection without changing it."""
        return await self._match_in_with_lease(query, target,
            working_directory=working_directory, compile_arguments=compile_arguments,
            traversal_mode=traversal_mode, on_row=on_row, lease=None, scope=scope)

    async def _match_in_with_lease(
        self, query: MatcherInput, target: MatchTarget, *,
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (),
        traversal_mode: match_service_pb2.MatchTraversalMode = match_service_pb2.MATCH_TRAVERSAL_MODE_AS_IS,
        on_row: AsyncMatchRowCallback | None = None,
        lease: OperationLease | None, scope: ResourceScope[AsyncClient] | str | None = None,
    ) -> MatchValue[AsyncClient]:
        self._begin_value_operation(lease)
        try:
            request = _value_request(self, query, target,
                working_directory=working_directory, compile_arguments=compile_arguments,
                traversal_mode=traversal_mode, scope=scope)
            source_id = target._owner.session_id if isinstance(
                target, (ParsedTree, MatchValue, BindingSelection)
            ) else None
            completion, store = await self._stream_cursor_match(
                request, on_row=on_row, source_session_id=source_id
            )
            return MatchValue[AsyncClient]._from_store(
                store, self._own_value(completion),
                source_file=_absolute_source_file(target, working_directory),
            )
        finally:
            self._end_value_operation()

    async def execute(
        self, source: str, *, working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] | None = None,
        scope: ResourceScope[AsyncClient] | str | None = None,
    ) -> Any:
        """Evaluate the console's Lark expressions and return typed live values."""
        self._begin_value_operation()
        lease = OperationLease(self)
        try:
            if self._expression_lock is None:
                self._expression_lock = asyncio.Lock()
            async with self._expression_lock:
                adapter = _AsyncExpressionAdapter(self, lease, scope)
                runtime = _expression_runtime(self, adapter,
                                              working_directory, compile_arguments)
                runtime.client = adapter
                worker = asyncio.create_task(asyncio.to_thread(runtime.evaluate, source))
                try:
                    return await asyncio.shield(worker)
                except asyncio.CancelledError:
                    adapter.cancel()
                    await asyncio.gather(worker, return_exceptions=True)
                    await adapter.wait_callbacks()
                    raise
        finally:
            lease.close()
            self._end_value_operation()

    async def traverse(
        self, path: str | Path | FileHandle[AsyncClient] | InputDescriptor, *, working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (), visit_implicit_code: bool = False,
        visit_template_instantiations: bool = False, max_depth: int | None = None,
        max_nodes: int | None = None, projection: str = "shallow",
        main_file_only: bool = False, payload_depth: int = 24,
        payload_nodes: int = 10000, scope: ResourceScope[AsyncClient] | str | None = None,
    ) -> traverse_response_pb2.TraverseResponse:
        path, input_descriptor = _analysis_input(path)
        request = traversal_request(path, working_directory=working_directory,
            compile_arguments=compile_arguments, visit_implicit_code=visit_implicit_code,
            visit_template_instantiations=visit_template_instantiations, max_depth=max_depth,
            max_nodes=max_nodes, projection=projection, main_file_only=main_file_only,
            payload_depth=payload_depth, payload_nodes=payload_nodes)
        _apply_input_descriptor(request.file, input_descriptor)
        request.resource_scope_id = _scope_id(scope)
        self._ensure_stub()
        assert self._channel is not None and self.config is not None
        try:
            return await analysis_service_pb2_grpc.AnalysisServiceStub(self._channel).Traverse(
                self._compilation_request(request), timeout=self.config.rpc_timeout)
        except grpc.aio.AioRpcError as error:
            raise AnalysisError(error.code(), error.details()) from error

    async def cfg(self, path: str | Path | FileHandle[AsyncClient] | InputDescriptor, function: str, *,
                  working_directory: str | Path | None = None,
                  compile_arguments: Sequence[str] = (), options: CfgOptions | None = None,
                  max_functions: int | None = None, max_blocks: int | None = None,
                  max_elements: int | None = None, projection: str = "shallow",
                  main_file_only: bool = False, payload_depth: int = 24,
                  payload_nodes: int = 10000,
                  scope: ResourceScope[AsyncClient] | str | None = None) -> cfg_response_pb2.CfgResponse:
        path, input_descriptor = _analysis_input(path)
        request = cfg_request(path, function, working_directory=working_directory,
            compile_arguments=compile_arguments, options=options, max_functions=max_functions,
            max_blocks=max_blocks, max_elements=max_elements, projection=projection,
            main_file_only=main_file_only, payload_depth=payload_depth,
            payload_nodes=payload_nodes)
        _apply_input_descriptor(request.file, input_descriptor)
        request.resource_scope_id = _scope_id(scope)
        self._ensure_stub()
        assert self._channel is not None and self.config is not None
        try:
            return await analysis_service_pb2_grpc.AnalysisServiceStub(self._channel).Cfg(
                self._compilation_request(request), timeout=self.config.rpc_timeout)
        except grpc.aio.AioRpcError as error:
            raise AnalysisError(error.code(), error.details()) from error

    async def run_script(
                         self, source: str, *,
                         path: str | Path | FileHandle[AsyncClient] | InputDescriptor | None = None,
                         working_directory: str | Path | None = None,
                         compile_arguments: Sequence[str] = (), max_steps: int | None = None,
                         profile: InputDescriptor | None = None,
                         scope: ResourceScope[AsyncClient] | str | None = None,
                         ) -> script_response_pb2.ScriptResponse:
        request = script_request(source, path=path, working_directory=working_directory,
            compile_arguments=compile_arguments, max_steps=max_steps, profile=profile)
        request.resource_scope_id = _scope_id(scope)
        self._ensure_stub()
        assert self._channel is not None and self.config is not None
        try:
            return await analysis_service_pb2_grpc.AnalysisServiceStub(self._channel).RunScript(
                self._compilation_request(request), timeout=self.config.rpc_timeout)
        except grpc.aio.AioRpcError as error:
            raise AnalysisError(error.code(), error.details()) from error

    async def start_batch(
        self,
        inputs: FileSet | Sequence[InputDescriptor],
        body_source: str,
        *,
        group_variable: str = "part",
        size: int | None = None,
        count: int | None = None,
        jobs: int | None = None,
        memory_bytes: int | None = None,
        continue_on_error: bool = False,
        request_id: str | None = None,
    ) -> BatchRun:
        """Start or recover an idempotent server-owned durable batch."""
        request = start_batch_request(
            inputs,
            body_source,
            group_variable=group_variable,
            size=size,
            count=count,
            jobs=jobs,
            memory_bytes=memory_bytes,
            continue_on_error=continue_on_error,
            request_id=request_id,
        )
        self._ensure_stub()
        assert self._channel is not None and self.config is not None
        try:
            result = await analysis_service_pb2_grpc.AnalysisServiceStub(self._channel).StartBatch(
                self._compilation_request(request), timeout=self.config.rpc_timeout
            )
            return batch_run(result)
        except grpc.aio.AioRpcError as error:
            raise AnalysisError(error.code(), error.details()) from error

    async def batch_status(self, run: BatchRun | str) -> BatchRun:
        """Fetch current durable status after a disconnect or client restart."""
        request = batch_pb2.BatchRunRequest(
            run_id=run.run_id if isinstance(run, BatchRun) else run
        )
        self._ensure_stub()
        assert self._channel is not None and self.config is not None
        try:
            result = await analysis_service_pb2_grpc.AnalysisServiceStub(self._channel).BatchStatus(
                request, timeout=self.config.rpc_timeout
            )
            return batch_run(result)
        except grpc.aio.AioRpcError as error:
            raise AnalysisError(error.code(), error.details()) from error

    async def _control_batch(
        self, method: str, run: BatchRun | str, expected_revision: int | None
    ) -> BatchRun:
        if isinstance(run, BatchRun):
            run_id = run.run_id
            revision = run.revision if expected_revision is None else expected_revision
        else:
            run_id = run
            if expected_revision is None:
                raise ValueError("expected_revision is required when a run id is used")
            revision = expected_revision
        request = batch_pb2.BatchControlRequest(
            run_id=run_id, expected_revision=revision
        )
        self._ensure_stub()
        assert self._channel is not None and self.config is not None
        try:
            result = await getattr(
                analysis_service_pb2_grpc.AnalysisServiceStub(self._channel), method
            )(request, timeout=self.config.rpc_timeout)
            return batch_run(result)
        except grpc.aio.AioRpcError as error:
            raise AnalysisError(error.code(), error.details()) from error

    async def cancel_batch(
        self, run: BatchRun | str, *, expected_revision: int | None = None
    ) -> BatchRun:
        return await self._control_batch("CancelBatch", run, expected_revision)

    async def resume_batch(
        self, run: BatchRun | str, *, expected_revision: int | None = None
    ) -> BatchRun:
        return await self._control_batch("ResumeBatch", run, expected_revision)

    async def retry_batch(
        self, run: BatchRun | str, *, expected_revision: int | None = None
    ) -> BatchRun:
        return await self._control_batch("RetryBatch", run, expected_revision)

    async def callgraph(self, path: str | Path | FileHandle[AsyncClient] | InputDescriptor, *,
                        working_directory: str | Path | None = None,
                        compile_arguments: Sequence[str] = (), visit_implicit_code: bool | None = None,
                        visit_template_instantiations: bool | None = None, max_nodes: int | None = None,
                        max_edges: int | None = None, projection: str = "shallow",
                        main_file_only: bool = False, payload_depth: int = 24,
                        payload_nodes: int = 10000,
                        scope: ResourceScope[AsyncClient] | str | None = None) -> call_graph_response_pb2.CallGraphResponse:
        path, input_descriptor = _analysis_input(path)
        request = call_graph_request(path, working_directory=working_directory,
            compile_arguments=compile_arguments, visit_implicit_code=visit_implicit_code,
            visit_template_instantiations=visit_template_instantiations, max_nodes=max_nodes,
            max_edges=max_edges, projection=projection, main_file_only=main_file_only,
            payload_depth=payload_depth, payload_nodes=payload_nodes)
        _apply_input_descriptor(request.file, input_descriptor)
        request.resource_scope_id = _scope_id(scope)
        self._ensure_stub()
        assert self._channel is not None and self.config is not None
        try:
            return await analysis_service_pb2_grpc.AnalysisServiceStub(self._channel).CallGraph(
                self._compilation_request(request), timeout=self.config.rpc_timeout)
        except grpc.aio.AioRpcError as error:
            raise AnalysisError(error.code(), error.details()) from error

    async def match_file(
        self, path: str | Path, query: MatcherInput, *,
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
        self, session_id: str, bind: str, query: MatcherInput, *,
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
        self, session_id: str, query: MatcherInput, *, expected_result_revision: int | None = None,
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
        reference = self._values.pop(session_id, None)
        owner = reference() if reference else None
        if owner is not None:
            owner.closed = True

    async def _management_call(self, method: str, request: Any) -> Any:
        self._ensure_stub()
        assert self._channel is not None and self.config is not None
        stub = match_service_pb2_grpc.MatchServiceStub(self._channel)
        try:
            return await getattr(stub, method)(request, timeout=self.config.rpc_timeout)
        except grpc.aio.AioRpcError as error:
            raise CursorError(error.code(), error.details()) from error

    async def server_status(self) -> match_service_pb2.ServerStatusResponse:
        """Read live process, retained cursor, memory cache and disk artifact usage."""
        return await self._management_call("ServerStatus", match_service_pb2.ServerStatusRequest())

    async def list_sessions(self) -> match_service_pb2.ListSessionsResponse:
        """List retained cursors visible to the transport's caller owner."""
        return await self._management_call("ListSessions", match_service_pb2.ListSessionsRequest())

    async def _session_info(self, session_id: str) -> match_service_pb2.SessionInfo:
        return await self._management_call("AttachSession", match_service_pb2.AttachSessionRequest(session_id=session_id))

    async def attach_session(self, session_id: str) -> ParsedTree[AsyncClient]:
        """Attach the latest cursor revision as a reusable tree and renew its TTL."""
        self._begin_value_operation()
        try:
            response = await self._session_info(session_id)
            return ParsedTree(
                response.file_path, self._own_value(response),
                _absolute_source_file(response.file_path),
            )
        finally:
            self._end_value_operation()

    async def prune_caches(self, *, memory: bool = True, disk: bool = False
                           ) -> match_service_pb2.PruneCachesResponse:
        """Prune reusable entries; active cursor pins and storage leases survive."""
        return await self._management_call("PruneCaches", match_service_pb2.PruneCachesRequest(memory=memory, disk=disk))

    def start_background_query(
        self,
        expression: MatcherInput,
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
            for scope_id, scope in tuple(self._resource_scopes.items()):
                try:
                    await scope.arelease()
                except BaseException as error:
                    errors.append(error)
                else:
                    self._resource_scopes.pop(scope_id, None)
            for lease_id in tuple(self._file_leases):
                try:
                    await self.close_file(lease_id)
                except BaseException as error:
                    errors.append(error)
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

    async def __aexit__(
        self, exc_type: object, exc: BaseException | None, tb: object
    ) -> None:
        try:
            await self.aclose()
        except BaseException as cleanup:
            _preserve_cleanup_error(exc, cleanup, "async client")


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
        self._closing = False

    @property
    def closing(self) -> bool:
        """Whether the client is intentionally shutting down this stream."""
        return self._closing

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
            raise RuntimeError("query session is closed")
        if self._call is None or self._call.done():
            raise RuntimeError("query session stream has ended")
        command = query_pb2.QueryCommand(request_id=uuid.uuid4().hex)
        if value is None:
            getattr(command, command_name).SetInParent()
        else:
            getattr(command, command_name).CopyFrom(self.client._compilation_request(value))
        self._commands.put_nowait(command)
        return command.request_id

    async def start_query(self, query: MatcherInput) -> str:
        return self._send("start_query", query_pb2.StartQuery(query=matcher_query(query)))

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
        self._closing = True
        self._call.cancel()
        if not self._input_closed:
            self._input_closed = True
            self._commands.put_nowait(None)

    async def aclose(self) -> None:
        self._closing = True
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
    _last_session_command: str | None = field(default=None, init=False, repr=False)
    _last_session_command_request_id: str | None = field(default=None, init=False, repr=False)
    _background_handles: dict[str, BackgroundQuery] = field(default_factory=dict, init=False, repr=False)
    _values: dict[str, weakref.ReferenceType[CursorOwner[Client]]] = field(
        default_factory=dict, init=False, repr=False)
    _pending_value_cleanup: set[str] = field(default_factory=set, init=False, repr=False)
    _file_leases: set[str] = field(default_factory=set, init=False, repr=False)
    _resource_scopes: dict[str, ResourceScope[Client]] = field(default_factory=dict, init=False, repr=False)
    _expression_runtime: Any = field(default=None, init=False, repr=False)

    def _configuration(self) -> NetworkConfig:
        if self._resolved_config is None:
            self._resolved_config = (load_network_config(self.config_path)
                if self.config_path is not None else self.config or load_network_config())
            self.config = self._resolved_config
        return self._resolved_config

    def server_version(self) -> VersionInfo:
        """Return the connected server binary's build identity."""
        return self._cursor_call("server_version")

    def _own_value(self, response: Any) -> CursorOwner[Client]:
        current = self._values.get(response.session_id)
        existing = current() if current else None
        if existing is not None and not existing.closed and existing.revision == response.result_revision:
            return existing
        holder: list[Any] = [None]
        def release(session_id: str) -> None:
            if self._values.get(session_id) is holder[0]:
                self._release_value(session_id)
        owner = CursorOwner(cast(Client, self), response.session_id, response.result_revision,
                             release)
        holder[0] = self._values[response.session_id] = weakref.ref(owner)
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

    def parse(self, path: str | Path | InputDescriptor, *, working_directory: str | Path | None = None,
              compile_arguments: Sequence[str] = (), compilation_database: str | Path | None = None,
              scope: ResourceScope[Client] | str | None = None) -> ParsedTree[Client]:
        """Parse a file and retain a tree with automatic native ownership."""
        response = self._cursor_call("_parse_response", path,
            working_directory=working_directory, compile_arguments=compile_arguments,
            compilation_database=compilation_database, scope=scope)
        return ParsedTree(
            str(path), self._own_value(response),
            _absolute_source_file(path, working_directory),
        )

    def match_in(
        self, query: MatcherInput, target: MatchTarget, *,
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (),
        traversal_mode: int = match_service_pb2.MATCH_TRAVERSAL_MODE_AS_IS,
        on_row: MatchRowCallback | None = None,
        scope: ResourceScope[Client] | str | None = None,
    ) -> MatchValue[Client]:
        callback: AsyncMatchRowCallback | None = None
        if on_row is not None:
            async def checked_callback(row: match_result_pb2.MatchResult) -> None:
                await _invoke_sync_callback(on_row, row)

            callback = checked_callback

        request = _value_request(self, query, target,
            working_directory=working_directory, compile_arguments=compile_arguments,
            traversal_mode=traversal_mode, scope=scope)
        source_id = target._owner.session_id if isinstance(
            target, (ParsedTree, MatchValue, BindingSelection)
        ) else None
        completion, store = self._cursor_call(
            "_stream_cursor_match", request, on_row=callback,
            source_session_id=source_id,
        )
        return MatchValue[Client]._from_store(
            store, self._own_value(completion),
            source_file=_absolute_source_file(target, working_directory),
        )

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
        for scope_id, scope in tuple(self._resource_scopes.items()):
            try:
                scope.release()
            except Exception as error:
                errors.append(error)
            else:
                self._resource_scopes.pop(scope_id, None)
        for lease_id in tuple(self._file_leases):
            try:
                self.close_file(lease_id)
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

    def __exit__(self, exc_type: object, exc: BaseException | None, tb: object) -> None:
        try:
            self.close()
        except BaseException as cleanup:
            _preserve_cleanup_error(exc, cleanup, "client")

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

    def _cursor_call_keep_resource(self, method: str, *args: Any, **kwargs: Any) -> Any:
        """Call once while transferring a newly returned lease/scope to this facade."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            raise RuntimeError("synchronous cursor methods cannot run inside an active event loop")
        config = self._configuration()

        async def run() -> Any:
            async with AsyncClient(self.address, config=config,
                                   compilation_database=self.compilation_database) as client:
                result = await getattr(client, method)(*args, **kwargs)
                if isinstance(result, FileHandle):
                    client._file_leases.discard(result.lease_id)
                elif isinstance(result, ResourceScope):
                    client._resource_scopes.pop(result.resource_scope_id, None)
                return result
        return asyncio.run(run())

    def match_file(self, path: str | Path, query: MatcherInput, **kwargs: Any) -> match_service_pb2.MatchResponse:
        return self._cursor_call("match_file", path, query, **kwargs)

    def continue_match(self, session_id: str, bind: str, query: MatcherInput, **kwargs: Any) -> match_service_pb2.MatchResponse:
        return self._cursor_call("continue_match", session_id, bind, query, **kwargs)

    def restart_match(self, session_id: str, query: MatcherInput, **kwargs: Any) -> match_service_pb2.MatchResponse:
        return self._cursor_call("restart_match", session_id, query, **kwargs)

    def close_match(self, session_id: str) -> None:
        self._cursor_call("close_match", session_id)
        reference = self._values.pop(session_id, None)
        owner = reference() if reference else None
        if owner is not None:
            owner.closed = True

    def discover_files(self, paths: Sequence[str | Path] = (), **kwargs: Any) -> FileSet:
        return self._cursor_call("discover_files", paths, **kwargs)

    def open_file(self, value: str | Path | InputDescriptor, **kwargs: Any) -> FileHandle[Client]:
        handle = self._cursor_call_keep_resource("open_file", value, **kwargs)
        result = FileHandle(handle.lease_id, handle.input, self,
                            handle.source_revision, handle.snapshot_id, handle.state)
        if kwargs.get("scope") is None:
            self._file_leases.add(result.lease_id)
        return result

    def list_files(self) -> tuple[Any, ...]:
        return self._cursor_call("list_files")

    def file_info(self, handle: FileHandle[Client] | ParsedTree[Client]) -> Any:
        return self._cursor_call("file_info", handle)

    def close_file(self, handle: FileHandle[Client] | ParsedTree[Client] | str) -> Any:
        response = self._cursor_call("close_file", handle)
        if isinstance(handle, FileHandle | str):
            self._file_leases.discard(handle.lease_id if isinstance(handle, FileHandle) else handle)
        return response

    def close_all_files(self) -> Any:
        response = self._cursor_call("close_all_files")
        self._file_leases.clear()
        return response

    def refresh_file(self, handle: FileHandle[Client] | ParsedTree[Client], **kwargs: Any) -> FileHandle[Client]:
        updated = self._cursor_call_keep_resource("refresh_file", handle, **kwargs)
        if kwargs.get("scope") is None:
            self._file_leases.add(updated.lease_id)
        return FileHandle(updated.lease_id, updated.input, self,
                          updated.source_revision, updated.snapshot_id, updated.state)

    def open_resource_scope(self, **kwargs: Any) -> ResourceScope[Client]:
        scope = self._cursor_call_keep_resource("open_resource_scope", **kwargs)
        scope._client = self
        self._resource_scopes[scope.resource_scope_id] = scope
        return scope

    def describe_resource_scope(self, scope: ResourceScope[Client] | str) -> Any:
        return self._cursor_call("describe_resource_scope", scope)

    def cancel_resource_scope(self, scope: ResourceScope[Client] | str) -> Any:
        return self._cursor_call("cancel_resource_scope", scope)

    def release_resource_scope(self, scope: ResourceScope[Client] | str) -> Any:
        info = self._cursor_call("release_resource_scope", scope)
        if info.cleanup_acknowledged:
            self._resource_scopes.pop(_scope_id(scope), None)
        return info

    def resource_status(self) -> Any:
        return self._cursor_call("resource_status")

    def server_status(self) -> match_service_pb2.ServerStatusResponse:
        return self._cursor_call("server_status")

    def list_sessions(self) -> match_service_pb2.ListSessionsResponse:
        return self._cursor_call("list_sessions")

    def attach_session(self, session_id: str) -> ParsedTree[Client]:
        response = self._cursor_call("_session_info", session_id)
        return ParsedTree(response.file_path, self._own_value(response))

    def prune_caches(self, *, memory: bool = True, disk: bool = False
                     ) -> match_service_pb2.PruneCachesResponse:
        return self._cursor_call("prune_caches", memory=memory, disk=disk)

    def traverse(
        self,
        path: str | Path | FileHandle[Client] | InputDescriptor,
        **kwargs: Any,
    ) -> traverse_response_pb2.TraverseResponse:
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
            raise QueryError("interactive query session is unavailable; restart the console")
        if self._query_session._input_closed:
            raise QueryError("interactive query session is closed")

        async def send() -> Any:
            self._query_session.client.compilation_database = self.compilation_database
            if command == "start":
                return await self._query_session.start_query(value or "")
            elif command == "add":
                return await self._query_session.add_files(
                    [value or ""], working_directory=working_directory,
                    compile_arguments=compile_arguments,
                )
            elif command == "match":
                return await self._query_session.match()
            elif command == "pause":
                return await self._query_session.pause()
            elif command == "resume":
                return await self._query_session.resume()
            elif command == "close":
                return await self._query_session.half_close()
            raise QueryError(f"unsupported interactive query session command: {command}")

        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None
        if running_loop is self._async_loop:
            raise QueryError("interactive query session command cannot run on its event loop")
        if self._async_loop.is_closed() or not self._async_loop.is_running():
            raise QueryError("interactive query session is unavailable because its event loop has stopped")
        try:
            future = asyncio.run_coroutine_threadsafe(send(), self._async_loop)
            request_id = future.result()
            self._last_session_command = command
            self._last_session_command_request_id = request_id
        except QueryError:
            raise
        except Exception as exc:
            raise QueryError(f"interactive query session {command} failed: {exc}") from exc
        return f"session {command} command sent"

    def start_background_query(
        self,
        expression: MatcherInput,
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
        self, matcher: MatcherInput, *, file: str | Path,
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (),
    ) -> MatchValue[Client]: ...

    @overload
    def match(
        self, matcher: MatcherInput, *, files: Sequence[str | Path] | None = None,
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (), file: None = None,
    ) -> list[str]: ...

    def match(
        self, matcher: MatcherInput, *, files: Sequence[str | Path] | None = None,
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

    def cfg(
            self, function: str, *,
            path: str | Path | FileHandle[Client] | InputDescriptor | None = None,
            **kwargs: Any) -> cfg_response_pb2.CfgResponse:
        if path is None:
            raise ValueError("CFG requires a file path; pass path=...")
        return self._cursor_call("cfg", path, function, **kwargs)

    def run_script(
                   self, source: str, *,
                   path: str | Path | FileHandle[Client] | InputDescriptor | None = None,
                   working_directory: str | Path | None = None,
                   compile_arguments: Sequence[str] = (),
                   max_steps: int | None = None,
                   profile: InputDescriptor | None = None,
                   scope: ResourceScope[Client] | str | None = None) -> script_response_pb2.ScriptResponse:
        return self._cursor_call("run_script", source, path=path,
            working_directory=working_directory, compile_arguments=compile_arguments,
            max_steps=max_steps, profile=profile, scope=scope)

    def start_batch(
        self,
        inputs: FileSet | Sequence[InputDescriptor],
        body_source: str,
        **kwargs: Any,
    ) -> BatchRun:
        """Start an idempotent server-owned durable batch."""
        return self._cursor_call("start_batch", inputs, body_source, **kwargs)

    def batch_status(self, run: BatchRun | str) -> BatchRun:
        return self._cursor_call("batch_status", run)

    def cancel_batch(
        self, run: BatchRun | str, *, expected_revision: int | None = None
    ) -> BatchRun:
        return self._cursor_call(
            "cancel_batch", run, expected_revision=expected_revision
        )

    def resume_batch(
        self, run: BatchRun | str, *, expected_revision: int | None = None
    ) -> BatchRun:
        return self._cursor_call(
            "resume_batch", run, expected_revision=expected_revision
        )

    def retry_batch(
        self, run: BatchRun | str, *, expected_revision: int | None = None
    ) -> BatchRun:
        return self._cursor_call(
            "retry_batch", run, expected_revision=expected_revision
        )

    def callgraph(
                  self,
                  path: str | Path | FileHandle[Client] | InputDescriptor | None = None,
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

    def __init__(self, client: AsyncClient, lease: OperationLease,
                 scope: ResourceScope[AsyncClient] | str | None = None) -> None:
        self.client = client
        self.lease = lease
        self.scope = scope
        self._cancelled = False
        self._futures: set[concurrent.futures.Future[Any]] = set()
        self._future_lock = Lock()
        self._row_callbacks: set[asyncio.Task[Any]] = set()

    def cancel(self) -> None:
        with self._future_lock:
            self._cancelled = True
            futures = tuple(self._futures)
        for future in futures:
            future.cancel()

    async def wait_callbacks(self) -> None:
        """Join cancelled row callbacks before releasing runtime scopes."""
        if self._row_callbacks:
            await asyncio.gather(*tuple(self._row_callbacks), return_exceptions=True)

    def _call(self, method: str, *args: Any, **kwargs: Any) -> Any:
        with self._future_lock:
            if self._cancelled:
                raise asyncio.CancelledError
            future = asyncio.run_coroutine_threadsafe(
                getattr(self.client, method)(*args, **kwargs), self.client._loop)
            self._futures.add(future)
        try:
            return future.result()
        finally:
            with self._future_lock:
                self._futures.discard(future)

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
            lease=self.lease, scope=self.scope)

    def match_in(self, query: MatcherInput, target: MatchTarget, *,
                 working_directory: str | Path | None = None,
                 compile_arguments: Sequence[str] = (),
                 traversal_mode: match_service_pb2.MatchTraversalMode = match_service_pb2.MATCH_TRAVERSAL_MODE_AS_IS,
                 on_row: MatchRowCallback | None = None,
                 ) -> MatchValue[AsyncClient]:
        async def callback(row: match_result_pb2.MatchResult) -> None:
            assert on_row is not None
            task = asyncio.current_task()
            assert task is not None
            self._row_callbacks.add(task)
            try:
                await _invoke_sync_callback(on_row, row)
            finally:
                self._row_callbacks.discard(task)

        return self._call("_match_in_with_lease", query, target,
            working_directory=working_directory, compile_arguments=compile_arguments,
            traversal_mode=traversal_mode, on_row=callback if on_row is not None else None,
            lease=self.lease, scope=self.scope)

    def match(self, query: MatcherInput, *, files: Sequence[str] | None = None,
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
    client: Client | AsyncClient, query: MatcherInput, target: MatchTarget | Path, *,
    working_directory: str | Path | None = None,
    compile_arguments: Sequence[str] = (),
    traversal_mode: int = match_service_pb2.MATCH_TRAVERSAL_MODE_AS_IS,
    scope: ResourceScope[Any] | str | None = None,
) -> match_service_pb2.MatchRequest:
    if isinstance(target, str | Path | InputDescriptor):
        target_path = target.path if isinstance(target, InputDescriptor) else target
        request = file_request(target_path, query, working_directory=working_directory,
                            compile_arguments=compile_arguments,
                            traversal_mode=traversal_mode)
        if isinstance(target, InputDescriptor):
            request.file.expected_profile_id = target.profile_id
            request.file.working_directory = target.working_directory or request.file.working_directory
            request.file.compile_arguments[:] = target.compile_arguments
            request.file.compilation_database = target.compilation_database
            request.file.frozen_profile = target.frozen_profile
    elif isinstance(target, FileHandle):
        if target._client is not client:
            raise MatchValueError("file handle belongs to a different client")
        request = match_service_pb2.MatchRequest(
            query=matcher_query(query), traversal_mode=traversal_mode,
            file_handle=resources_pb2.FileHandleTarget(lease_id=target.lease_id),
        )
    elif isinstance(target, ParsedTree | MatchValue | BindingSelection):
        target._owner.check(client)
        options: dict[str, Any] = {}
        if isinstance(target, BindingSelection):
            options.update(bind=target.name, match_index=target._index, scope=target.scope)
        request = retained_request(target._owner.session_id, query,
            expected_result_revision=target._owner.revision,
            traversal_mode=traversal_mode, **options)
        request.preserve_source = True
    else:
        raise TypeError("match target must be a path, descriptor, file handle, parsed tree or binding selection")
    request.resource_scope_id = _scope_id(scope)
    return request


def _absolute_source_file(
    target: MatchTarget | str | Path, working_directory: str | Path | None = None,
) -> str | None:
    if isinstance(target, str | Path):
        source = target
    elif isinstance(target, InputDescriptor):
        source = target.path
    elif isinstance(target, FileHandle):
        source = target.path
    elif isinstance(target, ParsedTree):
        source = target.source_file or target.path
    else:
        source = target.source_file
    if source is None:
        return None
    path = Path(source).expanduser()
    if not path.is_absolute():
        base = Path(working_directory).expanduser() if working_directory is not None else Path.cwd()
        path = base / path
    return str(path.resolve())


def _scope_id(scope: ResourceScope[Any] | str | None) -> str:
    return scope.resource_scope_id if isinstance(scope, ResourceScope) else (scope or "")


def _file_handle(client: Any, info: Any) -> FileHandle[Any]:
    if not info.lease_id or not info.HasField("input"):
        raise CursorError(grpc.StatusCode.DATA_LOSS, "file lease reply is missing its identity")
    return FileHandle(
        info.lease_id,
        InputDescriptor.from_proto(info.input),
        client,
        info.source_revision,
        info.snapshot_id,
        info.state,
    )


def _analysis_input(
    value: str | Path | FileHandle[Any] | InputDescriptor,
) -> tuple[str | Path, InputDescriptor | None]:
    if isinstance(value, FileHandle):
        return value.path, value.input
    if isinstance(value, InputDescriptor):
        return value.path, value
    return value, None


def _apply_input_descriptor(target: Any, descriptor: InputDescriptor | None) -> None:
    if descriptor is None:
        return
    target.expected_profile_id = descriptor.profile_id
    target.compile_arguments[:] = descriptor.compile_arguments
    target.working_directory = descriptor.working_directory
    target.compilation_database = descriptor.compilation_database
    target.frozen_profile = descriptor.frozen_profile


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
