"""Call-graph option presence and grammar-driven client dispatch."""
from __future__ import annotations
import json
from unittest.mock import Mock
import pytest
from clang_toolkit._generated.analysis.v1 import call_graph_response_pb2 as pb
from clang_toolkit.call_graph import call_graph_request
from clang_toolkit.cli.runtime import EvaluationError, Runtime
from clang_toolkit.client import Client

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
    output = Runtime(client, cwd=tmp_path).execute('callgraph "file.cc" implicit false instantiations true nodes 8 edges 20')
    assert json.loads(output)["nodes"][0]["is_virtual_root"]
    client.callgraph.assert_called_once_with("file.cc", working_directory=tmp_path,
        compile_arguments=[], visit_implicit_code=False, visit_template_instantiations=True,
        max_nodes=8, max_edges=20)

@pytest.mark.parametrize("options", ["nodes 0", "edges 1000001", "nodes 1 nodes 2"])
def test_invalid_options_stop_before_server_dispatch(tmp_path, options):
    client = Mock(spec=Client)
    with pytest.raises(EvaluationError):
        Runtime(client, cwd=tmp_path).execute(f'callgraph "file.cc" {options}')
    client.callgraph.assert_not_called()
