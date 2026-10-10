from __future__ import annotations

import asyncio
from types import SimpleNamespace

import grpc
import pytest

from clang_toolkit.client import (
    AsyncClient,
    Client,
    _apply_input_descriptor,
    _value_request,
)
from clang_toolkit._generated.match.v1 import match_service_pb2, resources_pb2
from clang_toolkit._generated.match.v1 import parse_response_pb2
from clang_toolkit._generated.analysis.v1 import call_graph_response_pb2
from clang_toolkit._generated.analysis.v1 import script_response_pb2
from clang_toolkit.cursors import CursorError
from clang_toolkit.resources import (
    FileHandle,
    FileSet,
    InputDescriptor,
    ResourceError,
    ResourceScope,
    partition_inputs,
    require_complete,
)


def _files(count: int, *, profiles: tuple[str, ...] = ("debug",)) -> FileSet:
    return FileSet(
        tuple(
            InputDescriptor(f"/tmp/{index}.cpp", profiles[index % len(profiles)])
            for index in range(count)
        )
    )


def test_input_descriptors_freeze_profile_identity_and_options() -> None:
    options = ["-std=c++20"]
    first = InputDescriptor("/tmp/a.cpp", "profile-a", compile_arguments=options)
    second = InputDescriptor("/tmp/a.cpp", "profile-b", compile_arguments=options)
    options.append("-DCHANGED")

    assert first != second
    assert first.compile_arguments == ("-std=c++20",)
    assert first.path == second.path


def test_size_partition_is_bounded_and_preserves_frozen_input_order() -> None:
    files = _files(5, profiles=("debug", "release"))

    batches = list(partition_inputs(files, size=2))

    assert [batch.index for batch in batches] == [1, 2, 3]
    assert [batch.length for batch in batches] == [2, 2, 1]
    assert [item for batch in batches for item in batch.inputs] == list(files.inputs)
    assert all(batch.length <= 2 for batch in batches)
    assert batches[0].inputs[0].profile_id == "debug"
    assert batches[0].inputs[1].profile_id == "release"


