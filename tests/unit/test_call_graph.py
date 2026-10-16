"""Call-graph option presence and grammar-driven client dispatch."""
from __future__ import annotations
import json
from unittest.mock import Mock
import pytest
from clang_toolkit._generated.analysis.v1 import call_graph_response_pb2 as pb
from clang_toolkit._generated.match.v1 import match_result_pb2 as match_pb
from clang_toolkit.call_graph import call_graph_request
from clang_toolkit.cli.runtime import EvaluationError, Runtime
from clang_toolkit.client import Client
from clang_toolkit._value_lifecycle import CursorOwner
from clang_toolkit.call_graph_values import CallGraph
from clang_toolkit.match_values import BindingSelection, MatchValue, ParsedTree

def test_native_defaults_and_explicit_false_are_distinct():
    plain = call_graph_request("file.cc")
    assert not plain.HasField("visit_implicit_code")
    assert not plain.HasField("visit_template_instantiations")
    request = call_graph_request("file.cc", visit_implicit_code=False, max_nodes=2)
    assert request.HasField("visit_implicit_code") and not request.visit_implicit_code
    assert request.max_nodes == 2
    with pytest.raises(ValueError):
        call_graph_request("file.cc", max_edges=0)

def test_callgraph_cli_returns_typed_nodes_and_visitation_options(tmp_path):
    client = Mock(spec=Client)
    response = pb.CallGraphResponse(is_complete=True)
    response.nodes.add(is_virtual_root=True)
    client.callgraph.return_value = response
    output = Runtime(client, cwd=tmp_path).execute('callgraph "file.cc" implicit false instantiations true nodes 8 edges 20 format json')
    assert json.loads(output)["nodes"][0]["is_virtual_root"]
    client.callgraph.assert_called_once_with("file.cc", working_directory=tmp_path,
        compile_arguments=[], visit_implicit_code=False, visit_template_instantiations=True,
        max_nodes=8, max_edges=20)


def test_raw_json_format_can_follow_graph_projection_options(tmp_path):
    client = Mock(spec=Client)
    client.callgraph.return_value = pb.CallGraphResponse(is_complete=True)
    output = Runtime(client, cwd=tmp_path).execute(
        'callgraph "file.cc" projection shallow main-file true format json')
    assert json.loads(output)["is_complete"] is True
    client.callgraph.assert_called_once_with(
        "file.cc", working_directory=tmp_path, compile_arguments=[],
        projection="shallow", main_file_only=True)


def test_standalone_callgraph_streams_compact_summary_after_completion(tmp_path):
    from clang_toolkit._generated.analysis.v1 import call_graph_stream_pb2 as stream_pb

    client = Mock(spec=Client)

    def stream(target, *, on_event, **kwargs):
        started = stream_pb.CallGraphStreamEvent()
        started.graph_started.graph.root_node = 0
        on_event(started)
        node = stream_pb.CallGraphStreamEvent()
        node.node.node.node_index = 1
        node.node.node.function.qualified_name = "pkg::f"
        node.node.node.function.type.spelling = "void ()"
        node.node.node.location.file = "file.cc"
        node.node.node.location.valid = True
        node.node.node.location.line = 8
        node.node.node.location.column = 2
        on_event(node)
        edge = stream_pb.CallGraphStreamEvent()
        edge.edge.edge.caller_node = 1
        edge.edge.edge.callee_node = 1
        on_event(edge)
        site = stream_pb.CallGraphStreamEvent()
        site.call_site.call_site.caller_node = 1
        site.call_site.call_site.callee_node = 1
        on_event(site)
        external = stream_pb.CallGraphStreamEvent()
        external.call_site.call_site.caller_node = 1
        external.call_site.call_site.facts.dispatch = match_pb.CALL_DISPATCH_DIRECT
        external.call_site.call_site.facts.static_callee_name = "header::f"
        on_event(external)
        completed = stream_pb.CallGraphStreamEvent()
        completed.completed.graph_count = 1
        completed.completed.node_count = 1
        completed.completed.edge_count = 1
        completed.completed.call_site_count = 2
        completed.completed.is_complete = True
        on_event(completed)
        return completed.completed

    client.stream_callgraph.side_effect = stream
    output = Runtime(client, cwd=tmp_path).execute('callgraph "file.cc"')
    assert output == (
        "Call graph: 1 functions, 1 calls, 2 call sites, 0 unresolved; complete\n"
        "  pkg::f void () @ file.cc:8:2: 2 call sites"
    )


def test_callgraph_wrapper_can_be_saved_as_plain_json(tmp_path):
    from google.protobuf.json_format import MessageToDict

    response = pb.CallGraphResponse(is_complete=True, snapshot_generation=12)
    response.nodes.add(node_index=0).function.qualified_name = "pkg::f"
    response.call_sites.add(caller_node=0)
    client = Mock(spec=Client)
    runtime = Runtime(client, cwd=tmp_path)
    runtime.bindings["incoming"] = CallGraph(response)

    runtime.execute('save $incoming to "incoming.json" as json')

    assert json.loads((tmp_path / "incoming.json").read_text()) == MessageToDict(
        response, preserving_proto_field_name=True
    )
    assert client.mock_calls == []
    client.callgraph.assert_not_called()


