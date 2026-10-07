"""Compilation database selection survives every client request shape."""
from pathlib import Path

import pytest

from clang_toolkit.client import AsyncClient, Client
from clang_toolkit.cli.app import dispatch
from clang_toolkit.cli.runtime import Runtime
from clang_toolkit.cli.runtime.config import ConfigError, ConfigStore
from clang_toolkit._generated.match.v1 import parse_request_pb2, match_service_pb2
from clang_toolkit._generated.query.v1 import query_pb2
from clang_toolkit._generated.analysis.v1 import script_request_pb2, traverse_request_pb2


def test_database_selection_reaches_parse_match_query_traversal_and_script():
    client = AsyncClient(compilation_database="build/compile_commands.json")
    requests = [
        parse_request_pb2.ParseRequest(file_path="source.cc"),
        match_service_pb2.MatchRequest(file=match_service_pb2.FileMatchTarget(file_path="source.cc")),
        query_pb2.QueryRequest(files=[query_pb2.FileInput(path="source.cc")]),
        traverse_request_pb2.TraverseRequest(file=match_service_pb2.FileMatchTarget(file_path="source.cc")),
        script_request_pb2.ScriptRequest(),
    ]
    requests[-1].profile.working_directory = "/project"
    for request in requests:
        client._compilation_request(request)
        if hasattr(request, "compilation_database"):
            target = request
        elif hasattr(request, "file") and request.HasField("file"):
            target = request.file
        elif hasattr(request, "profile"):
            target = request.profile
        else:
            target = request.files[0]
        assert target.compilation_database == "build/compile_commands.json"
    explicit = parse_request_pb2.ParseRequest(compilation_database="other.json")
    assert client._compilation_request(explicit).compilation_database == "other.json"
    retained = match_service_pb2.MatchRequest(session=match_service_pb2.SessionMatchTarget(session_id="cursor"))
    client._compilation_request(retained)
    assert retained.WhichOneof("target") == "session"


def test_console_selection_is_persisted_and_clear_restores_auto(tmp_path: Path):
    client = Client()
    client._async_client = AsyncClient()
    store = ConfigStore(tmp_path, home=tmp_path / "home", system=tmp_path / "missing.yaml")
    runtime = Runtime(client, cwd=tmp_path, config_store=store)
    assert dispatch(client, 'set compile_commands "build"', runtime) == ""
    dispatch(client, 'print "selected"', runtime)
    assert client.compilation_database == "build"
    assert client._async_client.compilation_database == "build"
    assert "compile_commands: build" in (tmp_path / ".clang_tools.yaml").read_text()
    assert dispatch(client, "clear compile_commands", runtime) == ""
    dispatch(client, 'print "automatic"', runtime)
    assert client.compilation_database is None
    assert client._async_client.compilation_database is None


@pytest.mark.parametrize("value", [[], 3, ""])
def test_database_setting_rejects_invalid_paths(tmp_path: Path, value):
    store = ConfigStore(tmp_path, home=tmp_path / "home", system=tmp_path / "missing.yaml")
    with pytest.raises(ConfigError, match="compile_commands"):
        store.set("compile_commands", value)
