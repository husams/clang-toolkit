from __future__ import annotations

from unittest.mock import Mock

from clang_toolkit.client import Client
from clang_toolkit.cli.runtime import Runtime


def test_project_index_controls_route_project_and_preserve_values(tmp_path):
    from clang_toolkit._generated.index.v1 import index_service_pb2 as pb

    client = Mock(spec=Client)
    client.compilation_database = None
    status = pb.ProjectIndexStatus(project_root=str(tmp_path), state=pb.INDEX_STATE_PAUSED)
    client.start_project_index.return_value = status
    client.project_index_status.return_value = status
    client.pause_project_index.return_value = status
    client.resume_project_index.return_value = status
    client.cancel_project_index.return_value = status
    runtime = Runtime(client, cwd=tmp_path, environment={})
    try:
        runtime.execute('index start "."')
        client.start_project_index.assert_called_once_with(str(tmp_path))
        runtime.execute('index pause "."')
        client.pause_project_index.assert_called_once_with(str(tmp_path))
        runtime.execute('index resume "."')
        client.resume_project_index.assert_called_once_with(str(tmp_path))
        runtime.execute('index cancel "."')
        client.cancel_project_index.assert_called_once_with(str(tmp_path))
        output = runtime.execute('index status "."')
        assert "PAUSED" in output
        runtime.execute('let state = index status "."')
        assert runtime.evaluate('$state.project_root') == str(tmp_path)
    finally:
        runtime.close()


def test_project_symbol_lookup_routes_without_parsing(tmp_path):
    from clang_toolkit._generated.index.v1 import index_service_pb2 as pb

    client = Mock(spec=Client)
    client.compilation_database = None
    client.find_symbols.return_value = pb.FindSymbolsResponse(symbols=[
        pb.Symbol(usr="c:@F@leaf#", name="leaf", qualified_name="leaf",
                  file_path=str(tmp_path / "leaf.cc"), line=1, column=1),
    ])
    client.lookup_symbol.return_value = client.find_symbols.return_value
    runtime = Runtime(client, cwd=tmp_path, environment={})
    try:
        assert "leaf" in runtime.execute('index find "leaf" in "."')
        client.find_symbols.assert_called_once_with(str(tmp_path), "leaf")
        runtime.execute('index lookup "c:@F@leaf#" in "."')
        client.lookup_symbol.assert_called_once_with(str(tmp_path), "c:@F@leaf#")
        client.parse.assert_not_called()
    finally:
        runtime.close()
