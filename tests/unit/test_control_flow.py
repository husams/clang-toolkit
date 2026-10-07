"""Typed CFG options, validated limits and formal command evaluation."""
from __future__ import annotations
import json
from unittest.mock import Mock
import pytest
from clang_toolkit._generated.analysis.v1 import cfg_response_pb2 as pb
from clang_toolkit.control_flow import CfgOptions, cfg_request
from clang_toolkit.client import Client
from clang_toolkit.cli.runtime import EvaluationError, Runtime

def test_cfg_options_keep_native_default_and_explicit_false(tmp_path):
    plain = cfg_request("file.cc", "ns::f", working_directory=tmp_path)
    assert not plain.options.HasField("prune_trivially_false_edges")
    request = cfg_request("file.cc", "ns::f", options=CfgOptions(
        prune_trivially_false_edges=False, add_scopes=True), max_blocks=2)
    assert request.options.HasField("prune_trivially_false_edges")
    assert not request.options.prune_trivially_false_edges
    assert request.options.add_scopes and request.max_blocks == 2
    with pytest.raises(ValueError):
        cfg_request("file.cc", "f", max_functions=0)
    with pytest.raises(ValueError):
        cfg_request("file.cc", "")

def test_cfg_cli_returns_typed_graph_and_selected_options(tmp_path):
    client = Mock(spec=Client)
    result = pb.CfgResponse()
    result.graphs.add(entry_block=1).blocks.add(block_index=1)
    client.cfg.return_value = result
    runtime = Runtime(client, cwd=tmp_path)
    output = runtime.execute('cfg ns::f in "fixture.cc" option prune_trivially_false_edges false option add_rich_cxx_constructors true blocks 9')
    assert json.loads(output)["graphs"][0]["entry_block"] == "1"
    args, kwargs = client.cfg.call_args
    assert args == ("ns::f",)
    assert kwargs["path"] == "fixture.cc" and kwargs["max_blocks"] == 9
    assert kwargs["options"].HasField("prune_trivially_false_edges")
    assert not kwargs["options"].prune_trivially_false_edges
    assert kwargs["options"].add_rich_cxx_constructors
    assert kwargs["working_directory"] == tmp_path

@pytest.mark.parametrize("options", ["blocks 0", "elements 1000001", "blocks 2 blocks 3", "option bad true", "option add_scopes true option add_scopes false"])
def test_cfg_invalid_cli_limits_do_not_reach_server(tmp_path, options):
    client = Mock(spec=Client)
    with pytest.raises(EvaluationError):
        Runtime(client, cwd=tmp_path).execute(f'cfg f in "fixture.cc" {options}')
    client.cfg.assert_not_called()
