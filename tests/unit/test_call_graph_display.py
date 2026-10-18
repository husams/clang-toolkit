"""Call graphs share matcher value display and inspection without losing ownership."""

from __future__ import annotations

import json

import pytest

from clang_toolkit._generated.analysis.v1 import call_graph_response_pb2
from clang_toolkit._generated.analysis.v1 import call_graph_request_pb2
from clang_toolkit._generated.ast.v1 import common_pb2
from clang_toolkit._value_lifecycle import CursorOwner
from clang_toolkit.call_graph_values import CallGraph
from clang_toolkit.cli.runtime.prototype.filters import make_filters
from clang_toolkit.cli.runtime.prototype.semantics import Context
from clang_toolkit.cli.runtime.references import inspect_value
from clang_toolkit.cli.runtime.semantic import (
    inspect_value as inspect_semantic_value,
    view as semantic_view,
)
from clang_toolkit.cli.runtime.values import render, render_inspection
from google.protobuf.json_format import MessageToDict


def graph(*, retained: bool = True) -> CallGraph:
    response = call_graph_response_pb2.CallGraphResponse(
        source_file="example.cc", is_complete=False,
    )
    response.nodes.add(is_virtual_root=True, is_complete=True)
    work = response.nodes.add(node_index=1, native_match_index=7, is_complete=True)
    work.function.qualified_name = "project::work"
    work.availability.add(
        field_path="CallGraphNode.location",
        state=common_pb2.FIELD_STATE_UNREQUESTED,
        reason="location omitted by this projection",
    )
    response.edges.add(caller_node=0, callee_node=1, is_virtual_root_edge=True)
    owner = CursorOwner(object(), "callables", 1, lambda _: None) if retained else None
    return CallGraph(response, owner=owner)


def test_graph_prints_bounded_semantic_fields_without_inspection_wrappers():
    value = graph()
    before = value.proto.SerializeToString()

    displayed = json.loads(render(value))

    assert displayed["is_complete"] is False
    assert displayed["nodes"][0]["is_virtual_root"] is True
    assert displayed["nodes"][1]["function"]["qualified_name"] == "project::work"
    assert displayed["nodes"][1]["availability"][0]["state"] == "FIELD_STATE_UNREQUESTED"
    assert displayed["nodes"][1]["availability"][0]["reason"] == "location omitted by this projection"
    assert not {"type", "active_oneof", "methods"} & displayed.keys()
    assert value.proto.SerializeToString() == before
    assert value.nodes[1].binding._owner is value._owner


def test_graph_and_node_print_match_protobuf_json_scalar_and_presence_contracts():
    value = graph()
    response = value.proto
    response.root_node = 2**64 - 1
    response.focus_node = 2**64 - 1
    response.selection_direction = call_graph_request_pb2.CALL_GRAPH_DIRECTION_IN
    response.nodes[1].node_index = 2**64 - 1
    response.nodes[1].native_match_index = 2**64 - 1
    response.nodes[1].is_complete = False
    response.nodes[1].location.offset = 2**64 - 1

    graph_display = json.loads(render(value))
    node_display = json.loads(render(value.nodes[1]))

    assert graph_display == MessageToDict(response, preserving_proto_field_name=True)
    assert node_display == MessageToDict(response.nodes[1], preserving_proto_field_name=True)
    assert graph_display["root_node"] == str(2**64 - 1)
    assert graph_display["focus_node"] == str(2**64 - 1)
    assert graph_display["nodes"][1]["node_index"] == str(2**64 - 1)
    assert graph_display["nodes"][1]["native_match_index"] == str(2**64 - 1)
    assert graph_display["nodes"][1]["location"]["offset"] == str(2**64 - 1)
    assert graph_display["selection_direction"] == "CALL_GRAPH_DIRECTION_IN"
    assert graph_display["nodes"][1]["is_complete"] is False
    assert " at 0x" not in render(value)
    assert " at 0x" not in render(value.nodes[1])


@pytest.mark.parametrize("select_node", [False, True])
def test_graph_and_node_pretty_use_structured_fields(select_node):
    value = graph()
    value.proto.nodes[1].node_index = 2**64 - 1
    value.proto.nodes[1].location.offset = 2**64 - 1
    selected = value.nodes[1] if select_node else value
    pretty = make_filters(Context())["pretty"]

    displayed = pretty(selected)
    payload = json.loads(displayed)

    assert '"qualified_name": "project::work"' in displayed
    assert "\n" in displayed
    assert "object at 0x" not in displayed
    assert "CallGraphNodeValue(" not in displayed
    node_payload = payload if select_node else payload["nodes"][1]
    assert node_payload["node_index"] == str(2**64 - 1)
    assert node_payload["location"]["offset"] == str(2**64 - 1)
    assert node_payload["availability"][0]["state"] == "FIELD_STATE_UNREQUESTED"


def test_graph_inspection_exposes_schema_and_existing_console_operations():
    value = graph()

    inspected = inspect_value(value)

    assert inspected["type"] == "CallGraph"
    assert inspected["node_count"] == 2
    assert inspected["is_complete"] is False
    assert inspected["retained"] is True
    assert inspected["value"]["type"] == "ctk.analysis.v1.CallGraphResponse"
    assert {"nodes", "edges", "is_complete"} <= inspected["value"]["fields"].keys()
    assert {"function", "grouped_calls", "shortest_route", "callees"} <= set(inspected["methods"])


