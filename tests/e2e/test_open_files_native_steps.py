"""Serving-machine acceptance of opened files, scope cleanup and real CTK syntax."""
from __future__ import annotations

import os
import json
import subprocess
import sys

import grpc
import pytest
from pytest_bdd import given, scenarios, then, when

from clang_toolkit import Client
from clang_toolkit.cursors import CursorError
from clang_toolkit.match_values import MatchValueError
from clang_toolkit.cli.runtime.persistence import load
from clang_toolkit._generated.match.v1 import match_service_pb2 as match_pb
from clang_toolkit._generated.match.v1 import match_service_pb2_grpc
from clang_toolkit._generated.match.v1 import resources_pb2 as resource_pb
from tests.e2e.test_network_steps import _launch_server

pytestmark = pytest.mark.e2e
scenarios("open_files_native.feature")


def _fixture(tmp_path, request, monkeypatch, *, max_files=100, max_send_bytes=None):
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "isolated-storage"))
    server = _launch_server("unix", tmp_path, request, max_files=max_files,
                            max_send_bytes=max_send_bytes)
    return server, tmp_path


@given("an isolated opened-file server and changing sources", target_fixture="native_files")
def changing_files(tmp_path, request, monkeypatch):
    fixture = _fixture(tmp_path, request, monkeypatch)
    (tmp_path / "source.cc").write_text("int original(){ return 1; }\n", encoding="utf-8")
    return fixture


@when("I discover open refresh and independently close native file resources",
      target_fixture="lease_evidence")
def exercise_leases(native_files):
    server, root = native_files
    with Client(server.endpoint) as client:
        before = client.resource_status()
        manifest = client.discover_files(["source.cc"], working_directory=root)
        after_discovery = client.resource_status()
        assert len(manifest) == 1
        assert manifest.inputs[0].frozen_profile
        assert after_discovery.result_cursors == before.result_cursors == 0
        assert after_discovery.explicit_file_leases == 0
        source = client.open_file(manifest.inputs[0])
        independent = client.open_file(manifest.inputs[0])
        assert source.snapshot_id == independent.snapshot_id
        original = client.match_in('functionDecl().bind("f")', source)
        assert len(original) == 1
        source_alias = source
        closed = client.close_file(source_alias)
        assert closed.released_leases == 1
        assert len(client.match_in('functionDecl()', independent)) == 1
        assert len(client.match_in('returnStmt()', original[0].binding("f"))) == 1
        root_tree = client.parse(manifest.inputs[0])
        attached = client.attach_session(root_tree._owner.session_id)
        derived = root_tree.match('functionDecl().bind("f")')
        client.close_file(root_tree)
        with pytest.raises((CursorError, MatchValueError)):
            attached.match('functionDecl()')
        assert len(client.match_in('returnStmt()', derived[0].binding("f"))) == 1
        (root / "source.cc").write_text("int changed(){return 2;}\nint extra(){return 3;}\n", encoding="utf-8")
        updated = client.refresh_file(independent)
        assert updated.input.profile_id == independent.input.profile_id
        assert updated.snapshot_id != independent.snapshot_id
        assert len(client.match_in('functionDecl()', updated)) == 2
        assert len(client.match_in('functionDecl()', independent)) == 1
        assert len(client.match_in('functionDecl()', original)) == 1
        return len(manifest), source.snapshot_id, updated.snapshot_id


@then("file identities and independent pins remain correct")
def correct_leases(lease_evidence):
    count, old, new = lease_evidence
    assert count == 1 and old != new


@when("I execute every detached native analysis under a frozen resource scope",
      target_fixture="native_analysis_evidence")
def scoped_native_analyses(native_files):
    server, root = native_files
    with Client(server.endpoint) as client:
        manifest = client.discover_files(["source.cc"], working_directory=root)
        descriptor = manifest.inputs[0]
        scope = client.open_resource_scope(inputs=manifest.inputs, transient=True)
        assert client.traverse(descriptor, main_file_only=True, scope=scope).nodes
        assert client.cfg("original", path=descriptor, scope=scope).graphs
        assert client.callgraph(descriptor, main_file_only=True, scope=scope).nodes
        default_file = client.run_script('emit count(match("functionDecl()"));',
                                         path=descriptor, scope=scope)
        explicit_file = client.run_script(
            'let tree = parse "source.cc"; let rows = match functionDecl() in $tree; emit rows;',
            profile=descriptor, scope=scope,
        )
        assert default_file.emissions[0].value.scalar.integer == 1
        assert len(explicit_file.emissions[0].value.matches.rows) == 1
        claimed = scope.describe()
        released = scope.release()
        return claimed, released, client.resource_status()


