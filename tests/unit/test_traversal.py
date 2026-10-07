"""Standalone traversal option presence and formal CLI integration."""
from __future__ import annotations
import json
from unittest.mock import Mock
import pytest
from clang_toolkit._generated.analysis.v1 import traverse_response_pb2 as pb
from clang_toolkit.cli.runtime import EvaluationError, Runtime
from clang_toolkit.client import Client
from clang_toolkit.traversal import traversal_request

def test_explicit_depth_zero_and_native_options_preserve_presence(tmp_path):
    request = traversal_request("fixture.cc", working_directory=tmp_path,
        compile_arguments=["-std=c++23"], max_depth=0, max_nodes=3,
        visit_implicit_code=True, visit_template_instantiations=True)
    assert request.HasField("max_depth") and request.max_depth == 0
    assert request.max_nodes == 3
    assert request.visit_implicit_code and request.visit_template_instantiations
    assert request.file.working_directory == str(tmp_path)
    assert list(request.file.compile_arguments) == ["-std=c++23"]
    assert not traversal_request("fixture.cc").HasField("max_depth")
    with pytest.raises(ValueError):
        traversal_request("fixture.cc", max_nodes=0)

def test_traversal_cli_emits_typed_response_and_compiler_options(tmp_path):
    client = Mock(spec=Client)
    response = pb.TraverseResponse(depth_limited=True)
    response.nodes.add(depth=0).value.node.translation_unit_decl.SetInParent()
    client.traverse.return_value = response
    runtime = Runtime(client, cwd=tmp_path)
    output = runtime.execute('traverse "fixture.cc" depth 0 nodes 9 implicit true instantiations false')
    assert json.loads(output)["depth_limited"] is True
    client.traverse.assert_called_once_with("fixture.cc", working_directory=tmp_path,
        compile_arguments=[], max_depth=0, max_nodes=9, visit_implicit_code=True,
        visit_template_instantiations=False)

@pytest.mark.parametrize("options", ["nodes 0", "depth 257", "depth 1 depth 2"])
def test_invalid_traversal_options_do_not_reach_server(tmp_path, options):
    client = Mock(spec=Client)
    with pytest.raises(EvaluationError):
        Runtime(client, cwd=tmp_path).execute(f'traverse "fixture.cc" {options}')
    client.traverse.assert_not_called()