def test_standalone_callgraph_does_not_emit_summary_before_terminal_success(tmp_path):
    import grpc
    from clang_toolkit.analysis_error import AnalysisError

    client = Mock(spec=Client)
    client.stream_callgraph.side_effect = AnalysisError(
        grpc.StatusCode.CANCELLED, "stream cancelled")
    runtime = Runtime(client, cwd=tmp_path)
    with pytest.raises(AnalysisError, match="stream cancelled"):
        runtime.execute('callgraph "file.cc"')


def test_standalone_stream_enforces_active_resource_scope_completeness(tmp_path):
    from clang_toolkit._generated.analysis.v1 import call_graph_stream_pb2 as stream_pb
    from clang_toolkit.resources import ResourceError

    client = Mock(spec=Client)

    def stream(_target, *, on_event, **_kwargs):
        started = stream_pb.CallGraphStreamEvent()
        started.graph_started.graph.root_node = 0
        on_event(started)
        completed = stream_pb.CallGraphStreamEvent()
        completed.completed.graph_count = 1
        completed.completed.is_complete = False
        on_event(completed)
        return completed.completed

    client.stream_callgraph.side_effect = stream
    runtime = Runtime(client, cwd=tmp_path)
    runtime._active_resource_scope = object()
    with pytest.raises(ResourceError, match="CallGraphResponse result is incomplete"):
        runtime.execute('callgraph "file.cc"')

@pytest.mark.parametrize("options", ["nodes 18446744073709551616", "edges 1000001", "nodes 1 nodes 2"])
def test_invalid_options_stop_before_server_dispatch(tmp_path, options):
    client = Mock(spec=Client)
    with pytest.raises(EvaluationError):
        Runtime(client, cwd=tmp_path).execute(f'callgraph "file.cc" {options}')
    client.callgraph.assert_not_called()


@pytest.mark.parametrize("limit", [100001, 1 << 40, (1 << 64) - 1, 0, "all"])
def test_node_limit_can_exceed_the_old_ceiling_or_be_unlimited(limit):
    request = call_graph_request("file.cc", max_nodes=limit)
    assert request.HasField("max_nodes")
    assert request.max_nodes == (0 if limit == "all" else limit)
    assert not call_graph_request("file.cc").HasField("max_nodes")


@pytest.mark.parametrize("limit", [-1, True, False, 1.5, "unlimited", 1 << 64])
def test_node_limit_rejects_invalid_types_and_wire_overflow(limit):
    with pytest.raises(ValueError, match="max_nodes"):
        call_graph_request("file.cc", max_nodes=limit)


@pytest.mark.parametrize("option, expected", [("all", "all"), ("0", 0), ("100001", 100001)])
def test_console_accepts_configurable_and_unlimited_node_limits(tmp_path, option, expected):
    client = Mock(spec=Client)
    client.callgraph.return_value = pb.CallGraphResponse(is_complete=True)
    Runtime(client, cwd=tmp_path).execute(f'let graph = callgraph "file.cc" nodes {option}')
    assert client.callgraph.call_args.kwargs["max_nodes"] == expected


