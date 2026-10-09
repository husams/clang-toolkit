from unittest.mock import Mock

import pytest

from clang_toolkit._generated.match.v1 import match_service_pb2 as pb
from clang_toolkit.cli.completion import ReplCompleter
from clang_toolkit.cli.runtime import EvaluationError, Runtime
from clang_toolkit.client import Client
from prompt_toolkit.document import Document


def test_bindings_rename_and_drop_preserve_aliases(tmp_path):
    runtime = Runtime(Mock(spec=Client), cwd=tmp_path, environment={})
    try:
        runtime.execute("let x = [1, 2]")
        runtime.execute("let alias = $x")
        runtime.execute("binding rename $x to $renamed")
        assert runtime.bindings["renamed"] is runtime.bindings["alias"]
        assert '"name": "renamed"' in runtime.execute("bindings list")
        with pytest.raises(EvaluationError, match="already exists"):
            runtime.execute("binding rename $renamed to $alias")
        with pytest.raises(EvaluationError, match="simple"):
            runtime.execute("binding drop $renamed[0]")
        runtime.execute("binding drop $renamed")
        assert runtime.bindings == {"alias": [1, 2]}
    finally:
        runtime.close()


def test_server_and_cache_commands_and_attach_are_routed(tmp_path):
    client = Mock(spec=Client)
    client.server_status.return_value = pb.ServerStatusResponse(active_sessions=2)
    client.list_sessions.return_value = pb.ListSessionsResponse()
    client.prune_caches.return_value = pb.PruneCachesResponse()
    runtime = Runtime(client, cwd=tmp_path, environment={})
    try:
        assert '"active_sessions": "2"' in runtime.execute("server status")
        assert '"storage_available": false' in runtime.execute("cache status")
        assert '"sessions": []' in runtime.execute("session list")
        runtime.execute("cache prune")
        client.prune_caches.assert_called_with(memory=True, disk=False)
        runtime.execute("cache prune all")
        client.prune_caches.assert_called_with(memory=True, disk=True)
        with pytest.raises(EvaluationError, match="memory, disk or all"):
            runtime.execute("cache prune wrong")
        runtime.execute('let id = "00000000-0000-4000-8000-000000000001"')
        runtime.execute("session attach $id into $tree")
        assert runtime.bindings["tree"] is client.attach_session.return_value
        runtime.execute("session close $id")
        client.close_match.assert_called_with(runtime.bindings["id"])
        runtime.bindings["tree"] = "prior"
        client.attach_session.side_effect = ValueError("expired")
        with pytest.raises(ValueError, match="expired"):
            runtime.execute("session attach $id into $tree")
        assert runtime.bindings["tree"] == "prior"
    finally:
        runtime.close()


@pytest.mark.parametrize("prefix,expected", [
    ("server ", {"status"}), ("cache ", {"status", "prune"}),
    ("cache prune ", {"memory", "disk", "all"}),
    ("binding ", {"drop", "rename"}),
    ('save $x to "data" as ', {"json", "yaml", "csv", "proto"}),
    ('print "hello" to "log.txt" mode ', {"replace", "append"}),
])
def test_management_completion(prefix, expected):
    completions = ReplCompleter().get_completions(Document(prefix), None)
    assert expected.issubset({item.text for item in completions})


def test_duplicate_attach_owners_reuse_and_stale_finalizers_do_not_close_latest():
    import gc
    client = Client()
    client._release_value = Mock()
    first = client._own_value(pb.SessionInfo(session_id="id", result_revision=1))
    assert client._own_value(pb.SessionInfo(session_id="id", result_revision=1)) is first
    latest = client._own_value(pb.SessionInfo(session_id="id", result_revision=2))
    del first
    gc.collect()
    client._release_value.assert_not_called()
    latest.close()
    client._release_value.assert_called_once_with("id")
