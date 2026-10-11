"""Independent wire-level acceptance of durable runs and native batch syntax."""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import time

import grpc
import pytest
from pytest_bdd import given, scenarios, then, when

from clang_toolkit import Client
from clang_toolkit._generated.analysis.v1 import analysis_service_pb2_grpc, batch_pb2
from test_network_steps import _launch_server

pytestmark = pytest.mark.e2e
scenarios("durable_batch_native.feature")


@given("an isolated durable batch server with five translation units", target_fixture="durable_server")
def durable_server(tmp_path, request, monkeypatch):
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "durable-storage"))
    server = _launch_server("unix", tmp_path, request, max_files=2)
    for index in range(5):
        (tmp_path / f"unit-{index}.cc").write_text(
            f"int function_{index}(){{ return {index}; }}\n", encoding="utf-8"
        )
    with Client(server.endpoint) as client:
        manifest = client.discover_files([str(tmp_path / "unit-*.cc")])
    return server, tmp_path, manifest, request


def wire_request(manifest, body):
    request = batch_pb2.StartBatchRequest(
        request_id="independent-acceptance", body_source=body,
        group_variable="part", size=2, jobs=2,
    )
    for descriptor in manifest:
        request.inputs.add().CopyFrom(descriptor.to_proto())
    return request


def await_terminal(stub, run_id, timeout=40):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        run = stub.BatchStatus(batch_pb2.BatchRunRequest(run_id=run_id), timeout=5)
        if run.state not in {"queued", "running"}:
            return run
        time.sleep(0.02)
    pytest.fail(f"durable run {run_id} did not terminate")


@when("I start a native batch and disconnect its caller", target_fixture="disconnected_run")
def disconnect_caller(durable_server):
    server, _, manifest, _ = durable_server
    body = 'let rows = match functionDecl(isExpansionInMainFile()).bind("f") in $part.inputs; rows;'
    request = wire_request(manifest, body)
    with grpc.insecure_channel(server.endpoint) as channel:
        stub = analysis_service_pb2_grpc.AnalysisServiceStub(channel)
        invalid = batch_pb2.StartBatchRequest()
        invalid.CopyFrom(request)
        invalid.body_source = "let broken = ;"
        with pytest.raises(grpc.RpcError) as malformed:
            stub.StartBatch(invalid, timeout=5)
        assert malformed.value.code() == grpc.StatusCode.INVALID_ARGUMENT
        with Client(server.endpoint) as client:
            before = client.resource_status()
        assert before.active_work == before.reserved_bytes == before.accounted_native_bytes == 0
        started = stub.StartBatch(request, timeout=10)
        assert not started.results_complete
    with grpc.insecure_channel(server.endpoint) as channel:
        stub = analysis_service_pb2_grpc.AnalysisServiceStub(channel)
        run = await_terminal(stub, started.run_id)
        repeated = stub.StartBatch(request, timeout=10)
        assert repeated.run_id == run.run_id
        assert repeated.revision == run.revision
        changed = batch_pb2.StartBatchRequest()
        changed.CopyFrom(request)
        changed.body_source = "1;"
        with pytest.raises(grpc.RpcError):
            stub.StartBatch(changed, timeout=5)
        with pytest.raises(grpc.RpcError) as stale:
            stub.CancelBatch(batch_pb2.BatchControlRequest(
                run_id=run.run_id, expected_revision=run.revision - 1), timeout=5)
        assert stale.value.code() == grpc.StatusCode.ABORTED
    return run


@then("the durable results agree with serial matching and resources are released")
def verify_disconnected(durable_server, disconnected_run):
    server, _, manifest, _ = durable_server
    run = disconnected_run
    assert run.state == "completed", run
    assert run.results_complete
    assert [len(group.inputs) for group in run.groups] == [2, 2, 1]
    assert all(group.cleanup_acknowledged for group in run.groups)
    actual = sum(len(group.result.emissions[-1].value.matches.rows) for group in run.groups)
    with Client(server.endpoint) as client:
        serial = 0
        for descriptor in manifest:
            with client.match_in('functionDecl(isExpansionInMainFile()).bind("f")', descriptor) as rows:
                serial += len(rows)
        status = client.resource_status()
    assert actual == serial == 5
    assert status.active_work == status.result_cursors == status.explicit_file_leases == 0
    assert status.reserved_bytes == 0


