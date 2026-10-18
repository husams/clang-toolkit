from __future__ import annotations

from unittest.mock import Mock

import pytest

from clang_toolkit.client import Client
from clang_toolkit.cli.runtime import Runtime


@pytest.mark.parametrize("engine", ["legacy", "tree", "compiled"])
@pytest.mark.parametrize("populated", [False, True])
def test_index_list_displays_count_and_preserves_project_values(tmp_path, engine, populated):
    from clang_toolkit._generated.index.v1 import index_service_pb2 as pb
    from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime

    client = Mock(spec=Client)
    client.compilation_database = None
    projects = [pb.ProjectIndexStatus(
        project_root="/remote/project", state=pb.INDEX_STATE_INDEXING,
        translation_units_indexed=2, translation_units_total=5,
        translation_units_completed=2, translation_units_skipped=1, translation_units_indexing=2,
    )] if populated else []
    client.list_project_indexes.return_value = pb.ListProjectIndexesResponse(
        projects=projects, total_count=len(projects))
    runtime = (Runtime(client, cwd=tmp_path, environment={}) if engine == "legacy"
               else PrototypeRuntime(client, script_engine=engine, cwd=tmp_path, environment={}))
    try:
        output = runtime.execute("index list")
        assert f"Total projects: {len(projects)}" in output
        assert output.splitlines()[1].split() == ["Project", "Path", "State", "Indexed", "Reused", "Newly", "indexed", "Indexing"]
        if populated:
            assert output.splitlines()[2].split() == [
                "project", "/remote/project", "INDEXING", "2/5", "indexed", "1", "1", "2"]
        else:
            assert "No indexed projects." in output
        client.list_project_indexes.assert_called_once_with()
        runtime.execute("let projects = index list")
        assert runtime.evaluate("$projects.total_count") == len(projects)
        if populated:
            assert runtime.evaluate("$projects.projects[0].project_root") == "/remote/project"
        client.parse.assert_not_called()
    finally:
        runtime.close()


def test_project_index_controls_route_project_and_preserve_values(tmp_path):
    from clang_toolkit._generated.index.v1 import index_service_pb2 as pb

    client = Mock(spec=Client)
    client.compilation_database = None
    status = pb.ProjectIndexStatus(project_root=str(tmp_path), state=pb.INDEX_STATE_PAUSED)
    client.start_project_index.return_value = status
    client.project_index_status.return_value = status
    client.pause_project_index.return_value = status
    client.resume_project_index.return_value = status
    client.cancel_project_index.return_value = status
    runtime = Runtime(client, cwd=tmp_path, environment={})
    try:
        runtime.execute('index start "."')
        client.start_project_index.assert_called_once_with(str(tmp_path))
        runtime.execute('index pause "."')
        client.pause_project_index.assert_called_once_with(str(tmp_path))
        runtime.execute('index resume "."')
        client.resume_project_index.assert_called_once_with(str(tmp_path))
        runtime.execute('index cancel "."')
        client.cancel_project_index.assert_called_once_with(str(tmp_path))
        output = runtime.execute('index status "."')
        assert "PAUSED" in output
        runtime.execute('let state = index status "."')
        assert runtime.evaluate('$state.project_root') == str(tmp_path)
    finally:
        runtime.close()


def test_project_symbol_lookup_routes_without_parsing(tmp_path):
    from clang_toolkit._generated.index.v1 import index_service_pb2 as pb

    client = Mock(spec=Client)
    client.compilation_database = None
    client.find_symbols.return_value = pb.FindSymbolsResponse(symbols=[
        pb.Symbol(usr="c:@F@leaf#", name="leaf", qualified_name="leaf",
                  file_path=str(tmp_path / "leaf.cc"), line=1, column=1),
    ])
    client.lookup_symbol.return_value = client.find_symbols.return_value
    runtime = Runtime(client, cwd=tmp_path, environment={})
    try:
        assert "leaf" in runtime.execute('index find "leaf" in "."')
        client.find_symbols.assert_called_once_with(str(tmp_path), "leaf", prefix=True, unique_symbols=True)
        runtime.execute('index lookup "c:@F@leaf#" in "."')
        client.lookup_symbol.assert_called_once_with(str(tmp_path), "c:@F@leaf#")
        client.parse.assert_not_called()
    finally:
        runtime.close()


