"""Native CFG transport, retained ownership, byte bounds and console acceptance."""
from __future__ import annotations
import asyncio
import json
import subprocess
import sys
import grpc
import pytest
from pytest_bdd import given, when, then, scenarios, parsers
from clang_toolkit import AsyncClient
from clang_toolkit.client import _cfg_value_request
from clang_toolkit.cursors import CursorError
from clang_toolkit.match_values import MatchValueError
from clang_toolkit.analysis_error import AnalysisError
from clang_toolkit._generated.analysis.v1 import analysis_service_pb2_grpc
from tests.e2e.test_network_steps import _launch_server

pytestmark = pytest.mark.e2e
scenarios("cfg_streaming.feature")


@given(parsers.parse("an isolated CFG server using {transport}"), target_fixture="cfg_server")
def cfg_server(transport, tmp_path, request, monkeypatch):
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "storage"))
    server = _launch_server(transport, tmp_path, request)
    source = tmp_path / "flow.cc"
    (tmp_path / "header.hpp").write_text('int from_header() { return 3; }\n')
    source.write_text('#include "header.hpp"\n'
                      'struct Worker { int run(int x) { if(x) return 1; return 0; } };\n'
                      'namespace demo { int work(int x) { int y=7; if (false) y=9; if(x) return y; return 2; } '
                      'int work(double x) { return int(x); } }\n'
                      'template<class T> T dependent(T x) { return x; }\n')
    return server, source


@when("I stream CFGs after removing the parsed source", target_fixture="retained_cfgs")
def retained_cfgs(cfg_server):
    server, source = cfg_server
    script = (f'let tree = parse "{source}"\n'
              'let functions = match functionDecl(isDefinition(), hasName("demo::work")).bind("f") in tree\n'
              'cfg "demo::work" in tree\n'
              'cfg in functions[0].f\n'
              'let flow = cfg in functions[0].f\n'
              'print flow.graphs.length\n')
    console = subprocess.run([sys.executable, "-m", "clang_toolkit.cli.app", "--server",
                              server.endpoint, "--script-engine", "compiled", "--execute", script],
                             text=True, capture_output=True, timeout=60)
    assert console.returncode == 0, console.stdout + console.stderr
    assert '"graph_started"' in console.stdout and '"graph_completed"' in console.stdout
    assert '"graph_count": "2"' in console.stdout
    remaining = console.stdout.lstrip()
    kinds = []
    decoder = json.JSONDecoder()
    while remaining:
        value, offset = decoder.raw_decode(remaining)
        if isinstance(value, dict):
            kinds.append(next(iter(value)))
        remaining = remaining[offset:].lstrip()
    assert kinds.count("completed") == 2
    starts = [i for i, kind in enumerate(kinds) if kind == "graph_started"]
    assert len(starts) == 3  # Two overloads, then the exact selected function.
    assert kinds.index("completed") < starts[2]

    async def run():
        async with AsyncClient(server.endpoint) as client:
            tree = await client.parse(source)
            rows = await client.match_in('functionDecl(isDefinition(), hasName("demo::work")).bind("f")', tree)
            literal = await client.match_in('integerLiteral().bind("n")', tree)
            dependent = await client.match_in('functionDecl(hasName("dependent")).bind("f")', tree)
            method = await client.match_in('cxxMethodDecl(hasName("run")).bind("f")', tree)
            header = await client.match_in('functionDecl(hasName("from_header")).bind("f")', tree)
            manifest = await client.discover_files([str(source)])
            handle = await client.open_file(manifest.inputs[0])
            revision = rows._owner.revision
            stale = _cfg_value_request(client, rows[0].binding("f"))
            stale.binding.expected_result_revision += 1
            stub = analysis_service_pb2_grpc.AnalysisServiceStub(client._channel)
            with pytest.raises(grpc.aio.AioRpcError) as error:
                async for _ in stub.StreamCfg(stale):
                    pass
            assert error.value.code() == grpc.StatusCode.ABORTED
            async with AsyncClient(server.endpoint) as foreign:
                with pytest.raises(MatchValueError):
                    await foreign.cfg(tree, "demo::work")
            source.unlink()
            generations = []
            for target, name, count in [(tree, "demo::work", 2), (rows[0].binding("f"), None, 1),
                                         (rows.binding("f"), None, 2), (handle, "demo::work", 2)]:
                seen = []
                completed = await client.stream_cfg(target, name, on_event=seen.append)
                assert completed.graph_count == count
                assert seen[-1].HasField("completed")
                assert completed.block_count == sum(e.HasField("block") for e in seen)
                graph_generations = [e.graph_started.snapshot_generation for e in seen if e.HasField("graph_started")]
                assert len(set(graph_generations)) == 1
                generations.append(graph_generations[0])
                collected = await client.cfg(target, name)
                request = _cfg_value_request(client, target, name)
                unary = await analysis_service_pb2_grpc.AnalysisServiceStub(client._channel).Cfg(request)
                assert collected == unary
            assert len(set(generations[:3])) == 1 and all(g > 0 for g in generations)
            assert rows._owner.revision == revision
            assert (await client.cfg(method[0].binding("f"))).graphs[0].function.qualified_name == "Worker::run"
            assert (await client.cfg(header[0].binding("f"))).graphs
            with pytest.raises(AnalysisError) as error:
                await client.cfg(header[0].binding("f"), main_file_only=True)
            assert error.value.code == grpc.StatusCode.NOT_FOUND
            assert len(await client.match_in('returnStmt()', rows[0].binding("f"))) > 0
            for target, code in [(literal[0].binding("n"), grpc.StatusCode.INVALID_ARGUMENT),
                                  (dependent[0].binding("f"), grpc.StatusCode.FAILED_PRECONDITION)]:
                with pytest.raises(AnalysisError) as error:
                    await client.cfg(target)
                assert error.value.code == code
            empty = await client.match_in('functionDecl(hasName("absent")).bind("f")', tree)
            assert not (await client.cfg(empty.binding("f"))).graphs
            await client.close_file(handle)
            with pytest.raises((AnalysisError, CursorError, MatchValueError)):
                await client.cfg(handle, "demo::work")
            await client.close_file(tree)
            with pytest.raises((AnalysisError, CursorError, MatchValueError)):
                await client.cfg(tree, "demo::work")
            assert (await client.cfg(rows[0].binding("f"))).graphs
            return completed.block_count
    return asyncio.run(run())


