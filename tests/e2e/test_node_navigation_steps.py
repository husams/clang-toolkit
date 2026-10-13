"""Real native transport and console acceptance for bound-node navigation."""
from __future__ import annotations
import asyncio
import os
from pathlib import Path
import subprocess
import sys
import grpc
import pytest
from pytest_bdd import given, when, then, scenarios, parsers
from clang_toolkit import AsyncClient, Client, MatchValueError
from clang_toolkit.cursors import CursorError
from clang_toolkit._generated.match.v1 import match_result_pb2 as scopes
from tests.e2e.test_network_steps import _launch_server

pytestmark = pytest.mark.e2e
scenarios("node_navigation.feature")


@given(parsers.parse("a navigation server using {transport}"), target_fixture="navigation_server")
def navigation_server(transport, tmp_path, request, monkeypatch):
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "storage"))
    return _launch_server(transport, tmp_path, request)


@when("I peek children and move down and up from retained bindings", target_fixture="navigation_result")
def navigate(navigation_server, tmp_path):
    root = Path(__file__).parents[2]
    path = tmp_path / "navigation.cc"
    path.write_text((root / "examples/bound_node_navigation.cc").read_text())
    script = (root / "examples/bound_node_navigation.ctk").read_text().replace(
        '"examples/bound_node_navigation.cc"', f'"{path}"')
    cli = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server",
         navigation_server.endpoint, "--execute", script],
        text=True, capture_output=True, timeout=60,
        env={**os.environ, "PYTHONPATH": str(root / "python")})
    assert cli.returncode == 0, cli.stdout + cli.stderr
    assert "Box::run" in cli.stdout and '"node_count": "1"' in cli.stdout
    assert "1 neighbours" in cli.stdout
    with Client(navigation_server.endpoint) as client:
        tree = client.parse(path)
        rows = client.match_in('cxxRecordDecl(hasName("Box"), isDefinition()).bind("r")', tree)
        box = rows[0].binding("r")
        methods = client.peek(box, query="cxxMethodDecl()")
        assert len(methods) == 2
        method = client.step(box, query='cxxMethodDecl(hasName("run"))')
        body = client.step(method, query="compoundStmt()")
        statement = client.step(body, query="returnStmt()")
        literal = client.step(statement, query="integerLiteral()")
        assert len(client.peek(literal)) == 0
        assert len(client.peek(method, query="integerLiteral()")) == 0
        assert client.step(body, axis="parents").decl_name == "Box::run"
        assert client.step(method, axis="parents", query="cxxRecordDecl()").decl_name == "Box"
        type_loc = client.step(method, query="typeLoc()")
        assert client.step(type_loc, axis="parents").decl_name == "Box::run"
        for options, message in [({}, "ambiguous"),
                                 ({"query": "callExpr()"}, "no candidates"),
                                 ({"at": 99}, "outside")]:
            with pytest.raises(MatchValueError, match=message):
                client.step(box, **options)
        # Source files are unnecessary once a snapshot is pinned.
        path.unlink()
        assert len(client.match_in('integerLiteral().bind("n")', method)) == 1
        assert client.step(literal, axis="parents").value.node.HasField("return_stmt")
        provisional = []
        with pytest.raises(CursorError) as error:
            client.peek(box, max_nodes=1, on_row=provisional.append)
        assert error.value.code == grpc.StatusCode.RESOURCE_EXHAUSTED
        assert len(provisional) == 1
        assert len(client.peek(box, query="cxxMethodDecl()")) == 2
    # Exercise the asynchronous console expression adapter as well.
    async def run():
        async_path = tmp_path / "async.cc"
        async_path.write_text("int compute(){return 7;}")
        async with AsyncClient(navigation_server.endpoint) as client:
            for statement in [
                f'let tree = parse "{async_path}"',
                'let fs = match functionDecl(hasName("compute")).bind("f") in $tree',
                'let body = step children compoundStmt() in $fs[0].f',
                'let back = step parents functionDecl() in $body',
                'peek children returnStmt() in $body',
            ]:
                result = await client.execute(statement)
            assert len(result) == 1
    asyncio.run(run())
    return True


@then("immediate filtering, streaming, continued matching and source ownership hold")
def navigation_holds(navigation_result):
    assert navigation_result