@pytest.mark.parametrize("engine", ["legacy", "tree", "compiled"])
@pytest.mark.parametrize("target", ["ctk-lab", "/remote/ctk-lab", "./ctk-lab", "../ctk-lab"])
@pytest.mark.parametrize("command", ["status", "find"])
def test_index_commands_resolve_listed_names_and_preserve_paths(tmp_path, engine, target, command):
    from clang_toolkit._generated.index.v1 import index_service_pb2 as pb
    from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime

    client = Mock(spec=Client)
    client.compilation_database = None
    client.list_project_indexes.return_value = pb.ListProjectIndexesResponse(projects=[
        pb.ProjectIndexStatus(project_root="/remote/ctk-lab"),
    ])
    expected = ("/remote/ctk-lab" if target in {"ctk-lab", "/remote/ctk-lab"}
                else str((tmp_path / target).resolve()))
    client.project_index_status.return_value = pb.ProjectIndexStatus(project_root=expected)
    client.find_symbols.return_value = pb.FindSymbolsResponse(symbols=[
        pb.Symbol(name="clamp", qualified_name="flow::clamp", file_path=expected + "/flow.cc"),
    ])
    runtime = (Runtime(client, cwd=tmp_path, environment={}) if engine == "legacy"
               else PrototypeRuntime(client, script_engine=engine, cwd=tmp_path, environment={}))
    try:
        source = (f'index status "{target}"' if command == "status"
                  else f'index find "flow::clamp" in "{target}"')
        output = runtime.execute(source)
        assert expected in output
        if command == "find":
            assert "flow::clamp" in output
            client.find_symbols.assert_called_once_with(expected, "flow::clamp", prefix=True, unique_symbols=True)
        else:
            client.project_index_status.assert_called_once_with(expected)
        assert client.list_project_indexes.call_count == (1 if target == "ctk-lab" else 0)
    finally:
        runtime.close()


@pytest.mark.parametrize("engine", ["legacy", "tree", "compiled"])
@pytest.mark.parametrize("roots, message", [
    (["/one/ctk-lab", "/two/ctk-lab"], "Ambiguous project name"),
    (["/one/other"], "No indexed project named"),
])
@pytest.mark.parametrize("command", ["status", "find"])
def test_index_commands_reject_ambiguous_or_unknown_names(tmp_path, engine, roots, message, command):
    from clang_toolkit._generated.index.v1 import index_service_pb2 as pb
    from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime

    client = Mock(spec=Client)
    client.compilation_database = None
    client.list_project_indexes.return_value = pb.ListProjectIndexesResponse(projects=[
        pb.ProjectIndexStatus(project_root=root) for root in roots
    ])
    runtime = (Runtime(client, cwd=tmp_path, environment={}) if engine == "legacy"
               else PrototypeRuntime(client, script_engine=engine, cwd=tmp_path, environment={}))
    try:
        with pytest.raises(Exception, match=message) as error:
            source = ('index status "ctk-lab"' if command == "status"
                      else 'index find "flow::clamp" in "ctk-lab"')
            runtime.execute(source)
        if len(roots) > 1:
            assert all(root in str(error.value) for root in roots)
        client.project_index_status.assert_not_called()
        client.find_symbols.assert_not_called()
    finally:
        runtime.close()


@pytest.mark.parametrize("engine", ["legacy", "tree", "compiled"])
@pytest.mark.parametrize("pattern, exact, query", [
    ("cla", False, "cla"), ("flow::cl*", False, "flow::cl"),
    ("flow::clamp", True, "flow::clamp"), ("operator*", True, "operator*"),
    ("name_%", False, "name_%"),
])
def test_index_find_global_modes_keep_project_identity(tmp_path, engine, pattern, exact, query):
    from clang_toolkit._generated.index.v1 import index_service_pb2 as pb
    from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime

    client = Mock(spec=Client)
    client.compilation_database = None
    client.list_project_indexes.return_value = pb.ListProjectIndexesResponse(projects=[
        pb.ProjectIndexStatus(project_root="/one/demo"),
        pb.ProjectIndexStatus(project_root="/two/demo"),
    ])
    client.find_symbols.return_value = pb.FindSymbolsResponse(symbols=[
        pb.Symbol(name="clamp", qualified_name="flow::clamp", file_path="/fixture/flow.cc"),
    ], truncated=True)
    runtime = (Runtime(client, cwd=tmp_path, environment={}) if engine == "legacy"
               else PrototypeRuntime(client, script_engine=engine, cwd=tmp_path, environment={}))
    try:
        source = f'index find "{pattern}"' + (" exact" if exact else "")
        output = runtime.execute(source)
        assert "across 2 projects" in output
        assert "/one/demo" in output and "/two/demo" in output
        assert "Results truncated" in output
        assert [call.args for call in client.find_symbols.call_args_list] == [
            ("/one/demo", query), ("/two/demo", query)]
        assert all(call.kwargs == {"prefix": not exact, "unique_symbols": True}
                   for call in client.find_symbols.call_args_list)
        runtime.execute("let hits = " + source)
        assert runtime.evaluate("$hits[0].project_root") == "/one/demo"
        assert runtime.evaluate("$hits[0].result.symbols[0].qualified_name") == "flow::clamp"
        client.parse.assert_not_called()
    finally:
        runtime.close()