@then("the retained trees and matches remain usable without reparsing")
def retained_reused(retained_cfgs):
    assert retained_cfgs > 2


@given("a CFG server with small messages and many blocks", target_fixture="large_cfg")
def large_cfg(tmp_path, request, monkeypatch):
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "storage"))
    server = _launch_server("unix", tmp_path, request, max_send_bytes=4096)
    source = tmp_path / "many.cc"
    branches = "\n".join(f"if (x == {i}) x += {i + 1};" for i in range(80))
    source.write_text("int work(int x) {\n" + branches + "\nreturn x; }\n"
                      "int oversized(int x) {\n" + "x += 1;\n" * 2000 + "return x; }\n")
    return server, source


@when("I stream a CFG larger than one message", target_fixture="cfg_sizes")
def cfg_sizes(large_cfg):
    server, source = large_cfg
    async def run():
        async with AsyncClient(server.endpoint) as client:
            sizes = []
            def consume(event):
                sizes.append(event.ByteSize())
            done = await client.stream_cfg(source, "work", on_event=consume)
            assert done.block_count > 80
            for name, kwargs in [("work", {"max_blocks": 2}), ("oversized", {})]:
                seen = []
                with pytest.raises(AnalysisError) as error:
                    await client.stream_cfg(source, name, on_event=seen.append, **kwargs)
                assert error.value.code == grpc.StatusCode.RESOURCE_EXHAUSTED
                assert seen and not any(e.HasField("completed") for e in seen)
            return sum(sizes), max(sizes)
    return asyncio.run(run())


@then("each CFG event fits and incomplete streams fail explicitly")
def bounded_events(cfg_sizes):
    total, largest = cfg_sizes
    assert total > 4096 and largest < 4096
