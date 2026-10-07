from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, Mock

import grpc
import pytest

from clang_toolkit.cli import app
from clang_toolkit.client import AsyncClient, QueryError
from clang_toolkit._generated.query.v1 import query_pb2
from clang_toolkit.version import client_version


def test_client_version_exits_without_config_or_connection(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["ctk", "--version", "-c", "/does/not/exist.yaml"])
    monkeypatch.setattr(app, "load_network_config", Mock(side_effect=AssertionError("configuration was read")))
    with pytest.raises(SystemExit) as exit:
        app.main()
    assert exit.value.code == 0
    assert capsys.readouterr().out.strip() == client_version().format("ctk")


def test_old_server_version_reports_update_instead_of_client_identity(monkeypatch):
    error = grpc.aio.AioRpcError(grpc.StatusCode.UNIMPLEMENTED, (), (), "unknown method")
    stub = Mock(GetVersion=AsyncMock(side_effect=error))
    monkeypatch.setattr(AsyncClient, "_ensure_stub", lambda _self: stub)
    client = AsyncClient(config=Mock(rpc_timeout=None))
    with pytest.raises(QueryError, match="update and restart"):
        asyncio.run(client.server_version())


def test_server_identity_comes_from_rpc_and_uses_a_bounded_timeout(monkeypatch):
    stub = Mock(GetVersion=AsyncMock(return_value=query_pb2.VersionResponse(version="2.3.4", revision="abcdef123456")))
    monkeypatch.setattr(AsyncClient, "_ensure_stub", lambda _self: stub)
    info = asyncio.run(AsyncClient(config=Mock(rpc_timeout=None)).server_version())
    assert info.format("ctk-server") == "ctk-server 2.3.4 (revision abcdef123456)"
    assert stub.GetVersion.call_args.kwargs["timeout"] > 0