@when("I match immediate children with an explicit scope", target_fixture="children_result")
def match_children(navigation_server, tmp_path):
    root = Path(__file__).parents[2]
    path = tmp_path / "children.cc"
    path.write_text((root / "examples/bound_node_navigation.cc").read_text())
    script = (root / "examples/match_children_scope.ctk").read_text().replace(
        '"examples/bound_node_navigation.cc"', f'"{path}"')
    cli = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server",
         navigation_server.endpoint, "--execute", script], text=True,
        capture_output=True, timeout=60,
        env={**os.environ, "PYTHONPATH": str(root / "python")})
    assert cli.returncode == 0, cli.stdout + cli.stderr
    assert cli.stdout.splitlines() == ["2", "3", "1", "0", "1", "Box::run", "Box::other", "1", "2"]
    with Client(navigation_server.endpoint) as client:
        tree = client.parse(path)
        rows = client.match_in('cxxRecordDecl(hasName("Box"), isDefinition()).bind("r")', tree)
        box = rows[0].binding("r", scope=scopes.BINDING_MATCH_SCOPE_CHILDREN)
        provisional = []
        methods = client.match_in('cxxMethodDecl().bind("m")', box, on_row=provisional.append)
        assert len(provisional) == len(methods) == 2
        assert all(set(row.bindings) == {"m", "root"} for row in methods)
        method = methods[0].binding("m", scope=scopes.BINDING_MATCH_SCOPE_CHILDREN)
        assert len(client.match_in("integerLiteral()", method)) == 0
        path.unlink()
        assert len(client.match_in("compoundStmt()", method)) == 1
        assert len(client.match_in("cxxMethodDecl()", box)) == 2
    async def run():
        path.write_text("int compute(){return 7;}")
        async with AsyncClient(navigation_server.endpoint) as client:
            await client.execute(f'let tree = parse "{path}"')
            await client.execute('let funcs = match functionDecl().bind("f") in $tree')
            result = await client.execute('match compoundStmt().bind("body") in $funcs[0].f scope children')
            assert len(result) == 1
    asyncio.run(run())
    return True


@then("scoped matches stream and preserve named native bindings")
def children_hold(children_result):
    assert children_result


@when("I navigate base specifiers and their bound class declarations", target_fixture="inheritance_result")
def navigate_inheritance(navigation_server, tmp_path):
    root = Path(__file__).parents[2]
    path = tmp_path / "inheritance.cc"
    path.write_text((root / "examples/multiple_inheritance_navigation.cc").read_text())
    script = (root / "examples/multiple_inheritance_navigation.ctk").read_text().replace(
        '"examples/multiple_inheritance_navigation.cc"', f'"{path}"')
    cli = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server",
         navigation_server.endpoint, "--execute", script], text=True,
        capture_output=True, timeout=60,
        env={**os.environ, "PYTHONPATH": str(root / "python")})
    assert cli.returncode == 0, cli.stdout + cli.stderr
    assert cli.stdout.splitlines() == [
        "demo::Left", "demo::Right", "demo::Root", "demo::Root",
        "Unique base classes:", "demo::Left", "demo::Right", "demo::Root",
        "3", "demo::Leaf"]
    query = 'cxxBaseSpecifier(hasType(cxxRecordDecl().bind("base")))'
    with Client(navigation_server.endpoint) as client:
        tree = client.parse(path)
        rows = client.match_in('cxxRecordDecl(hasName("demo::Leaf"), isDefinition()).bind("cls")', tree)
        leaf = rows[0].binding("cls")
        provisional = []
        edges = client.peek(leaf, query=query, on_row=provisional.append)
        assert len(provisional) == len(edges) == 2
        assert all(row.bindings["target"].HasField("base_specifier") for row in provisional)
        assert [edge.binding("base").decl_name for edge in edges] == ["demo::Left", "demo::Right"]
        assert client.step(edges[0].binding("target"), axis="parents").decl_name == "demo::Leaf"
        loc = client.step(edges[0].binding("target"), query="typeLoc()")
        assert client.step(loc, axis="parents", query="cxxBaseSpecifier()").value.HasField("base_specifier")
        assert len(client.peek(leaf, query='cxxBaseSpecifier(isVirtual())')) == 0
        path.unlink()
        roots = client.peek(edges[0].binding("base"), query=query)
        assert roots[0].binding("base").decl_name == "demo::Root"
        scoped = client.match_in(query, rows[0].binding("cls", scope=scopes.BINDING_MATCH_SCOPE_CHILDREN))
        assert len(scoped) == 2 and all("target" not in row.bindings for row in scoped)
    async def run():
        path.write_text("struct A {}; struct B {}; struct Leaf : A, B {};")
        async with AsyncClient(navigation_server.endpoint) as client:
            await client.execute(f'let tree = parse "{path}"')
            await client.execute('let rows = match cxxRecordDecl(hasName("Leaf"), isDefinition()).bind("cls") in $tree')
            result = await client.execute(f'peek children {query} in $rows[0].cls')
            assert len(result) == 2
    asyncio.run(run())
    return True


@then("inheritance results stream and the simpler console example finds the diamond")
def inheritance_holds(inheritance_result):
    assert inheritance_result