def test_count_partition_balances_groups_without_losing_profiles() -> None:
    files = _files(8, profiles=("a", "b"))

    batches = list(partition_inputs(files, count=3))

    assert [batch.length for batch in batches] == [3, 3, 2]
    assert [batch.index for batch in batches] == [1, 2, 3]
    assert [item.profile_id for batch in batches for item in batch.inputs] == [
        item.profile_id for item in files.inputs
    ]


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({}, "exactly one"),
        ({"size": 2, "count": 1}, "exactly one"),
        ({"size": 0}, "positive"),
        ({"count": True}, "positive"),
    ],
)
def test_partition_rejects_invalid_bounds(
    kwargs: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        list(partition_inputs(_files(3), **kwargs))  # type: ignore[arg-type]


def test_count_cannot_exceed_nonempty_manifest_and_empty_manifest_is_noop() -> None:
    with pytest.raises(ValueError, match="cannot exceed"):
        list(partition_inputs(_files(2), count=3))
    assert list(partition_inputs(_files(0), count=4)) == []
    assert list(partition_inputs(_files(0), size=2)) == []


def test_discovery_is_metadata_only_and_preserves_profile_fields() -> None:
    client = AsyncClient()
    requests = []

    async def resource_call(method, request):
        requests.append((method, request))
        return resources_pb2.DiscoverFilesResponse(
            inputs=[
                InputDescriptor(
                    "/src/a.cpp",
                    "profile-7",
                    "/src",
                    ("-std=c++20",),
                    "/src/compile_commands.json",
                    120,
                    4096,
                    True,
                ).to_proto()
            ],
            diagnostics=["one input expanded"],
            metadata_bytes=256,
        )

    client._resource_call = resource_call  # type: ignore[method-assign]
    result = asyncio.run(client.discover_files(["src/"]))

    method, request = requests[0]
    assert method == "DiscoverFiles"
    assert list(request.paths) == ["src/"]
    assert len(result) == 1
    assert result.inputs[0].profile_id == "profile-7"
    assert result.inputs[0].estimated_parse_bytes == 4096
    assert result.inputs[0].frozen_profile
    assert result.diagnostics == ("one input expanded",)
    assert result.metadata_bytes == 256


def test_open_scope_and_file_handle_targets_are_typed_and_scoped() -> None:
    client = AsyncClient()
    calls: list[tuple[str, object]] = []
    descriptor = InputDescriptor("/src/a.cpp", "p1", "/src", frozen_profile=True)

    async def resource_call(method, request):
        calls.append((method, request))
        if method == "OpenFile":
            return resources_pb2.FileInfo(
                lease_id="lease-1",
                input=descriptor.to_proto(),
                source_revision="r1",
                snapshot_id="snapshot-1",
                state=resources_pb2.FILE_STATE_OPEN,
            )
        if method == "OpenResourceScope":
            return resources_pb2.ResourceScopeInfo(
                resource_scope_id="scope-1",
                state=resources_pb2.RESOURCE_SCOPE_STATE_OPEN,
                admitted_inputs=len(request.inputs),
            )
        return resources_pb2.ResourceScopeInfo(
            resource_scope_id=request.resource_scope_id,
            state=resources_pb2.RESOURCE_SCOPE_STATE_RELEASED,
            cleanup_acknowledged=True,
        )

    client._resource_call = resource_call  # type: ignore[method-assign]

    async def run() -> tuple[ResourceScope[AsyncClient], object]:
        scope_value = await client.open_resource_scope(
            inputs=(descriptor,), memory_bytes=1024, jobs=2
        )
        handle_value = await client.open_file(descriptor, scope=scope_value)
        await scope_value.arelease()
        return scope_value, handle_value

    scope, handle = asyncio.run(run())

    request = _value_request(client, "functionDecl()", handle, scope=scope)
    assert handle.lease_id == "lease-1"
    assert request.WhichOneof("target") == "file_handle"
    assert request.file_handle.lease_id == "lease-1"
    assert request.resource_scope_id == "scope-1"
    assert request.file_handle.lease_id != "scope-1"
    open_scope_request = calls[0][1]
    assert isinstance(open_scope_request, resources_pb2.OpenResourceScopeRequest)
    assert len(open_scope_request.inputs) == 1
    assert open_scope_request.memory_bytes == 1024
    assert open_scope_request.jobs == 2
    assert scope.cleanup_acknowledged


def test_closing_one_file_lease_does_not_close_an_independent_lease() -> None:
    client = AsyncClient()
    first = resources_pb2.FileInfo(
        lease_id="lease-a", input=InputDescriptor("/a.cpp", "p").to_proto()
    )
    second = resources_pb2.FileInfo(
        lease_id="lease-b", input=InputDescriptor("/a.cpp", "p").to_proto()
    )
    from clang_toolkit.client import _file_handle

    first_handle = _file_handle(client, first)
    second_handle = _file_handle(client, second)
    client._file_leases.update((first_handle.lease_id, second_handle.lease_id))
    closed_ids: list[str] = []

    async def resource_call(method, request):
        assert method == "CloseFile"
        closed_ids.append(request.lease_id)
        return resources_pb2.CloseFileResponse(released_leases=1)

    client._resource_call = resource_call  # type: ignore[method-assign]
    asyncio.run(client.close_file(first_handle))

    assert closed_ids == ["lease-a"]
    assert client._file_leases == {"lease-b"}


def test_scoped_file_leases_are_owned_by_the_scope_not_client_shutdown() -> None:
    client = AsyncClient()
    descriptor = InputDescriptor("/src/a.cpp", "p", "/src", frozen_profile=True)

    async def resource_call(method, _request):
        lease_id = "lease-open" if method == "OpenFile" else "lease-refresh"
        return resources_pb2.FileInfo(lease_id=lease_id, input=descriptor.to_proto())

    client._resource_call = resource_call  # type: ignore[method-assign]

    async def run():
        handle = await client.open_file(descriptor, scope="scope-1")
        refreshed = await client.refresh_file(handle, scope="scope-1")
        return handle, refreshed

    handle, refreshed = asyncio.run(run())

    assert handle.lease_id == "lease-open"
    assert refreshed.lease_id == "lease-refresh"
    assert client._file_leases == set()


def test_repeated_file_lease_close_treats_not_found_as_already_released() -> None:
    client = AsyncClient()
    client._file_leases.add("lease-closed")

    async def resource_call(method, request):
        assert method == "CloseFile"
        assert request.lease_id == "lease-closed"
        raise CursorError(grpc.StatusCode.NOT_FOUND, "lease not found")

    client._resource_call = resource_call  # type: ignore[method-assign]

    response = asyncio.run(client.close_file("lease-closed"))

    assert response == resources_pb2.CloseFileResponse()
    assert client._file_leases == set()


def test_context_cleanup_failure_does_not_mask_body_exception(monkeypatch) -> None:
    client = Client()

    def fail_cleanup():
        raise RuntimeError("cleanup failed")

    monkeypatch.setattr(client, "close", fail_cleanup)
    primary = ValueError("body failed")

    with pytest.raises(ValueError, match="body failed") as caught:
        with client:
            raise primary

    assert caught.value is primary
    assert any("client cleanup failed" in note for note in primary.__notes__)


def test_async_context_cleanup_failure_does_not_mask_body_exception(monkeypatch) -> None:
    client = AsyncClient()

    async def fail_cleanup():
        raise RuntimeError("cleanup failed")

    monkeypatch.setattr(client, "aclose", fail_cleanup)
    monkeypatch.setattr(client, "_ensure_stub", lambda: None)
    primary = ValueError("body failed")

    async def run():
        with pytest.raises(ValueError, match="body failed"):
            async with client:
                raise primary

    asyncio.run(run())

    assert any("async client cleanup failed" in note for note in primary.__notes__)


def test_resource_scope_context_cleanup_failure_does_not_mask_body_exception(
) -> None:
    class Owner:
        def release_resource_scope(self, _scope):
            raise RuntimeError("release failed")

    scope = ResourceScope(
        "scope-1", resources_pb2.ResourceScopeInfo(), Owner()
    )
    primary = ValueError("body failed")

    with pytest.raises(ValueError, match="body failed") as caught:
        with scope:
            raise primary

    assert caught.value is primary
    assert any("resource scope cleanup failed" in note for note in primary.__notes__)


def test_file_handle_context_cleanup_failure_does_not_mask_body_exception() -> None:
    class Owner:
        def close_file(self, _handle):
            raise RuntimeError("close failed")

    handle = FileHandle("lease-1", InputDescriptor("/a.cpp", "p"), Owner())
    primary = ValueError("body failed")

    with pytest.raises(ValueError, match="body failed") as caught:
        with handle:
            raise primary

    assert caught.value is primary
    assert any("file handle cleanup failed" in note for note in primary.__notes__)


def test_descriptor_match_target_sends_frozen_profile_and_scope_identity() -> None:
    descriptor = InputDescriptor(
        "/src/a.cpp",
        "profile-frozen",
        "/src",
        ("-std=c++23",),
        "/src/compile_commands.json",
        frozen_profile=True,
    )

    request = _value_request(
        AsyncClient(), "functionDecl()", descriptor, scope="scope-batch"
    )

    assert request.file.expected_profile_id == "profile-frozen"
    assert request.file.frozen_profile
    assert list(request.file.compile_arguments) == ["-std=c++23"]
    assert request.file.compilation_database == "/src/compile_commands.json"
    assert request.resource_scope_id == "scope-batch"

    client = AsyncClient(compilation_database="/client/local/compile_commands.json")
    prepared = client._compilation_request(request)
    assert prepared.file.compilation_database == "/src/compile_commands.json"


def test_graph_file_target_preserves_descriptor_profile_and_scope() -> None:
    descriptor = InputDescriptor(
        "/src/a.cpp",
        "profile-frozen",
        "/src",
        ("-std=c++23",),
        "/src/compile_commands.json",
        frozen_profile=True,
    )
    target = match_service_pb2.FileMatchTarget(file_path=descriptor.path)

    _apply_input_descriptor(target, descriptor)

    assert target.expected_profile_id == "profile-frozen"
    assert target.frozen_profile
    assert target.compile_arguments == ["-std=c++23"]


def test_parse_request_carries_scope_and_frozen_profile(monkeypatch) -> None:
    client = AsyncClient()
    captured = {}

    class Stub:
        def __init__(self, _channel):
            pass

        async def Parse(self, request, *, timeout=None):
            captured["request"] = request
            captured["timeout"] = timeout
            return parse_response_pb2.ParseResponse(
                session_id="tree-1", result_revision=1
            )

    monkeypatch.setattr(client, "_ensure_stub", lambda: None)
    client._channel = object()
    client.config = SimpleNamespace(rpc_timeout=5)
    monkeypatch.setattr(
        "clang_toolkit.client.match_service_pb2_grpc.MatchServiceStub", Stub
    )
    descriptor = InputDescriptor(
        "/remote/a.cpp",
        "profile-remote",
        "/remote",
        ("-std=c++20",),
        "/remote/compile_commands.json",
        frozen_profile=True,
    )

    response = asyncio.run(client._parse_response(descriptor, scope="scope-parse"))

    request = captured["request"]
    assert response.session_id == "tree-1"
    assert request.file_path == "/remote/a.cpp"
    assert request.expected_profile_id == "profile-remote"
    assert request.frozen_profile
    assert request.working_directory == "/remote"
    assert request.resource_scope_id == "scope-parse"


def test_async_script_file_handle_carries_frozen_profile_and_scope(monkeypatch) -> None:
    client = AsyncClient(compilation_database="/local/compile_commands.json")
    captured = {}

    class Stub:
        def __init__(self, _channel):
            pass

        async def RunScript(self, request, *, timeout=None):
            captured["request"] = request
            captured["timeout"] = timeout
            return script_response_pb2.ScriptResponse()

    monkeypatch.setattr(client, "_ensure_stub", lambda: None)
    client._channel = object()
    client.config = SimpleNamespace(rpc_timeout=5)
    monkeypatch.setattr(
        "clang_toolkit.client.analysis_service_pb2_grpc.AnalysisServiceStub", Stub
    )
    descriptor = InputDescriptor(
        "/remote/a.cpp",
        "profile-remote",
        "/remote",
        ("-std=c++20",),
        "/remote/compile_commands.json",
        frozen_profile=True,
    )
    handle = FileHandle("lease-1", descriptor, client)

    asyncio.run(client.run_script("emit parse(\"a.cpp\");", path=handle,
                                  scope="scope-script"))

    request = captured["request"]
    assert request.file.file_path == "/remote/a.cpp"
    assert request.file.expected_profile_id == "profile-remote"
    assert request.file.frozen_profile
    assert request.file.working_directory == "/remote"
    assert list(request.file.compile_arguments) == ["-std=c++20"]
    assert request.file.compilation_database == "/remote/compile_commands.json"
    assert request.profile.expected_profile_id == "profile-remote"
    assert request.profile.frozen
    assert request.resource_scope_id == "scope-script"


def test_script_default_profile_applies_without_default_file() -> None:
    from clang_toolkit.scripting import script_request

    descriptor = InputDescriptor(
        "/remote/a.cpp",
        "profile-remote",
        "/remote",
        ("-std=c++20",),
        "/remote/compile_commands.json",
        frozen_profile=True,
    )

    request = script_request("emit parse(\"a.cpp\");", profile=descriptor)

    assert not request.HasField("file")
    assert request.profile.expected_profile_id == "profile-remote"
    assert request.profile.frozen
    assert request.profile.working_directory == "/remote"
    assert list(request.profile.compile_arguments) == ["-std=c++20"]
    assert request.profile.compilation_database == "/remote/compile_commands.json"


def test_sync_script_path_accepts_frozen_descriptors_and_forwards_profile(monkeypatch) -> None:
    client = Client()
    descriptor = InputDescriptor("/remote/a.cpp", "profile", "/remote", frozen_profile=True)
    captured = {}

    def cursor_call(method, *args, **kwargs):
        captured.update(method=method, args=args, kwargs=kwargs)
        return script_response_pb2.ScriptResponse()

    monkeypatch.setattr(client, "_cursor_call", cursor_call)
    client.run_script("emit 1;", path=descriptor, scope="scope-sync")

    assert captured["method"] == "run_script"
    assert captured["kwargs"]["path"] is descriptor
    assert captured["kwargs"]["scope"] == "scope-sync"


def test_scope_cancel_and_failed_file_open_keep_acknowledgement_explicit() -> None:
    client = AsyncClient()
    calls: list[tuple[str, object]] = []

    async def resource_call(method, request):
        calls.append((method, request))
        if method == "CancelResourceScope":
            return resources_pb2.ResourceScopeInfo(
                resource_scope_id=request.resource_scope_id,
                state=resources_pb2.RESOURCE_SCOPE_STATE_CANCELLING,
                cleanup_acknowledged=False,
            )
        raise CursorError(9, "file admission rejected")

    client._resource_call = resource_call  # type: ignore[method-assign]
    scope = ResourceScope(
        "scope-cancel",
        resources_pb2.ResourceScopeInfo(resource_scope_id="scope-cancel"),
        client,
    )

    result = asyncio.run(scope.acancel())
    assert result.state == resources_pb2.RESOURCE_SCOPE_STATE_CANCELLING
    assert not scope.cleanup_acknowledged
    with pytest.raises(CursorError, match="file admission rejected"):
        asyncio.run(client.open_file("/src/rejected.cpp", scope=scope))
    assert [name for name, _ in calls] == ["CancelResourceScope", "OpenFile"]


def test_open_file_rejects_success_reply_without_a_lease_identity() -> None:
    client = AsyncClient()

    async def resource_call(_method, _request):
        return resources_pb2.FileInfo()

    client._resource_call = resource_call  # type: ignore[method-assign]

    with pytest.raises(CursorError, match="missing its identity"):
        asyncio.run(client.open_file("/src/a.cpp"))


def test_batch_result_completeness_check_rejects_partial_responses() -> None:
    response = match_service_pb2.ServerStatusResponse()
    assert require_complete(response) is response

    with pytest.raises(ResourceError, match="incomplete"):
        require_complete(call_graph_response_pb2.CallGraphResponse(is_complete=False))