@then("detached analyses account for their snapshots and release transient reuse")
def native_analyses_cleanup(native_analysis_evidence):
    claimed, released, remaining = native_analysis_evidence
    assert claimed.accounted_native_bytes > 0
    assert claimed.active_work == claimed.result_cursors == claimed.file_leases == 0
    assert released.cleanup_acknowledged
    assert remaining.accounted_native_bytes == remaining.reserved_bytes == 0
    assert remaining.reusable_snapshots == 0


@given("an isolated opened-file server with a two-input admission limit", target_fixture="native_batches")
def batch_files(tmp_path, request, monkeypatch):
    fixture = _fixture(tmp_path, request, monkeypatch, max_files=2)
    for index in range(5):
        (tmp_path / f"input-{index}.cc").write_text(f"int f{index}(){{return {index};}}\n", encoding="utf-8")
    return fixture


@when("I run real console size and count batches with detached exports", target_fixture="batch_evidence")
def real_batches(native_batches):
    server, root = native_batches
    script = '\n'.join([
        'let inputs = files "*.cc"',
        'file list discovered in $inputs',
        'batch part in $inputs size 2 jobs 2 memory "128MiB" do {',
        '  let rows = match functionDecl().bind("f") in $part.inputs;',
        '  save $rows to "size-${part.index}.proto" as proto;',
        '}',
        'batch part in $inputs count 3 do {',
        '  let rows = match functionDecl().bind("f") in $part.inputs;',
        '  save $rows to "count-${part.index}.json" as json;',
        '}',
        'resource status',
        'file list',
    ])
    result = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server", server.endpoint, "-e", script],
        cwd=root, env=dict(os.environ, XDG_STATE_HOME=str(root / "console-state")),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        timeout=60, check=False,
    )
    with Client(server.endpoint) as client:
        status = client.resource_status()
        files = client.list_files()
        manifest = client.discover_files(["*.cc"], working_directory=root)
        serial_count = 0
        for descriptor in manifest:
            with client.match_in('functionDecl().bind("f")', descriptor) as rows:
                serial_count += len(rows)
    return result, status, files, root, serial_count


@then("every group finishes with acknowledged cleanup and no native resources escape")
def batch_cleanup(batch_evidence):
    result, status, files, root, serial_count = batch_evidence
    assert result.returncode == 0, result.stdout
    reports = [json.loads(line) for line in result.stdout.splitlines()
               if line.startswith("{") and '"completed_groups"' in line]
    assert [report["completed_groups"] for report in reports] == [3, 3]
    assert all(report["cleanup_acknowledged"] for report in reports)
    assert status.result_cursors == 0
    assert status.explicit_file_leases == 0
    assert status.active_work == 0
    assert status.reserved_bytes == 0
    assert status.reusable_snapshots == 0
    assert not files
    assert len(list(root.glob("size-*.proto"))) == 3
    assert len(list(root.glob("count-*.json"))) == 3
    assert sum(len(load(path).rows) for path in root.glob("size-*.proto")) == serial_count == 5
    assert sum(len(load(path)) for path in root.glob("count-*.json")) == serial_count


@when("I reject an oversized scope and release a scope borrowing an existing snapshot",
      target_fixture="external_pin_evidence")
def external_pin_scope(native_batches):
    server, root = native_batches
    with Client(server.endpoint) as client:
        manifest = client.discover_files(["*.cc"], working_directory=root)
        borrowed = client.match_in('functionDecl().bind("f")', manifest.inputs[0])
        baseline = client.resource_status()
        with pytest.raises(CursorError):
            client.open_resource_scope(inputs=manifest.inputs[:3], transient=True)
        rejected = client.resource_status()
        scope = client.open_resource_scope(inputs=manifest.inputs[:2], transient=True)
        with client.match_in('functionDecl()', manifest.inputs[1],
                             scope=scope) as rows:
            assert len(rows) == 1
        released = scope.release()
        after = client.resource_status()
        assert len(client.match_in('returnStmt()', borrowed[0].binding("f"))) == 1
        inventory = client.list_files()
        return baseline, rejected, released, after, inventory


@then("admission is atomic and external result pins survive acknowledged cleanup")
def external_pins_remain(external_pin_evidence):
    baseline, rejected, released, after, inventory = external_pin_evidence
    assert rejected.explicit_file_leases == baseline.explicit_file_leases == 0
    assert rejected.result_cursors == baseline.result_cursors == 1
    assert rejected.reusable_snapshots == baseline.reusable_snapshots == 1
    assert rejected.reserved_bytes == 0
    assert released.cleanup_acknowledged
    assert after.result_cursors == 1
    assert after.reserved_bytes == after.active_work == 0
    assert after.reusable_snapshots == 1
    assert any(info.cursor_count > 0 for info in inventory)