@when("I complete an exported native batch and restart the server", target_fixture="restarted_run")
def restart_completed(durable_server):
    server, root, manifest, request = durable_server
    output = root / "export-${part.index}.json"
    body = (
        'let rows = match functionDecl(isExpansionInMainFile()).bind("f") in $part.inputs; '
        f'save rows to "{output}" as json; rows;'
    )
    with grpc.insecure_channel(server.endpoint) as channel:
        stub = analysis_service_pb2_grpc.AnalysisServiceStub(channel)
        started = stub.StartBatch(wire_request(manifest, body), timeout=10)
        run = await_terminal(stub, started.run_id)
    assert run.state == "completed", run
    exports = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in root.glob("export-*.json")}
    assert len(exports) == 3
    server.process.terminate()
    server.process.communicate(timeout=10)
    executable = Path(os.environ.get(
        "CTK_SERVER", Path(__file__).parents[2] / "build/dev/server/ctk-server"
    ))
    process = subprocess.Popen(
        [str(executable), "-c", str(server.config)], cwd=root / "work",
        env=dict(os.environ, HOME=str(root / "home")),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    def cleanup():
        if process.poll() is None:
            process.terminate()
        process.communicate(timeout=10)
    request.addfinalizer(cleanup)
    with grpc.insecure_channel(server.endpoint) as channel:
        grpc.channel_ready_future(channel).result(timeout=10)
        stub = analysis_service_pb2_grpc.AnalysisServiceStub(channel)
        restored = stub.BatchStatus(batch_pb2.BatchRunRequest(run_id=run.run_id), timeout=5)
    return run, restored, exports


@then("status retains the results and committed exports without replay")
def verify_restarted(restarted_run):
    before, after, exports = restarted_run
    assert before == after
    assert all(group.exports and group.exports[0].state == "committed" for group in after.groups)
    assert all(receipt.digest for group in after.groups for receipt in group.exports)
    for path, evidence in exports.items():
        assert (path.read_bytes(), path.stat().st_mtime_ns) == evidence


@when("I evaluate a batch through the native script API", target_fixture="native_expression")
def native_batch_expression(durable_server):
    server, root, _, _ = durable_server
    source = (
        f'let inputs = files "{root / "unit-*.cc"}"; '
        'let run = batch part in $inputs size 2 jobs 2 do { '
        'let rows = match functionDecl(isExpansionInMainFile()) in $part.inputs; rows; }; '
        'emit run;'
    )
    with Client(server.endpoint) as client:
        response = client.run_script(source, max_steps=10000)
        return response, client.resource_status()


@then("native expression results are detached and group cleanup is acknowledged")
def verify_native_expression(native_expression):
    response, resources = native_expression
    report = response.emissions[-1].value.object.fields
    assert report["status"].scalar.text == "completed"
    assert report["results_complete"].scalar.boolean
    values = report["results"].list.values
    assert sum(len(value.matches.rows) for value in values) == 5
    assert resources.result_cursors == resources.explicit_file_leases == resources.active_work == 0
    assert resources.reserved_bytes == resources.accounted_native_bytes == 0


@when("I retry a known failed export after repairing its destination", target_fixture="retried_run")
def retry_failed_exports(durable_server):
    server, root, manifest, _ = durable_server
    export_root = root.parent / f"{root.name}-exports"
    export_root.mkdir()
    destinations = [export_root / f"retry-{index}.json" for index in range(1, 4)]
    for destination in destinations:
        destination.mkdir()
    body = (
        'let rows = match functionDecl(isExpansionInMainFile()) in $part.inputs; '
        f'save rows to "{export_root / "retry-${part.index}.json"}" as json; rows;'
    )
    request = wire_request(manifest, body)
    request.continue_on_error = True
    with grpc.insecure_channel(server.endpoint) as channel:
        stub = analysis_service_pb2_grpc.AnalysisServiceStub(channel)
        started = stub.StartBatch(request, timeout=10)
        failed = await_terminal(stub, started.run_id)
        assert failed.state == "failed", failed
        assert all(group.state == "failed" and group.cleanup_acknowledged for group in failed.groups)
        for destination in destinations:
            destination.rmdir()
        stub.RetryBatch(batch_pb2.BatchControlRequest(
            run_id=failed.run_id, expected_revision=failed.revision), timeout=10)
        return await_terminal(stub, failed.run_id), destinations


@then("all retried groups complete with committed exports")
def verify_retried_exports(retried_run):
    run, destinations = retried_run
    assert run.state == "completed" and run.results_complete, run
    assert all(group.state == "completed" and group.cleanup_acknowledged for group in run.groups)
    assert all(receipt.state == "committed" for group in run.groups for receipt in group.exports)
    assert all(destination.is_file() for destination in destinations)


@when("I change a consumed header before retrying a failed group", target_fixture="changed_header_retry")
def changed_header_retry(durable_server):
    server, root, _, _ = durable_server
    header = root / "dependency.hpp"
    header.write_text("constexpr int value = 1;\n", encoding="utf-8")
    source = root / "with-header.cc"
    source.write_text('#include "dependency.hpp"\nint f(){return value;}\n', encoding="utf-8")
    with Client(server.endpoint) as client:
        manifest = client.discover_files([str(source)])
    destination = root / "blocked.json"
    destination.mkdir()
    body = (
        'let rows = match functionDecl(isExpansionInMainFile()) in $part.inputs; '
        f'save rows to "{destination}" as json; rows;'
    )
    with grpc.insecure_channel(server.endpoint) as channel:
        stub = analysis_service_pb2_grpc.AnalysisServiceStub(channel)
        started = stub.StartBatch(wire_request(manifest, body), timeout=10)
        failed = await_terminal(stub, started.run_id)
        assert failed.groups[0].state == "failed" and failed.groups[0].cleanup_acknowledged, failed
        header.write_text("constexpr int value = 2;\n", encoding="utf-8")
        destination.rmdir()
        with pytest.raises(grpc.RpcError) as rejected:
            stub.RetryBatch(batch_pb2.BatchControlRequest(
                run_id=failed.run_id, expected_revision=failed.revision), timeout=10)
        restored = stub.BatchStatus(batch_pb2.BatchRunRequest(run_id=failed.run_id), timeout=5)
    return failed, restored, rejected.value.code(), destination


@then("retry rejects the changed dependency without mutating the run")
def verify_changed_header_retry(changed_header_retry):
    before, after, code, destination = changed_header_retry
    assert code == grpc.StatusCode.FAILED_PRECONDITION
    assert before == after
    assert not destination.exists()


@when("I cancel admitted native work and resume the durable run", target_fixture="cancelled_resumed_run")
def cancel_resume_run(durable_server):
    server, root, _, _ = durable_server
    source = root / "unit-0.cc"
    source.write_text(
        "int function_0(){return 0;}\n" + "".join(
            f"int helper_{index}(){{return {index};}}\n" for index in range(12000)
        ), encoding="utf-8",
    )
    with Client(server.endpoint) as client:
        manifest = client.discover_files([str(root / "unit-*.cc")])
    request = wire_request(manifest,
        'foreach n in [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14] { '
        'let ignored = match functionDecl(hasName("function_0")) in $part.inputs; } '
        '$part.index;')
    with grpc.insecure_channel(server.endpoint) as channel:
        stub = analysis_service_pb2_grpc.AnalysisServiceStub(channel)
        started = stub.StartBatch(request, timeout=10)
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            run = stub.BatchStatus(batch_pb2.BatchRunRequest(run_id=started.run_id), timeout=5)
            assert run.state in {"queued", "running"}, run
            if any(group.state == "running" and all(
                revision.startswith("closure:") for revision in group.source_revisions
            ) for group in run.groups):
                try:
                    stub.CancelBatch(batch_pb2.BatchControlRequest(
                        run_id=run.run_id, expected_revision=run.revision), timeout=5)
                    break
                except grpc.RpcError as error:
                    assert error.code() == grpc.StatusCode.ABORTED
            time.sleep(0.002)
        else:
            pytest.fail("did not observe admitted native work before cancellation")
        cancelled = await_terminal(stub, run.run_id)
        assert cancelled.state == "cancelled", cancelled
        assert any(group.state == "pending" for group in cancelled.groups)
        assert all(group.cleanup_acknowledged for group in cancelled.groups if group.state == "cancelled")
        stub.ResumeBatch(batch_pb2.BatchControlRequest(
            run_id=cancelled.run_id, expected_revision=cancelled.revision), timeout=5)
        resumed = await_terminal(stub, run.run_id)
        assert any(group.state == "cancelled" for group in resumed.groups)
        stub.RetryBatch(batch_pb2.BatchControlRequest(
            run_id=resumed.run_id, expected_revision=resumed.revision), timeout=10)
        completed = await_terminal(stub, run.run_id)
    with Client(server.endpoint) as client:
        resources = client.resource_status()
    return completed, resources


@then("pending and cancelled groups eventually complete without leaked ownership")
def verify_cancel_resume_run(cancelled_resumed_run):
    run, resources = cancelled_resumed_run
    assert run.state == "completed" and run.results_complete, [
        (group.index, group.state, group.message, group.cleanup_acknowledged)
        for group in run.groups
    ]
    assert all(group.state == "completed" and group.cleanup_acknowledged for group in run.groups)
    assert resources.active_work == resources.result_cursors == resources.explicit_file_leases == 0
    assert resources.accounted_native_bytes == resources.reserved_bytes == 0


@when("I kill the server during admitted native work and restart it", target_fixture="killed_recovered_run")
def kill_recover_run(durable_server):
    server, root, _, request = durable_server
    source = root / "unit-0.cc"
    source.write_text(
        "int function_0(){return 0;}\n" + "".join(
            f"int helper_{index}(){{return {index};}}\n" for index in range(12000)
        ), encoding="utf-8",
    )
    with Client(server.endpoint) as client:
        manifest = client.discover_files([str(root / "unit-*.cc")])
    body = (
        'foreach n in [0,1,2,3,4,5,6,7,8,9,10,11,12,13,14] { '
        'let ignored = match functionDecl(hasName("function_0")) in $part.inputs; } '
        '$part.index;'
    )
    with grpc.insecure_channel(server.endpoint) as channel:
        stub = analysis_service_pb2_grpc.AnalysisServiceStub(channel)
        started = stub.StartBatch(wire_request(manifest, body), timeout=10)
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            current = stub.BatchStatus(batch_pb2.BatchRunRequest(run_id=started.run_id), timeout=5)
            assert current.state in {"queued", "running"}, current
            if any(group.state == "running" and all(
                revision.startswith("closure:") for revision in group.source_revisions
            ) for group in current.groups):
                break
            time.sleep(0.002)
        else:
            pytest.fail("did not observe admitted native work before process loss")
    server.process.kill()
    server.process.communicate(timeout=10)
    default_executable = Path(__file__).parents[2] / "build/dev/server/ctk-server"
    process = subprocess.Popen(
        [os.environ.get("CTK_SERVER", str(default_executable)), "-c", str(server.config)],
        cwd=root / "work", env=dict(os.environ, HOME=str(root / "home")),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    def cleanup():
        if process.poll() is None:
            process.terminate()
        process.communicate(timeout=10)
    request.addfinalizer(cleanup)
    with grpc.insecure_channel(server.endpoint) as channel:
        grpc.channel_ready_future(channel).result(timeout=10)
        stub = analysis_service_pb2_grpc.AnalysisServiceStub(channel)
        recovered = stub.BatchStatus(batch_pb2.BatchRunRequest(run_id=started.run_id), timeout=5)
        rejected = []
        for action in [stub.ResumeBatch, stub.RetryBatch]:
            with pytest.raises(grpc.RpcError) as error:
                action(batch_pb2.BatchControlRequest(
                    run_id=recovered.run_id, expected_revision=recovered.revision), timeout=5)
            rejected.append(error.value.code())
        after = stub.BatchStatus(batch_pb2.BatchRunRequest(run_id=started.run_id), timeout=5)
    with Client(server.endpoint) as client:
        resources = client.resource_status()
    return recovered, after, rejected, resources


@then("the interrupted group is unknown and cannot be silently resumed")
def verify_kill_recover(killed_recovered_run):
    before, after, codes, resources = killed_recovered_run
    assert before == after
    assert after.state == "interrupted" and not after.results_complete
    assert any(group.state == "unknown" and not group.cleanup_acknowledged for group in after.groups)
    assert codes == [grpc.StatusCode.FAILED_PRECONDITION] * 2
    assert resources.active_work == resources.result_cursors == resources.explicit_file_leases == 0
    assert resources.accounted_native_bytes == resources.reserved_bytes == 0
