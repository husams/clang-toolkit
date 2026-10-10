"""Operational values compose without triggering their standalone display."""

from __future__ import annotations

import json
import asyncio
from unittest.mock import Mock

import pytest

from clang_toolkit._generated.match.v1 import match_service_pb2 as pb
from clang_toolkit._generated.match.v1 import resources_pb2 as resource_pb
from clang_toolkit.cli.runtime import Runtime
from clang_toolkit.client import AsyncClient, Client
from clang_toolkit.resources import FileHandle, InputDescriptor
from test_match_block import function_row
from test_match_stream import Stream, completed, patch_stream


@pytest.fixture
def expression_runtime(tmp_path):
    client = Mock(spec=Client)
    client.server_status.return_value = pb.ServerStatusResponse(active_sessions=7)
    client.server_status.return_value.cache.reusable_snapshots = 3
    runtime = Runtime(client, cwd=tmp_path, environment={})
    yield runtime, client
    runtime.close()


def test_status_command_values_compose_in_assignment_list_dict_and_group(expression_runtime, capsys):
    runtime, client = expression_runtime
    assert runtime.execute("let status = server status") == ""
    assert runtime.execute("let statuses = [server status, cache status]") == ""
    assert runtime.execute("let summary = {server: server status, cache: cache status}") == ""
    assert runtime.evaluate("(server status).active_sessions") == 7
    assert runtime.evaluate("$status.active_sessions") == 7
    assert runtime.evaluate("$statuses[1].reusable_snapshots") == 3
    assert runtime.evaluate("$summary.server.active_sessions") == 7
    assert capsys.readouterr().out == ""
    assert client.server_status.call_count == 6
    assert "Server status" in runtime.execute("server status")


@pytest.mark.parametrize("source,expected", [("42", 42), ("true", True), ("[1, 2]", [1, 2])])
def test_standalone_and_assigned_plain_values_share_the_evaluator(expression_runtime, source, expected):
    runtime, _ = expression_runtime
    assert runtime.evaluate(source) == expected
    assert runtime.execute(source)
    assert runtime.execute(f"let value = {source}") == ""
    assert runtime.bindings["value"] == expected


def test_assigned_foreach_block_collects_only_last_typed_value_and_is_silent(expression_runtime, capsys, tmp_path):
    runtime, _ = expression_runtime
    runtime.execute('set output to "display.txt"')
    runtime.execute("let values = foreach x in [1, 2] do { print $x; let ignored = 9; {item: $x}; }")
    assert runtime.bindings["values"] == [{"item": 1}, {"item": 2}]
    assert "x" not in runtime.bindings and "ignored" not in runtime.bindings
    assert capsys.readouterr().out == ""
    assert (tmp_path / "display.txt").read_text() == ""


def test_assignment_returns_operation_value_without_replaying_side_effects(expression_runtime):
    runtime, client = expression_runtime
    runtime.execute("let values = [1]")
    assert runtime.execute("let pushed = push values, 2") == ""
    assert runtime.bindings["values"] == [1, 2]
    runtime.execute("let printed = print server status")
    assert runtime.evaluate("$printed.active_sessions") == 7
    assert client.server_status.call_count == 1


def test_file_commands_return_handles_inventory_and_status_as_values(expression_runtime, tmp_path, capsys):
    runtime, client = expression_runtime
    handle = FileHandle("lease-1", InputDescriptor.from_path(tmp_path / "a.cc"), client)
    client.open_file.return_value = handle
    client.list_files.return_value = (handle,)
    client.file_info.return_value = {"lease_id": handle.lease_id}
    client.resource_status.return_value = resource_pb.ResourceStatusResponse(explicit_file_leases=1)
    client.close_file.return_value = {"closed": handle.lease_id}
    assert runtime.execute('let opened = file open "a.cc" into $source') == ""
    assert runtime.bindings["opened"] is runtime.bindings["source"] is handle
    runtime.execute("let inventory = file list")
    assert list(runtime.bindings["inventory"]) == [handle]
    runtime.execute("let details = {file: file info $opened, status: resource status}")
    assert runtime.evaluate("$details.file.lease_id") == "lease-1"
    assert runtime.evaluate("$details.status.explicit_file_leases") == 1
    runtime.execute("let closed = file close $opened")
    assert runtime.bindings["closed"] == {"closed": "lease-1"}
    client.open_file.assert_called_once()
    client.close_file.assert_called_once_with(handle)
    assert capsys.readouterr().out == ""


def test_assigned_file_operations_work_without_into_and_close_inventory(expression_runtime, tmp_path):
    runtime, client = expression_runtime
    descriptor = InputDescriptor.from_path(tmp_path / "a.cc")
    source = FileHandle("lease-1", descriptor, client)
    refreshed = FileHandle("lease-2", descriptor, client)
    active = [source]
    client.open_file.return_value = source

    def refresh(handle, **kwargs):
        assert handle is source
        active.append(refreshed)
        return refreshed

    def close(handle):
        active.remove(handle)
        return {"closed": handle.lease_id}

    client.refresh_file.side_effect = refresh
    client.close_file.side_effect = close
    client.list_files.side_effect = lambda: tuple(active)
    assert runtime.execute('let source = file open "a.cc"') == ""
    assert runtime.execute("let refreshed = file refresh $source") == ""
    assert runtime.bindings["source"] is source
    assert runtime.bindings["refreshed"] is refreshed
    assert list(runtime.evaluate("file list")) == [source, refreshed]
    runtime.evaluate("file close $source")
    runtime.evaluate("file close $refreshed")
    assert list(runtime.evaluate("file list")) == []
    client.open_file.assert_called_once()
    client.refresh_file.assert_called_once()
    assert client.close_file.call_count == 2


