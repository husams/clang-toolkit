"""Native interval convergence, bounded transport and the exact console example."""
from __future__ import annotations

import asyncio
from contextlib import aclosing
from pathlib import Path
import subprocess
import sys

import grpc
import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from clang_toolkit import AsyncClient, MatchValueError
from clang_toolkit.analysis_error import AnalysisError
from clang_toolkit._generated.analysis.v1 import variable_flow_pb2 as pb
from tests.e2e.test_network_steps import _launch_server

pytestmark = pytest.mark.e2e
scenarios("value_ranges.feature")


@given(parsers.parse("an isolated value interval server using {transport}"), target_fixture="interval_server")
def interval_server(transport, tmp_path, request, monkeypatch):
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "storage"))
    server = _launch_server(transport, tmp_path, request, max_send_bytes=4096)
    root = Path(__file__).resolve().parents[2]
    source = tmp_path / "value_ranges.cc"
    source.write_text((root / "examples/value_ranges.cc").read_text())
    return server, source, root


@when("I analyze the loop ranges with retained nodes and the console", target_fixture="interval_report")
def interval_report(interval_server, tmp_path):
    server, source, root = interval_server
    libraries = tmp_path / "empty-libraries"
    libraries.mkdir()
    script = (root / "examples/value_ranges.ctk").read_text().replace(
        '"examples/value_ranges.cc"', f'"{source}"')
    result = subprocess.run([
        sys.executable, "-m", "clang_toolkit.cli.app", "--server", server.endpoint,
        "--script-engine", "compiled", "--lib-dir", str(libraries), "--execute", script,
    ], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == (root / "examples/value_ranges.output.txt").read_text()
    standalone = script[:script.index("let report =")] + (
        'variableflow variables[0].v in functions[0].f values interval\nprint "finished"\n')
    result = subprocess.run([
        sys.executable, "-m", "clang_toolkit.cli.app", "--server", server.endpoint,
        "--script-engine", "compiled", "--lib-dir", str(libraries), "--execute", standalone,
    ], capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '"value_before"' in result.stdout
    assert result.stdout.index('"completed"') < result.stdout.index("finished")

    async def run():
        async with AsyncClient(server.endpoint) as client:
            tree = await client.parse(source)
            functions = await client.match_in('functionDecl(hasName("score")).bind("f")', tree)
            function = functions[0].binding("f")
            variables = await client.match_in('varDecl(hasName("total")).bind("v")', function)
            variable = variables[0].binding("v")
            source.unlink()
            plain = await client.variable_flow(variable, function)
            assert all(not fact.HasField("value_before") for fact in plain.facts)
            report = await client.variable_flow(variable, function, value_domain="interval")
            assert report.analysis.value_domain == pb.INTERVAL
            assert report.analysis.snapshot_generation == plain.analysis.snapshot_generation
            sizes = []
            done = await client.stream_variable_flow(
                variable, function, value_domain="interval", on_event=lambda e: sizes.append(e.ByteSize()))
            assert done.is_complete and max(sizes) <= 4096
            async with aclosing(client.variable_flow_stream(variable, function, value_domain="interval")) as stream:
                async for event in stream:
                    assert event.HasField("started")
                    break
            for limits in ({"max_iterations": 1}, {"max_events": 1}):
                seen = []
                with pytest.raises(AnalysisError) as error:
                    await client.stream_variable_flow(variable, function, value_domain="interval",
                                                     on_event=seen.append, **limits)
                assert error.value.code == grpc.StatusCode.RESOURCE_EXHAUSTED
                assert not any(e.HasField("completed") for e in seen)
            assert (await client.variable_flow(variable, function, value_domain="interval")).completed.is_complete
            async with AsyncClient(server.endpoint) as foreign:
                with pytest.raises(MatchValueError):
                    await foreign.variable_flow(variable, function, value_domain="interval")
            large = source.with_name("large_ranges.cc")
            large.write_text("int large(int n){int x=0;\n" +
                             "\n".join(f"if(n=={i})x={i + 1};" for i in range(80)) + "\nreturn x;}")
            large_tree = await client.parse(large)
            large_functions = await client.match_in('functionDecl(hasName("large")).bind("f")', large_tree)
            large_function = large_functions[0].binding("f")
            large_variables = await client.match_in('varDecl(hasName("x")).bind("v")', large_function)
            large.unlink()
            sizes.clear()
            done = await client.stream_variable_flow(
                large_variables[0].binding("v"), large_function, value_domain="interval",
                on_event=lambda e: sizes.append(e.ByteSize()))
            assert done.is_complete and sum(sizes) > 4096 and max(sizes) <= 4096
            await variables.aclose()
            with pytest.raises(MatchValueError):
                await client.variable_flow(variable, function, value_domain="interval")
            return report
    return asyncio.run(run())


@then("the numeric facts match the loop invariant and capped branches")
def verify_intervals(interval_report):
    report = interval_report
    assert report.completed.is_complete and not report.findings
    usages = {u.id: u for u in report.usages}
    facts = {usages[f.usage_id].location.line: f for f in report.facts}
    expected = {2: (None, (0, 0)), 5: ((0, 10), (2, 12)), 7: ((0, 10), (1, 11)),
                9: ((1, 12), (1, 12)), 10: ((11, 12), (10, 10)), 13: ((0, 10), (0, 10))}
    assert facts.keys() == expected.keys()
    for line, ranges in expected.items():
        for value, bounds in zip((facts[line].value_before, facts[line].value_after), ranges):
            if bounds is None:
                assert value.kind == pb.VariableValueRange.UNINITIALIZED
            else:
                assert value.kind == pb.VariableValueRange.INTERVAL
                assert (int(value.lower), int(value.upper)) == bounds
