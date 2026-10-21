from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock

import pytest

from clang_toolkit import AsyncClient, Client
from clang_toolkit._generated.index.v1 import index_service_pb2 as pb


def test_async_index_controls_build_ui_contract_requests():
    async def exercise():
        client = AsyncClient("unix:///tmp/not-connected-index-test.sock")
        client._index_call = AsyncMock(return_value=pb.ProjectIndexStatus())
        await client.list_project_indexes()
        method, request = client._index_call.call_args.args
        assert method == "ListProjectIndexes"
        assert isinstance(request, pb.ListProjectIndexesRequest)
        await client.start_project_index("/remote/project", compile_commands="/remote/build", poll_interval_seconds=3)
        method, request = client._index_call.call_args.args
        assert method == "StartProjectIndex"
        assert request.project_root == "/remote/project"
        assert request.compile_commands == "/remote/build"
        assert request.poll_interval_seconds == 3
        for name, rpc in [
            ("project_index_status", "GetProjectIndexStatus"),
            ("pause_project_index", "PauseProjectIndex"),
            ("resume_project_index", "ResumeProjectIndex"),
            ("cancel_project_index", "CancelProjectIndex"),
        ]:
            await getattr(client, name)("/remote/project")
            method, request = client._index_call.call_args.args
            assert method == rpc and request.project_root == "/remote/project"
        await client.find_symbols("/remote/project", "demo::Wid", prefix=True, limit=5)
        method, request = client._index_call.call_args.args
        assert method == "FindSymbols"
        assert request.match_mode == pb.FindSymbolsRequest.MATCH_MODE_PREFIX
        assert request.query == "demo::Wid" and request.limit == 5
        await client.lookup_symbol("/remote/project", "c:@S@Widget")
        assert client._index_call.call_args.args[0] == "LookupSymbol"
        assert client._index_call.call_args.args[1].usr == "c:@S@Widget"
        for limit in (0, -1, 1001):
            with pytest.raises(ValueError, match="limit"):
                await client.find_symbols("/remote/project", "Widget", limit=limit)
        with pytest.raises(ValueError, match="poll_interval"):
            await client.start_project_index("/remote/project", poll_interval_seconds=0)
        await client.aclose()

    asyncio.run(exercise())


def test_sync_index_controls_use_existing_client_loop(monkeypatch):
    client = Client("unix:///tmp/not-connected-index-test.sock")
    calls = []
    expected = pb.ProjectIndexStatus(state=pb.INDEX_STATE_PAUSED)

    def call(name, *args, **kwargs):
        calls.append((name, args, kwargs))
        return expected

    monkeypatch.setattr(client, "_cursor_call", call)
    assert client.pause_project_index("/project") is expected
    assert calls == [("pause_project_index", ("/project",), {})]
    assert client.list_project_indexes() is expected
    assert calls[-1] == ("list_project_indexes", (), {})
    client.close()


@pytest.mark.parametrize("kind, expected", [("", pb.FindSymbolsRequest.KIND_ANY),
    ("function", pb.FindSymbolsRequest.KIND_FUNCTION),
    ("class", pb.FindSymbolsRequest.KIND_CLASS),
    ("variable", pb.FindSymbolsRequest.KIND_VARIABLE), ("alias", pb.FindSymbolsRequest.KIND_ALIAS)])
def test_optional_kind_filter_is_sent_before_server_limit(kind, expected):
    async def exercise():
        client = AsyncClient("unix:///tmp/not-connected-index-test.sock")
        client._index_call = AsyncMock(return_value=pb.FindSymbolsResponse())
        try:
            await client.find_symbols("/project", "demo", kind=kind, prefix=True, limit=1, unique_symbols=True)
            request = client._index_call.call_args.args[1]
            assert request.kind == expected and request.limit == 1 and request.unique_symbols
        finally:
            await client.aclose()
    asyncio.run(exercise())


def test_unknown_kind_fails_before_rpc():
    async def exercise():
        client = AsyncClient("unix:///tmp/not-connected-index-test.sock")
        client._index_call = AsyncMock()
        try:
            with pytest.raises(ValueError, match="kind"):
                await client.find_symbols("/project", "name", kind="unknown")
            client._index_call.assert_not_called()
        finally:
            await client.aclose()
    asyncio.run(exercise())


def test_source_only_symbol_search_forwards_paging_contract():
    async def exercise():
        client = AsyncClient("unix:///tmp/not-connected-index-test.sock")
        client._index_call = AsyncMock(return_value=pb.FindSymbolsResponse())
        try:
            await client.find_symbols("/project", "", prefix=True, kind="alias",
                                      source_only=True, offset=17, expected_revision=42)
            request = client._index_call.call_args.args[1]
            assert request.query == "" and request.source_only
            assert request.offset == 17 and request.expected_revision == 42
        finally:
            await client.aclose()
    asyncio.run(exercise())


def test_sync_client_forwards_source_only_paging_options(monkeypatch):
    client = Client("unix:///tmp/not-connected-index-test.sock")
    calls = []
    monkeypatch.setattr(client, "_cursor_call", lambda *args, **kwargs: calls.append((args, kwargs)))
    client.find_symbols("/project", "", prefix=True, kind="alias", source_only=True,
                        offset=9, expected_revision=12)
    assert calls == [(("find_symbols", "/project", ""), {
        "limit": 100, "prefix": True, "kind": "alias", "unique_symbols": False,
        "source_only": True, "offset": 9, "expected_revision": 12,
    })]
    client.close()


@pytest.mark.parametrize("name,value", [("offset", -1), ("expected_revision", -1)])
def test_source_only_symbol_search_rejects_negative_paging_values(name, value):
    async def exercise():
        client = AsyncClient("unix:///tmp/not-connected-index-test.sock")
        client._index_call = AsyncMock()
        try:
            with pytest.raises(ValueError, match=name):
                await client.find_symbols("/project", "name", **{name: value})
            client._index_call.assert_not_called()
        finally:
            await client.aclose()
    asyncio.run(exercise())


def test_optional_project_name_presence_and_rename_contract():
    async def exercise():
        client = AsyncClient("unix:///tmp/not-connected-index-test.sock")
        client._index_call = AsyncMock(return_value=pb.ProjectIndexStatus())
        try:
            await client.start_project_index("/project")
            assert not client._index_call.call_args.args[1].HasField("project_name")
            await client.start_project_index("/project", project_name="My library")
            assert client._index_call.call_args.args[1].project_name == "My library"
            await client.start_project_index("/project", project_name="")
            assert client._index_call.call_args.args[1].HasField("project_name")
            await client.rename_project_index("/project", "New library")
            method, request = client._index_call.call_args.args
            assert method == "RenameProjectIndex"
            assert request.project_root == "/project" and request.project_name == "New library"
        finally:
            await client.aclose()
    asyncio.run(exercise())


def test_sync_project_naming_uses_client_loop(monkeypatch):
    client = Client("unix:///tmp/not-connected-index-test.sock")
    calls = []
    monkeypatch.setattr(client, "_cursor_call", lambda *args, **kwargs: calls.append((args, kwargs)))
    try:
        client.start_project_index("/project", project_name="Library")
        assert calls[-1][1]["project_name"] == "Library"
        client.rename_project_index("/project", "Renamed")
        assert calls[-1] == (("rename_project_index", "/project", "Renamed"), {})
    finally:
        client.close()
