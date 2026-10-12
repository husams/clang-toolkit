"""Real native transport coverage for retained-root traversal streams."""
from __future__ import annotations
import asyncio
import subprocess
import sys
from pathlib import Path
import grpc
import pytest
from pytest_bdd import given, when, then, scenarios, parsers
from clang_toolkit import AsyncClient
from clang_toolkit.analysis_error import AnalysisError
from tests.e2e.test_network_steps import _launch_server, RunningServer

pytestmark = pytest.mark.e2e
scenarios("node_traversal.feature")

@given(parsers.parse("a query server using {transport}"), target_fixture="server")
def node_server(transport, tmp_path, request, monkeypatch):
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "isolated-storage"))
    return _launch_server(transport, tmp_path, request)

@given("a native traversal fixture with types and inheritance", target_fixture="node_source")
def node_source(tmp_path):
    source = tmp_path / "nodes.cc"
    source.write_text("struct Base {}; struct Leaf : Base { int *p; int run(){return 7;} };\n")
    return source

@when("I stream visits from the parsed tree and its retained bindings", target_fixture="visits")
def stream_nodes(server: RunningServer, node_source: Path):
    # Exercise the installed console entry point with actual retained variables.
    script = (f'let tree = parse "{node_source}"\n'
              'let rows = match pointerType().bind("n") in $tree\n'
              'traverse $tree depth 0\n'
              'traverse $rows[0].n depth 1\n')
    cli = subprocess.run([sys.executable, "-m", "clang_toolkit.cli.app", "--server",
                          server.endpoint, "--execute", script],
                         text=True, capture_output=True, timeout=30)
    assert cli.returncode == 0, cli.stderr + cli.stdout
    assert '"native_kind": "TranslationUnitDecl"' in cli.stdout
    assert '"native_kind": "PointerType"' in cli.stdout
    assert '"node_count"' in cli.stdout
    async def run():
        async with AsyncClient(server.endpoint) as client:
            tree = await client.parse(node_source)
            selected = []
            for query in ['cxxRecordDecl(hasName("Leaf"), isDefinition()).bind("n")',
                          'integerLiteral().bind("n")',
                          'qualType(isInteger()).bind("n")',
                          'pointerType().bind("n")',
                          'typeLoc().bind("n")',
                          'cxxRecordDecl(hasName("Leaf"), isDefinition(), hasAnyBase(cxxBaseSpecifier().bind("n")))']:
                rows = await client.match_in(query, tree)
                assert len(rows) > 0, query
                selected.append((rows, rows[0].binding("n")))
            # A binding collection is an ordered forest, not an implicit first row.
            forest = []
            qual_rows = selected[2][0]
            result = await client.stream_traverse(qual_rows.binding("n"), max_depth=0,
                                                  on_node=forest.append)
            assert result.node_count == len(qual_rows)
            assert all(n.depth == 0 and not n.HasField("parent_index") for n in forest)
            empty = await client.match_in('functionDecl(hasName("absent")).bind("n")', tree)
            assert (await client.stream_traverse(empty.binding("n"), on_node=lambda n: None)).node_count == 0
            node_source.unlink()
            observed = []
            for target in [tree] + [binding for rows, binding in selected]:
                visits = []
                completion = await client.stream_traverse(target, on_node=visits.append)
                assert visits and visits[0].depth == 0
                assert not visits[0].HasField("parent_index")
                assert completion.node_count == len(visits)
                observed.append(visits[0].native_kind)
                # An explicit consumer limit fails after a provisional root.
                if len(visits) > 1:
                    provisional = []
                    with pytest.raises(AnalysisError) as error:
                        await client.stream_traverse(target, max_nodes=1, on_node=provisional.append)
                    assert error.value.code == grpc.StatusCode.RESOURCE_EXHAUSTED
                    assert len(provisional) == 1
                assert (await client.stream_traverse(target, max_depth=0, on_node=lambda n: None)).node_count == 1
            # Native continuation still works after traversal and source removal.
            methods = await client.match_in('cxxMethodDecl(hasName("run"))', selected[0][1])
            assert len(methods) == 1
            return observed
    return asyncio.run(run())

@then("visits precede completion and every native root remains reusable")
def check_visits(visits):
    assert visits[0] == "TranslationUnitDecl"
    assert "CXXRecordDecl" in visits and "IntegerLiteral" in visits
    assert "QualType" in visits and "PointerType" in visits
    assert any("TypeLoc" in name for name in visits)
    assert "CXXBaseSpecifier" in visits


@given("a traversal server with a small message limit and many nodes", target_fixture="small_stream")
def small_traversal_server(tmp_path, request, monkeypatch):
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "isolated-storage"))
    server = _launch_server("unix", tmp_path, request, max_send_bytes=4096)
    source = tmp_path / "many.cc"
    source.write_text("\n".join(f"int f{i}() {{ return {i}; }}" for i in range(200)))
    return server, source


@when("I consume a traversal whose visits exceed one message", target_fixture="stream_sizes")
def consume_many_nodes(small_stream):
    server, source = small_stream
    async def run():
        async with AsyncClient(server.endpoint) as client:
            total = count = largest = 0
            def consume(node):
                nonlocal total, count, largest
                size = node.ByteSize()
                total += size
                largest = max(largest, size)
                count += 1
            result = await client.stream_traverse(source, on_node=consume)
            assert result.node_count == count
            return count, total, largest
    return asyncio.run(run())


@then("each visit fits and the complete stream exceeds the message limit")
def check_stream_sizes(stream_sizes):
    count, total, largest = stream_sizes
    assert count > 200 and total > 4096 and largest < 4096