@when("I fail batch bodies after exporting under stop and continue policies",
      target_fixture="native_error_evidence")
def native_batch_errors(native_batches):
    server, root = native_batches
    reports = {}
    for policy in ("stop", "continue"):
        script = '\n'.join([
            'let inputs = files "*.cc"',
            f'batch part in $inputs size 2 jobs 2 on error {policy} do {{',
            ' let rows = match functionDecl() in $part.inputs;',
            f' save $rows to "{policy}-${{part.index}}.json" as json;',
            ' print $missing;',
            '}',
        ])
        result = subprocess.run(
            [sys.executable, "-m", "clang_toolkit.cli.app", "--server", server.endpoint,
             "-e", script], cwd=root,
            env=dict(os.environ, XDG_STATE_HOME=str(root / "console-state")),
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
            timeout=60, check=False,
        )
        assert result.returncode == 1, result.stdout
        report_text = result.stdout.rsplit("batch failed: ", 1)[-1].strip()
        reports[policy] = json.loads(report_text)
        with Client(server.endpoint) as client:
            status = client.resource_status()
            assert status.result_cursors == status.explicit_file_leases == 0
            assert status.active_work == status.reserved_bytes == status.reusable_snapshots == 0
    return reports, root


@then("failure status preserves exports while every accepted group acknowledges cleanup")
def native_batch_errors_cleanup(native_error_evidence):
    reports, root = native_error_evidence
    assert reports["stop"]["failed_groups"] == 1
    assert reports["stop"]["skipped_groups"] == 2
    assert reports["continue"]["failed_groups"] == 3
    assert reports["continue"]["skipped_groups"] == 0
    assert all(report["cleanup_acknowledged"] for report in reports.values())
    assert len(list(root.glob("stop-*.json"))) == 1
    assert len(list(root.glob("continue-*.json"))) == 3
    assert sum(len(load(path)) for path in root.glob("continue-*.json")) == 5


@given("an isolated opened-file server with a small client reply limit", target_fixture="native_failed_reply")
def failed_reply_files(tmp_path, request, monkeypatch):
    fixture = _fixture(tmp_path, request, monkeypatch)
    (tmp_path / "large.cc").write_text(
        '\n'.join(f"int value_{index}(){{return {index};}}" for index in range(100)),
        encoding="utf-8",
    )
    return fixture


@when("a scoped unary match commits but its reply exceeds the transport limit",
      target_fixture="failed_reply_evidence")
def lost_reply(native_failed_reply):
    server, root = native_failed_reply
    with Client(server.endpoint) as client:
        manifest = client.discover_files(["large.cc"], working_directory=root)
        scope = client.open_resource_scope(inputs=manifest.inputs, transient=True)
        descriptor = manifest.inputs[0]
        request = match_pb.MatchRequest(query='functionDecl().bind("f")',
                                        resource_scope_id=scope.resource_scope_id)
        request.file.file_path = descriptor.path
        request.file.working_directory = descriptor.working_directory
        request.file.compile_arguments.extend(descriptor.compile_arguments)
        request.file.compilation_database = descriptor.compilation_database
        request.file.expected_profile_id = descriptor.profile_id
        request.file.frozen_profile = True
        with grpc.insecure_channel(
            server.endpoint, options=(("grpc.max_receive_message_length", 1024),)
        ) as channel:
            stub = match_service_pb2_grpc.MatchServiceStub(channel)
            with pytest.raises(grpc.RpcError) as error:
                # Exercise reply-size loss after publication, not a cold-server
                # deadline while the full native suite competes for resources.
                stub.Match(request, timeout=60)
        assert error.value.code() == grpc.StatusCode.RESOURCE_EXHAUSTED
        committed = scope.describe()
        released = scope.release()
        repeated = client.release_resource_scope(scope.resource_scope_id)
        remaining = client.resource_status()
        return committed, released, repeated, remaining


@then("releasing the scope acknowledges all provisional resources were closed")
def lost_reply_cleanup(failed_reply_evidence):
    committed, released, repeated, remaining = failed_reply_evidence
    assert committed.result_cursors == 1
    assert committed.accounted_native_bytes > 0
    assert released.cleanup_acknowledged
    assert released.state == resource_pb.RESOURCE_SCOPE_STATE_RELEASED
    assert repeated.cleanup_acknowledged
    assert released.result_cursors == released.file_leases == released.active_work == 0
    assert remaining.result_cursors == 0
    assert remaining.reserved_bytes == 0
    assert remaining.reusable_snapshots == 0
