"""Graph values compose independently of native candidate/projection budgets."""
from unittest.mock import Mock

import pytest
from clang_toolkit._generated.analysis.v1 import call_graph_response_pb2, cfg_response_pb2, traverse_response_pb2
from clang_toolkit._generated.analysis.v1.value_projection_pb2 import ValueProjection
from clang_toolkit.call_graph import call_graph_request
from clang_toolkit.cli.runtime import EvaluationError, Runtime
from clang_toolkit.client import Client
from clang_toolkit.control_flow import cfg_request
from clang_toolkit.traversal import traversal_request


@pytest.mark.parametrize("make", [lambda: traversal_request("a.cc"), lambda: call_graph_request("a.cc"), lambda: cfg_request("a.cc", "f")])
def test_graph_default_projection_is_explicitly_shallow(make):
    assert make().projection.mode == ValueProjection.SHALLOW


@pytest.mark.parametrize("make", [traversal_request, call_graph_request])
def test_graph_projection_limits_are_distinct_from_graph_node_limit(make):
    request = make("a.cc", max_nodes=3, projection="recursive", payload_depth=2, payload_nodes=7, main_file_only=True)
    assert request.max_nodes == 3
    assert request.projection.mode == ValueProjection.RECURSIVE
    assert request.projection.max_depth == 2 and request.projection.max_nodes == 7
    assert request.main_file_only
    for options in [dict(projection="guess"), dict(payload_depth=0), dict(payload_nodes=0)]:
        with pytest.raises(ValueError):
            make("a.cc", **options)


def test_graph_assignment_and_foreach_read_typed_fields(tmp_path):
    client = Mock(spec=Client)
    response = traverse_response_pb2.TraverseResponse(depth_limited=True)
    response.nodes.add(depth=0)
    response.nodes.add(depth=1)
    client.traverse.return_value = response
    runtime = Runtime(client, cwd=tmp_path)
    runtime.evaluate('let graph = traverse "a.cc" depth 1 projection shallow main-file true payload-depth 2 payload-nodes 7')
    assert runtime.evaluate('$graph.nodes.length') == 2
    assert runtime.evaluate('foreach $n in $graph.nodes do $n.depth done') == [0, 1]
    assert runtime.evaluate('$graph.depth_limited') is True
    client.traverse.assert_called_once_with('a.cc', working_directory=tmp_path, compile_arguments=[], max_depth=1, projection='shallow', main_file_only=True, payload_depth=2, payload_nodes=7)


def test_callgraph_and_cfg_values_preserve_typed_relation_fields(tmp_path):
    client = Mock(spec=Client)
    calls = call_graph_response_pb2.CallGraphResponse(is_complete=True, main_file_only=True, external_edges_omitted=2)
    calls.nodes.add(node_index=0, is_virtual_root=True)
    calls.edges.add(caller_node=0, callee_node=1)
    client.callgraph.return_value = calls
    cfg = cfg_response_pb2.CfgResponse()
    cfg.graphs.add(entry_block=3, exit_block=0).blocks.add(block_index=3)
    client.cfg.return_value = cfg
    runtime = Runtime(client, cwd=tmp_path)
    runtime.evaluate('let calls = callgraph "a.cc" main-file true')
    assert runtime.evaluate('$calls.external_edges_omitted') == 2
    assert runtime.evaluate('$calls.edges[0].callee_node') == 1
    runtime.evaluate('let flows = cfg ns::f in "a.cc" projection shallow')
    assert runtime.evaluate('$flows.graphs[0].blocks[0].block_index') == 3
    assert client.cfg.call_args.args == ('ns::f',)


@pytest.mark.parametrize("suffix", ['projection unknown', 'payload-depth 0', 'payload-nodes 100001', 'projection shallow projection recursive'])
def test_invalid_graph_projection_stops_before_rpc(tmp_path, suffix):
    client = Mock(spec=Client)
    with pytest.raises(EvaluationError):
        Runtime(client, cwd=tmp_path).execute('traverse "a.cc" '+suffix)
    client.traverse.assert_not_called()
