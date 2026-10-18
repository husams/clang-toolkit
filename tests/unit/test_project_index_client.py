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
