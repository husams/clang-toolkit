from unittest.mock import Mock

import pytest

from clang_toolkit._generated.match.v1 import match_service_pb2 as pb
from clang_toolkit.cli.completion import ReplCompleter
from clang_toolkit.cli.runtime import EvaluationError, Runtime
from clang_toolkit.cli.runtime.management import _bytes, _cache_rows, _render_status
from clang_toolkit.client import Client
from prompt_toolkit.document import Document


def test_bindings_rename_and_drop_preserve_aliases(tmp_path):
    runtime = Runtime(Mock(spec=Client), cwd=tmp_path, environment={})
    try:
        runtime.execute("let x = [1, 2]")
        runtime.execute("let alias = $x")
        runtime.execute("binding rename $x to $renamed")
        assert runtime.bindings["renamed"] is runtime.bindings["alias"]
        assert any(line.startswith("$renamed ") and line.endswith("list")
                   for line in runtime.execute("bindings list").splitlines())
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
    client.server_status.return_value = pb.ServerStatusResponse(
        uptime_ms=3723000, active_sessions=2, retained_memory_bytes=2048,
        max_sessions=10, max_retained_memory_bytes=10240,
        cache=pb.CacheResources(memory_available=True, reusable_snapshots=3,
                                reusable_memory_bytes=4096, storage_available=False))
    first_session = pb.SessionInfo(session_id="00000000-0000-4000-8000-000000000001",
                                   result_revision=4, file_path="/tmp/example.cc", row_count=12,
                                   binding_names=["root", "function"])
    first_session.expires_at.FromJsonString("2026-10-09T12:00:00Z")
    second_session = pb.SessionInfo(session_id="00000000-0000-4000-8000-000000000002",
                                    result_revision=1, file_path="/tmp/other.cc", row_count=2,
                                    binding_names=["other"])
    second_session.expires_at.FromJsonString("1970-01-01T00:00:00Z")
    client.list_sessions.return_value = pb.ListSessionsResponse(sessions=[first_session, second_session])
    client.prune_caches.return_value = pb.PruneCachesResponse()
    runtime = Runtime(client, cwd=tmp_path, environment={})
    try:
        status = runtime.execute("server status")
        assert any(line.startswith("Active sessions ") and line.endswith("2") for line in status.splitlines())
        assert any(line.startswith("Uptime ") and line.endswith("1:02:03") for line in status.splitlines())
        assert any(line.startswith("Retained memory ") and line.endswith("2.00 KiB") for line in status.splitlines())
        assert any(line.startswith("Storage ") and line.endswith("Unavailable") for line in status.splitlines())
        assert any(line.startswith("Resident memory ") and line.endswith("Unavailable") for line in status.splitlines())
        cache = runtime.execute("cache status")
        assert any(line.startswith("Reusable snapshots ") and line.endswith("3") for line in cache.splitlines())
        assert any(line.startswith("Artifact disk ") and line.endswith("Unavailable") for line in cache.splitlines())
        sessions = runtime.execute("session list")
        assert "00000000-0000-4000-8000-000000000001" in sessions
        assert "/tmp/example.cc" in sessions
        assert "00000000-0000-4000-8000-000000000002" in sessions
        assert "/tmp/other.cc" in sessions
        assert "1970-01-01T00:00:00Z" in sessions
        assert "Session 1" in sessions and "Session 2" in sessions
        assert "Revision" in sessions and "4" in sessions and "1" in sessions
        assert "Rows" in sessions and "12" in sessions and "2" in sessions
        assert "root, function" in sessions
        assert "2026-10-09T12:00:00Z" in sessions
        runtime.execute("cache prune")
        client.prune_caches.assert_called_with(memory=True, disk=False)
        runtime.execute("cache prune all")
        client.prune_caches.assert_called_with(memory=True, disk=True)
        assert "Cache prune results" in runtime.execute("cache prune all")
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


@pytest.mark.parametrize(("raw", "expected"), [
    (0, "0.00 KiB"),
    (1, "0.00 KiB"),
    (1024 * 1024 - 1, "1024.00 KiB"),
    (1024 * 1024, "1.00 MiB"),
    (1024**3 - 1, "1024.00 MiB"),
    (1024**3, "1.00 GiB"),
    (1024**3 + 512 * 1024**2, "1.50 GiB"),
])
def test_byte_format_uses_binary_units_at_boundaries(raw, expected):
    assert _bytes(raw) == expected


def test_zero_rss_and_available_zero_cache_counters_are_preserved():
    status = pb.ServerStatusResponse(resident_memory_bytes=0,
                                     cache=pb.CacheResources(memory_available=True,
                                                             storage_available=True))
    rendered = _render_status(status)
    assert "Resident memory" in rendered and "0.00 KiB" in rendered
    rows = dict(_cache_rows(status.cache))
    assert rows["Reusable snapshots"] == "0"
    assert rows["Reusable memory"] == "0.00 KiB"
    assert rows["Pending builds"] == "0"
    assert rows["Artifact disk"] == "0.00 KiB"
    assert rows["Ready snapshots"] == "0"


def test_missing_rss_and_unavailable_cache_counters_are_explicit():
    status = pb.ServerStatusResponse(cache=pb.CacheResources())
    rendered = _render_status(status)
    assert "Resident memory" in rendered and "Unavailable" in rendered
    rows = dict(_cache_rows(status.cache))
    assert rows["Reusable snapshots"] == "Unavailable"
    assert rows["Reusable memory"] == "Unavailable"
    assert rows["Artifact disk"] == "Unavailable"


def test_management_empty_results_are_human_readable(tmp_path):
    client = Mock(spec=Client)
    client.list_sessions.return_value = pb.ListSessionsResponse()
    runtime = Runtime(client, cwd=tmp_path, environment={})
    try:
        assert runtime.execute("bindings list") == "No bindings."
        assert runtime.execute("session list") == "No active sessions."
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
