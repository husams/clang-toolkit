"""Real native dataflow and console acceptance of the CFG Page example."""
from __future__ import annotations
import asyncio
from contextlib import aclosing
from pathlib import Path
import subprocess
import sys
import grpc
import pytest
from pytest_bdd import given, when, then, scenarios, parsers
from clang_toolkit import AsyncClient, MatchValueError
from clang_toolkit.analysis_error import AnalysisError
from clang_toolkit.client import _variable_flow_request
from clang_toolkit._generated.analysis.v1 import variable_flow_pb2 as pb, analysis_service_pb2_grpc
from tests.e2e.test_network_steps import _launch_server

pytestmark = pytest.mark.e2e
scenarios("variable_flow.feature")


@given(parsers.parse("an isolated variable flow server using {transport}"), target_fixture="variable_server")
def variable_server(transport, tmp_path, request, monkeypatch):
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "storage"))
    server = _launch_server(transport, tmp_path, request, max_send_bytes=4096)
    source = tmp_path / "local_usage.cc"
    root = Path(__file__).resolve().parents[2]
    source.write_text((root / "examples/local_usage.cc").read_text())
    return server, source, root


@when("I analyze a retained variable after removing its source", target_fixture="variable_report")
def variable_report(variable_server, tmp_path):
    server, source, root = variable_server
    empty_libraries = tmp_path / "empty-libraries"
    empty_libraries.mkdir()
    script = (root / "examples/local_usage.ctk").read_text().replace('"examples/local_usage.cc"', f'"{source}"')
    console = subprocess.run([sys.executable, "-m", "clang_toolkit.cli.app", "--server", server.endpoint,
                              "--script-engine", "compiled", "--lib-dir", str(empty_libraries),
                              "--execute", script], text=True, capture_output=True, timeout=60)
    assert console.returncode == 0, console.stdout + console.stderr
    assert "Variable: x" in console.stdout and "Complete: true" in console.stdout
    assert "POSSIBLY_UNINITIALIZED" in console.stdout and "DEAD_STORE" in console.stdout
    standalone = script[:script.index('let report =')] + 'variableflow variables[0].v in functions[0].f\nprint "after completion"\n'
    streamed = subprocess.run([sys.executable, "-m", "clang_toolkit.cli.app", "--server", server.endpoint,
                               "--script-engine", "compiled", "--lib-dir", str(empty_libraries),
                               "--execute", standalone], text=True, capture_output=True, timeout=60)
    assert streamed.returncode == 0, streamed.stdout + streamed.stderr
    assert streamed.stdout.index('"completed"') < streamed.stdout.index("after completion")
    async def run():
        async with AsyncClient(server.endpoint) as client:
            tree = await client.parse(source)
            functions = await client.match_in('functionDecl(isDefinition(),hasName("example")).bind("f")', tree)
            function = functions[0].binding("f")
            variables = await client.match_in('varDecl(hasName("x")).bind("v")', function)
            variable = variables[0].binding("v")
            stale = _variable_flow_request(client, variable, function)
            stale.variable.expected_result_revision += 1
            with pytest.raises(grpc.aio.AioRpcError) as error:
                async for _ in analysis_service_pb2_grpc.AnalysisServiceStub(client._channel).StreamVariableFlow(stale):
                    pass
            assert error.value.code() == grpc.StatusCode.ABORTED
            async with AsyncClient(server.endpoint) as foreign:
                with pytest.raises(MatchValueError):
                    await foreign.variable_flow(variable, function)
            source.unlink()
            seen = []
            done = await client.stream_variable_flow(variable, function, on_event=seen.append)
            assert done.is_complete and seen[-1].HasField("completed")
            assert all(e.usage.provisional for e in seen if e.HasField("usage"))
            first_fact = next(i for i, e in enumerate(seen) if e.HasField("fact"))
            assert all(not e.HasField("usage") for e in seen[first_fact:])
            report = await client.variable_flow(variable, function)
            assert report.analysis.snapshot_generation == seen[0].started.snapshot_generation
            async with aclosing(client.variable_flow_stream(variable, function)) as stream:
                async for event in stream:
                    break
            assert client._value_operation_count == 0
            for limits in [{"max_events": 1}, {"max_iterations": 1}, {"max_blocks": 1}]:
                partial = []
                with pytest.raises(AnalysisError) as error:
                    await client.stream_variable_flow(variable, function, on_event=partial.append, **limits)
                assert error.value.code == grpc.StatusCode.RESOURCE_EXHAUSTED
                assert not any(e.HasField("completed") for e in partial)
            assert (await client.variable_flow(variable, function)).completed.is_complete
            # Total variable data exceeds one message; individual usage/fact
            # events fit, so graph collection is never required for transport.
            large_source = source.with_name("large_usage.cc")
            large_source.write_text("int large(int n) { int x=0;\n" +
                                    "\n".join(f"if(n == {i}) x={i + 1};" for i in range(80)) +
                                    "\nreturn x; }\n")
            large_tree = await client.parse(large_source)
            large_functions = await client.match_in('functionDecl(hasName("large")).bind("f")', large_tree)
            large_function = large_functions[0].binding("f")
            large_variables = await client.match_in('varDecl(hasName("x")).bind("v")', large_function)
            large_source.unlink()
            sizes = []
            large_findings = []
            def measure(event):
                sizes.append(event.ByteSize())
                if event.HasField("finding"):
                    large_findings.append(event.finding.message)
            completed = await client.stream_variable_flow(large_variables[0].binding("v"), large_function,
                                                           on_event=measure)
            assert completed.is_complete, large_findings
            assert sum(sizes) > 4096 and max(sizes) < 4096
            await variables.aclose()
            with pytest.raises(MatchValueError):
                await client.variable_flow(variable, function)
            return report
    return asyncio.run(run())


@then("the converged report identifies the uninitialized read and dead assignment")
def verified_report(variable_report):
    report = variable_report
    assert report.completed.is_complete and report.completed.usage_count == 6
    by_id = {u.id: u for u in report.usages}
    by_line = {by_id[f.usage_id].location.line: f for f in report.facts}
    assert by_line[6].initialization == pb.VariableFlowFact.MAYBE_INITIALIZED
    assert set(by_line[6].reaching_assignments) == {0, next(u.id for u in report.usages if u.location.line == 5)}
    assert by_line[7].dead_store and not by_line[8].dead_store
    assert by_line[9].initialization == pb.VariableFlowFact.INITIALIZED
    assert list(by_line[9].reaching_assignments) == [next(u.id for u in report.usages if u.location.line == 8)]
    assert {(f.kind, by_id[f.usage_id].location.line) for f in report.findings} == {
        (pb.VariableFlowFinding.POSSIBLY_UNINITIALIZED, 6), (pb.VariableFlowFinding.DEAD_STORE, 7)}
