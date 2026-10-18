"""Call graphs share matcher value display and inspection without losing ownership."""

from __future__ import annotations

import json

import pytest

from clang_toolkit._generated.analysis.v1 import call_graph_response_pb2
from clang_toolkit._generated.ast.v1 import common_pb2
from clang_toolkit._value_lifecycle import CursorOwner
from clang_toolkit.call_graph_values import CallGraph
from clang_toolkit.cli.runtime.prototype.filters import make_filters
from clang_toolkit.cli.runtime.prototype.semantics import Context
from clang_toolkit.cli.runtime.references import inspect_value
from clang_toolkit.cli.runtime.values import render, render_inspection


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
    assert "availability" not in displayed["nodes"][1]
    assert not {"type", "active_oneof", "methods"} & displayed.keys()
    assert value.proto.SerializeToString() == before
    assert value.nodes[1].binding._owner is value._owner


@pytest.mark.parametrize("select_node", [False, True])
def test_graph_and_node_pretty_use_structured_fields(select_node):
    value = graph()
    selected = value.nodes[1] if select_node else value
    pretty = make_filters(Context())["pretty"]

    displayed = pretty(selected)

    assert '"qualified_name": "project::work"' in displayed
    assert "\n" in displayed
    assert "object at 0x" not in displayed
    assert "CallGraphNodeValue(" not in displayed


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
    assert "project::work" in inspected
    assert nodes[1]["value"]["fields"]["function"]["fields"]["qualified_name"] == "project::work"
    assert nodes[-1] == {"truncated": 20}
    assert len(value.nodes) == 40
    assert value.proto.SerializeToString() == before