def test_load_without_into_and_save_direct_values_preserve_explicit_effects(expression_runtime, tmp_path):
    runtime, client = expression_runtime
    client.resource_status.return_value = resource_pb.ResourceStatusResponse(explicit_file_leases=1)
    runtime.execute('save [resource status] to "status.json" as json')
    assert json.loads((tmp_path / "status.json").read_text()) == [{"explicit_file_leases": 1}]
    runtime.execute('save [1, true] to "values.proto" as proto')
    assert runtime.execute('let loaded = load "values.proto"') == ""
    assert runtime.bindings["loaded"] == [1, True]
    runtime.execute('load "values.proto" into $legacy')
    assert runtime.bindings["legacy"] == runtime.bindings["loaded"]


def test_read_commands_produce_values_without_display(expression_runtime, capsys):
    runtime, _ = expression_runtime
    runtime.bindings["existing"] = 42
    runtime.execute("let instructions = help batch")
    assert "batch" in runtime.bindings["instructions"]
    runtime.execute("let shape = inspect $existing")
    assert runtime.bindings["shape"]
    inventory = runtime.evaluate("bindings list")
    assert inventory is not None
    assert "existing" in str(inventory)
    assert capsys.readouterr().out == ""


def test_cursor_read_commands_return_response_values_once(expression_runtime, capsys):
    runtime, client = expression_runtime
    client.match_file.return_value = pb.MatchResponse(session_id="cursor-1", result_revision=1)
    client.continue_match.return_value = pb.MatchResponse(session_id="cursor-1", result_revision=2)
    runtime.execute('let opened = cursor open "a.cc" functionDecl()')
    runtime.execute('let continued = cursor continue "cursor-1" "f" returnStmt()')
    assert runtime.evaluate("$opened.session_id") == "cursor-1"
    assert runtime.evaluate("$continued.result_revision") == 2
    client.match_file.assert_called_once()
    client.continue_match.assert_called_once()
    assert capsys.readouterr().out == ""


def test_direct_evaluate_foreach_blocks_return_values_and_execute_quit_remains_control(expression_runtime):
    runtime, _ = expression_runtime
    assert runtime.evaluate("foreach x in [1, 2] do { let item = $x; $item; }") == [1, 2]
    assert runtime.evaluate("foreach x in [1, 2] do {\n}") == [None, None]
    assert runtime.execute("foreach x in [1] do { quit; }") is None
    assert runtime.execute("quit") is None


@pytest.mark.parametrize("mode", ["assignment", "evaluate", "sync_sdk", "standalone"])
def test_match_do_capture_does_not_publish_automatic_output_in_value_context(monkeypatch, tmp_path, capsys, mode):
    stream = Stream([function_row(), function_row(1), completed("captured-rows", 2)])
    stub = patch_stream(monkeypatch, stream)
    source = ('match functionDecl().bind("func") in "a.cc" do { '
              'let name = $func.value.node.qualified_name; '
              'print $name to "explicit.txt" mode append; print $name; }')
    with Client("unix:///tmp/test.sock") as client:
        runtime = Runtime(client, cwd=tmp_path, environment={})
        client._expression_runtime = runtime
        runtime.execute('set output to "automatic.txt"')
        if mode == "assignment":
            assert runtime.execute("let captured = " + source) == ""
            captured = runtime.bindings["captured"]
        elif mode == "evaluate":
            captured = runtime.evaluate(source)
        elif mode == "sync_sdk":
            captured = client.execute(source, working_directory=tmp_path)
        else:
            captured = runtime.execute(source)
        assert captured == ("" if mode == "standalone" else "function_0\nfunction_1")
        assert (tmp_path / "automatic.txt").read_text() == (
            "function_0\nfunction_1\n" if mode == "standalone" else ""
        )
        assert (tmp_path / "explicit.txt").read_text() == "function_0\nfunction_1\n"
        assert stub.stream_calls == 1
        assert runtime._scopes == [] and runtime._block_owners == []
        assert not client._values
        assert capsys.readouterr().out == ""


def test_async_sdk_match_do_capture_is_silent_to_selected_output(monkeypatch, tmp_path, capsys):
    stream = Stream([function_row(), completed("async-captured", 1)])
    stub = patch_stream(monkeypatch, stream)

    async def run():
        async with AsyncClient("unix:///tmp/test.sock") as client:
            await client.execute('set output to "automatic.txt"', working_directory=tmp_path)
            captured = await client.execute(
                'match functionDecl().bind("func") in "a.cc" do { print $func.value.node.qualified_name; }',
                working_directory=tmp_path,
            )
            assert captured == "function_0"
            assert (tmp_path / "automatic.txt").read_text() == ""
            assert not client._values

    asyncio.run(run())
    assert stub.stream_calls == 1
    assert capsys.readouterr().out == ""