@pytest.mark.parametrize("engine", ["legacy", "tree", "compiled"])
@pytest.mark.parametrize("pattern", ["", "*", "*clamp", "cl*mp", "cl?mp", "[Cc]lamp"])
def test_index_find_rejects_scan_patterns_before_any_rpc(tmp_path, engine, pattern):
    from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime

    client = Mock(spec=Client)
    client.compilation_database = None
    runtime = (Runtime(client, cwd=tmp_path, environment={}) if engine == "legacy"
               else PrototypeRuntime(client, script_engine=engine, cwd=tmp_path, environment={}))
    try:
        with pytest.raises(Exception, match="nonempty name prefix"):
            runtime.execute(f'index find "{pattern}"')
        client.list_project_indexes.assert_not_called()
        client.find_symbols.assert_not_called()
    finally:
        runtime.close()


@pytest.mark.parametrize("engine", ["legacy", "tree", "compiled"])
def test_index_find_global_empty_and_failed_projects_are_explicit(tmp_path, engine):
    import grpc
    from clang_toolkit._generated.index.v1 import index_service_pb2 as pb
    from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
    from clang_toolkit.cursors import CursorError

    client = Mock(spec=Client)
    client.compilation_database = None
    client.list_project_indexes.return_value = pb.ListProjectIndexesResponse()
    runtime = (Runtime(client, cwd=tmp_path, environment={}) if engine == "legacy"
               else PrototypeRuntime(client, script_engine=engine, cwd=tmp_path, environment={}))
    try:
        assert "No indexed projects" in runtime.execute('index find "cla" in "*"')
        client.find_symbols.assert_not_called()
        client.list_project_indexes.return_value = pb.ListProjectIndexesResponse(projects=[
            pb.ProjectIndexStatus(project_root="/one/broken"),
            pb.ProjectIndexStatus(project_root="/two/good"),
        ])
        client.find_symbols.side_effect = [
            CursorError(grpc.StatusCode.UNAVAILABLE, "unavailable test project"),
            pb.FindSymbolsResponse(symbols=[pb.Symbol(qualified_name="clamp")]),
        ]
        output = runtime.execute('index find "cla"')
        assert "Search failed: unavailable test project" in output
        assert "clamp" in output and "/two/good" in output
    finally:
        runtime.close()


@pytest.mark.parametrize("engine", ["legacy", "tree", "compiled"])
def test_index_find_scoped_exact_preserves_literal_query(tmp_path, engine):
    from clang_toolkit._generated.index.v1 import index_service_pb2 as pb
    from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime

    client = Mock(spec=Client)
    client.compilation_database = None
    client.find_symbols.return_value = pb.FindSymbolsResponse()
    runtime = (Runtime(client, cwd=tmp_path, environment={}) if engine == "legacy"
               else PrototypeRuntime(client, script_engine=engine, cwd=tmp_path, environment={}))
    try:
        runtime.execute('index find "operator*" exact in "."')
        client.find_symbols.assert_called_once_with(str(tmp_path), "operator*", prefix=False, unique_symbols=True)
        client.list_project_indexes.assert_not_called()
    finally:
        runtime.close()


@pytest.mark.parametrize("engine", ["legacy", "tree", "compiled"])
@pytest.mark.parametrize("category, raw", [("function", "Function"), ("class", "CXXRecord"), ("variable", "Var"), ("alias", "TypeAlias"), ("alias", "Typedef")])
@pytest.mark.parametrize("scope", ["", ' in "/project"'])
def test_optional_kind_filter_is_forwarded_and_kind_returned(tmp_path, engine, category, raw, scope):
    from clang_toolkit._generated.index.v1 import index_service_pb2 as pb
    from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime

    client = Mock(spec=Client)
    client.compilation_database = None
    client.list_project_indexes.return_value = pb.ListProjectIndexesResponse(projects=[
        pb.ProjectIndexStatus(project_root="/project")])
    client.find_symbols.return_value = pb.FindSymbolsResponse(symbols=[
        pb.Symbol(name="demo", qualified_name="demo", kind=raw)])
    runtime = (Runtime(client, cwd=tmp_path, environment={}) if engine == "legacy"
               else PrototypeRuntime(client, script_engine=engine, cwd=tmp_path, environment={}))
    try:
        source = f'index find "demo" exact kind {category}' + scope
        assert f"[{raw}]" in runtime.execute(source)
        client.find_symbols.assert_called_once_with("/project", "demo", prefix=False, kind=category, unique_symbols=True)
        runtime.execute("let hits = " + source)
        field = "$hits.symbols[0].kind" if scope else "$hits[0].result.symbols[0].kind"
        assert runtime.evaluate(field) == raw
    finally:
        runtime.close()


@pytest.mark.parametrize("engine", ["legacy", "tree", "compiled"])
def test_unknown_console_kind_fails_before_rpc(tmp_path, engine):
    from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime

    client = Mock(spec=Client)
    client.compilation_database = None
    runtime = (Runtime(client, cwd=tmp_path, environment={}) if engine == "legacy"
               else PrototypeRuntime(client, script_engine=engine, cwd=tmp_path, environment={}))
    try:
        with pytest.raises(Exception, match="kind must be"):
            runtime.execute('index find "demo" kind unknown')
        client.find_symbols.assert_not_called()
        client.list_project_indexes.assert_not_called()
    finally:
        runtime.close()