def test_console_exact_target_and_composable_local_graph_methods(tmp_path):
    client = Mock(spec=Client)
    response = pb.CallGraphResponse(root_node=99, is_complete=True)
    for index, name in ((0, "pkg::A"), (1, "pkg::B")):
        response.nodes.add(node_index=index).function.qualified_name = name
    response.edges.add(caller_node=0, callee_node=1)
    client.callgraph.return_value = response
    target = BindingSelection("fn", CursorOwner(client, "retained", 4, lambda _: None), 2)
    runtime = Runtime(client, cwd=tmp_path)
    runtime.bindings["target"] = target

    runtime.execute("let g = callgraph in $target")
    client.callgraph.assert_called_once_with(target, working_directory=tmp_path,
        compile_arguments=[])
    assert runtime.execute("$g.function(\"pkg::A\").function.qualified_name") == "pkg::A"
    runtime.execute("let out = $g.callees($target, 0)")
    assert client.callgraph.call_args.args[0] is target
    assert client.callgraph.call_args.kwargs["direction"] == "out"
    assert client.callgraph.call_args.kwargs["max_depth"] == 0
    assert runtime.execute("$g.recursive_components().length") == "0"
    runtime.close()


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_callgraph_in_accepts_retained_tree_and_path_in_both_engines(
        tmp_path, engine):
    from clang_toolkit.cli.app import dispatch_result
    from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
    from clang_toolkit.match_values import ParsedTree

    client = Mock(spec=Client)
    client.callgraph.return_value = pb.CallGraphResponse(is_complete=True)
    client.stream_callgraph.return_value = None
    runtime = PrototypeRuntime(client, cwd=tmp_path, script_engine=engine)
    tree = ParsedTree("fixture.cc", CursorOwner(client, "tree-session", 3, lambda _: None))
    runtime.bindings["tree"] = tree

    result = dispatch_result(client, "callgraph in $tree depth 0 direction both", runtime)
    assert result.success
    assert client.stream_callgraph.call_args.args[0] is tree
    assert client.stream_callgraph.call_args.kwargs["max_depth"] == 0
    assert client.stream_callgraph.call_args.kwargs["direction"] == "both"

    result = dispatch_result(client, 'callgraph in "fixture.cc"', runtime)
    assert result.success
    assert client.stream_callgraph.call_args.args[0] == "fixture.cc"
    assert "max_depth" not in client.stream_callgraph.call_args.kwargs
    assert "direction" not in client.stream_callgraph.call_args.kwargs
    result = dispatch_result(client, "callgraph in $tree depth all", runtime)
    assert result.success
    assert client.stream_callgraph.call_args.kwargs["max_depth"] == "all"
    for option, expected in (("all", "all"), ("100001", 100001),
                             ("18446744073709551615", (1 << 64) - 1)):
        result = dispatch_result(client, f"callgraph in $tree nodes {option}", runtime)
        assert result.success
        assert client.stream_callgraph.call_args.kwargs["max_nodes"] == expected
    runtime.close()


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_graph_binding_lookup_composes_with_local_callees(tmp_path, engine):
    from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
    from clang_toolkit._generated.match.v1 import match_service_pb2

    client = Mock(spec=Client)
    response = pb.CallGraphResponse(root_node=0, is_complete=True, snapshot_generation=9)
    response.nodes.add(node_index=0, is_virtual_root=True)
    function = response.nodes.add(node_index=1)
    function.function.qualified_name = "pkg::f"
    function.symbol_identity = "usr:pkg::f"
    client.callgraph.return_value = response
    runtime = PrototypeRuntime(client, cwd=tmp_path, script_engine=engine)
    tree_owner = CursorOwner(client, "tree-session", 2, lambda _: None)
    runtime.bindings["tree"] = ParsedTree("fixture.cc", tree_owner)
    match_response = match_service_pb2.MatchResponse()
    match_response.results.add().bindings["f"].symbol_identity = "usr:pkg::f"
    match_owner = CursorOwner(client, "match-session", 1, lambda _: None)
    runtime.bindings["functions"] = MatchValue._from_response(
        match_response, match_owner)

    runtime.execute("let g = callgraph in $tree")
    runtime.execute("let submit = $g.function($functions[0].f)")
    runtime.execute("let outgoing = $g.callees($submit, depth=0)")
    assert isinstance(runtime.bindings["g"], CallGraph)
    assert runtime.bindings["submit"].node_index == 1
    assert isinstance(runtime.bindings["outgoing"], CallGraph)
    client.callgraph.assert_called_once_with(
        runtime.bindings["tree"], working_directory=tmp_path,
        compile_arguments=[])
    runtime.close()


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_console_exposes_shortest_route_and_grouped_call_rows(tmp_path, engine):
    from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime

    client = Mock(spec=Client)
    response = pb.CallGraphResponse(root_node=0, is_complete=True)
    response.nodes.add(node_index=0, is_virtual_root=True)
    response.nodes.add(node_index=1).function.qualified_name = "pkg::f"
    response.nodes.add(node_index=2).function.qualified_name = "pkg::g"
    response.edges.add(caller_node=1, callee_node=2)
    response.call_sites.add(caller_node=1, callee_node=2)
    client.callgraph.return_value = response
    runtime = PrototypeRuntime(client, cwd=tmp_path, script_engine=engine)
    runtime.bindings["tree"] = ParsedTree(
        "fixture.cc", CursorOwner(client, "tree-session", 4, lambda _: None)
    )

    runtime.execute("let graph = callgraph in $tree")
    runtime.execute('let route = $graph.shortest_route("pkg::f", "pkg::g")')
    runtime.execute("let groups = $graph.grouped_calls()")
    assert runtime.execute("$route.length") == "1"
    assert runtime.execute("$route[0].caller.function.qualified_name") == "pkg::f"
    assert runtime.execute("$route[0].call_sites.length") == "1"
    assert runtime.execute("$groups.length") == "1"
    assert runtime.execute("$groups[0].caller.function.qualified_name") == "pkg::f"
    assert runtime.execute("$groups[0].call_site_count") == "1"
    assert runtime.execute("$groups[0].unresolved_count") == "0"
    runtime.close()


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_callgraph_function_rejects_named_arguments(tmp_path, engine):
    from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime

    client = Mock(spec=Client)
    response = pb.CallGraphResponse(root_node=99, is_complete=True)
    response.nodes.add(node_index=0).function.qualified_name = "pkg::f"
    client.callgraph.return_value = response
    runtime = PrototypeRuntime(client, cwd=tmp_path, script_engine=engine)
    runtime.bindings["tree"] = ParsedTree(
        "fixture.cc", CursorOwner(client, "tree-session", 1, lambda _: None)
    )
    runtime.execute("let graph = callgraph in $tree")

    with pytest.raises(EvaluationError, match="does not accept named arguments"):
        runtime.execute('let selected = $graph.function(name="pkg::f")')

    runtime.close()