@pytest.mark.parametrize("select_node", [False, True])
def test_call_graph_inspection_uses_default_semantic_inspector_depth(select_node):
    value = graph()
    value.proto.nodes[1].function.type.spelling = "project::return_type"
    value.proto.nodes[1].function.function.return_type.spelling = "project::return_type"
    selected = value.nodes[1].proto if select_node else value.proto

    inspected = inspect_value(value.nodes[1] if select_node else value)

    if select_node:
        assert inspected["value"] == inspect_semantic_value(semantic_view(selected))
        assert inspected["value"]["fields"]["function"]["fields"]["type"]["fields"]["spelling"] == "project::return_type"
        assert inspected["value"]["fields"]["function"]["fields"]["function"]["fields"]["return_type"] == {
            "type": "ctk.ast.v1.TypeDescription",
            "truncated": True,
        }
    else:
        standalone = inspect_value(value.nodes[1])["value"]
        graph_node = inspected["value"]["fields"]["nodes"][1]
        assert graph_node["fields"]["function"] == standalone["fields"]["function"]
        assert graph_node["fields"]["function"]["fields"]["type"]["fields"]["spelling"] == "project::return_type"
        assert graph_node["fields"]["function"]["fields"]["function"]["fields"]["return_type"] == {
            "type": "ctk.ast.v1.TypeDescription",
            "truncated": True,
        }


def test_graph_inspection_gives_each_node_default_depth_with_present_location():
    value = graph()
    value.proto.nodes[1].availability.clear()
    value.proto.nodes[1].location.file = "example.cc"
    value.proto.nodes[1].location.line = 12
    value.proto.nodes[1].location.column = 4
    value.proto.nodes[1].function.type.spelling = "project::return_type"
    value.proto.nodes[1].function.function.return_type.spelling = "project::return_type"

    graph_inspection = inspect_value(value)
    nodes_inspection = graph_inspection["value"]["fields"]["nodes"]
    standalone_node = inspect_value(value.nodes[1])["value"]

    graph_node = nodes_inspection[1]
    assert graph_node["fields"]["function"] == standalone_node["fields"]["function"]
    assert graph_node["fields"]["location"] == standalone_node["fields"]["location"]
    assert graph_node["fields"]["function"]["fields"]["qualified_name"] == "project::work"
    assert graph_node["fields"]["function"]["fields"]["type"]["fields"]["spelling"] == "project::return_type"
    assert graph_node["fields"]["function"]["fields"]["function"]["fields"]["return_type"] == {
        "type": "ctk.ast.v1.TypeDescription",
        "truncated": True,
    }
    assert graph_node["fields"]["location"]["fields"]["file"] == "example.cc"
    assert graph_node["fields"]["location"]["fields"]["line"] == 12
    rendered = json.loads(render_inspection(value))
    rendered_node = rendered["value"]["fields"]["nodes"][1]
    assert rendered_node["fields"]["function"]["fields"]["qualified_name"] == "project::work"
    assert rendered_node["fields"]["location"]["fields"]["file"] == "example.cc"
    assert rendered_node["fields"]["function"]["fields"]["function"]["fields"]["return_type"] == {
        "type": "ctk.ast.v1.TypeDescription",
        "truncated": True,
    }


@pytest.mark.parametrize("state", ["live", "detached", "closed", "root"])
def test_node_inspection_keeps_semantic_availability_and_local_retention_state(state):
    value = graph(retained=state != "detached")
    if state == "closed":
        value._owner.close()
    selected = value.nodes[0] if state == "root" else value.nodes[1]

    inspected = inspect_value(selected)

    assert inspected["type"] == "CallGraphNodeValue"
    assert inspected["retained"] is (state == "live")
    fields = inspected["value"]["fields"]
    if state != "root":
        assert fields["function"]["fields"]["qualified_name"] == "project::work"
        assert "location" not in fields
        availability = fields["availability"][0]["fields"]
        assert availability["state"]["name"] == "FIELD_STATE_UNREQUESTED"
        assert availability["reason"] == "location omitted by this projection"


def test_graph_preview_limits_do_not_truncate_the_stored_graph_or_nodes():
    value = graph()
    for index in range(2, 40):
        value.proto.nodes.add(node_index=index).function.qualified_name = f"project::f{index}"
    value = CallGraph(value.proto, owner=value._owner)
    before = value.proto.SerializeToString()

    displayed = render(value)
    inspected = render_inspection(value)
    nodes = inspect_value(value.nodes)

    assert len(displayed) <= 20_000
    assert len(inspected) <= 20_000
    assert json.loads(inspected)["type"] == "CallGraph"
    assert "truncated" in displayed
    assert "project::work" in displayed
    assert json.loads(inspected)["node_count"] == 40
    graph_nodes = inspect_value(value)["value"]["fields"]["nodes"]
    assert len(graph_nodes) == 21
    assert graph_nodes[-1] == {"truncated": 20}
    assert nodes[1]["value"]["fields"]["function"]["fields"]["qualified_name"] == "project::work"
    assert nodes[-1] == {"truncated": 20}
    assert len(value.nodes) == 40
    assert value.proto.SerializeToString() == before
