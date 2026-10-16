"""Reusable local queries over a collected static call graph."""

from __future__ import annotations

import pytest

from clang_toolkit._generated.analysis.v1 import call_graph_response_pb2 as pb
from clang_toolkit._generated.match.v1 import match_result_pb2
from clang_toolkit._value_lifecycle import CursorOwner
from clang_toolkit.call_graph_values import CallGraph, CallGraphError
from clang_toolkit.match_values import BindingSelection


def graph() -> CallGraph:
    response = pb.CallGraphResponse(root_node=0, is_complete=False)
    for index, qualified_name, signature in [
        (0, "", ""),
        (1, "pkg::A", "void ()"),
        (2, "pkg::B", "void (int)"),
        (3, "pkg::C", "void ()"),
        (4, "pkg::D", "void ()"),
        (5, "pkg::B", "void (double)"),
    ]:
        node = response.nodes.add(node_index=index, is_virtual_root=index == 0)
        if index:
            node.function.qualified_name = qualified_name
            node.function.type.spelling = signature
    for caller, callee in [
        (0, 1),
        (1, 2),
        (1, 2),
        (2, 3),
        (3, 1),
        (3, 4),
        (0, 5),
    ]:
        response.edges.add(
            caller_node=caller, callee_node=callee, is_virtual_root_edge=caller == 0
        )
    response.call_sites.add(caller_node=1)
    response.call_sites.add(caller_node=1, callee_node=2)
    return CallGraph(response)


def test_bounded_neighborhood_excludes_synthetic_root_and_keeps_edge_multiplicity():
    value = graph()
    outgoing = value.callees("pkg::A", depth=2)
    assert {node.function.qualified_name for node in outgoing.nodes} == {
        "pkg::A",
        "pkg::B",
        "pkg::C",
    }
    assert [(edge.caller_node, edge.callee_node) for edge in outgoing.edges] == [
        (0, 1),
        (0, 1),
        (1, 2),
    ]
    assert [
        (node.node_index, node.function.qualified_name) for node in outgoing.nodes
    ] == [
        (0, "pkg::A"),
        (1, "pkg::B"),
        (2, "pkg::C"),
    ]
    assert len(outgoing.call_sites) == 2
    assert outgoing.call_sites[0].caller_node == 0
    incoming = value.callers("pkg::D", depth=2)
    assert {node.function.qualified_name for node in incoming.nodes} == {
        "pkg::B",
        "pkg::C",
        "pkg::D",
    }
    assert all(not edge.is_virtual_root_edge for edge in incoming.edges)
    only = value.callees("pkg::A", depth=0)
    assert [(node.node_index, node.function.qualified_name) for node in only.nodes] == [
        (0, "pkg::A")
    ]
    assert not only.edges
    assert not only.call_sites
    assert only.selection_boundary_call_sites == 2
    with pytest.raises(ValueError, match="depth"):
        value.callees("pkg::A", depth=33)


def test_unlimited_local_neighborhood_is_cycle_safe_and_keeps_partial_coverage():
    response = pb.CallGraphResponse(
        root_node=0,
        is_complete=True,
        external_edges_omitted=2,
        selection_boundary_edges=3,
        selection_boundary_call_sites=4,
    )
    response.nodes.add(node_index=0, is_virtual_root=True)
    for index in range(1, 38):
        response.nodes.add(node_index=index).function.qualified_name = f"f{index}"
    response.nodes.add(node_index=38).function.qualified_name = "disconnected"
    for index in range(1, 37):
        response.edges.add(caller_node=index, callee_node=index + 1)
        response.call_sites.add(caller_node=index, callee_node=index + 1)
    response.edges.add(caller_node=37, callee_node=2)
    response.edges.add(caller_node=1, callee_node=2)
    response.call_sites.add(caller_node=37, callee_node=2)
    response.call_sites.add(caller_node=1, callee_node=2)

    selected = CallGraph(response).callees("f1", depth="all")
    names = {node.function.qualified_name for node in selected.nodes}
    assert len(selected.nodes) == 37
    assert "f37" in names and "disconnected" not in names
    assert len(selected.edges) == 38
    assert len(selected.call_sites) == 38
    assert selected.selection_unlimited_depth
    assert not selected.HasField("selection_max_depth")
    assert selected.external_edges_omitted == 2
    assert selected.selection_boundary_edges == 3
    assert selected.selection_boundary_call_sites == 4

    partial = CallGraph(response).callees("f1", depth=1)
    expanded = partial.callees(0, depth="all")
    assert {node.function.qualified_name for node in expanded.nodes} == {"f1", "f2"}
    assert expanded.selection_boundary_edges == partial.selection_boundary_edges
    assert expanded.selection_boundary_call_sites == partial.selection_boundary_call_sites
    assert expanded.external_edges_omitted == partial.external_edges_omitted


def test_function_lookup_requires_an_overload_disambiguator():
    value = graph()
    with pytest.raises(CallGraphError, match="ambiguous"):
        value.function("pkg::B")
    selected = value.function("pkg::B", signature="void (double)")
    assert selected.node_index == 5
    assert value.function("pkg::A").node_index == 1


def test_local_neighborhood_rejects_node_from_another_graph_at_same_index():
    value = graph()
    other_response = pb.CallGraphResponse(root_node=99)
    other = other_response.nodes.add(node_index=1)
    other.function.qualified_name = "different::function"

    with pytest.raises(CallGraphError, match="does not belong to this call graph"):
        value.callees(other)


def test_grouped_call_classifies_scoped_out_direct_targets_and_indirect_sites():
    response = pb.CallGraphResponse(root_node=0)
    response.nodes.add(node_index=0, is_virtual_root=True)
    response.nodes.add(node_index=1).function.qualified_name = "pkg::caller"
    direct = response.call_sites.add(caller_node=1)
    direct.facts.dispatch = match_result_pb2.CALL_DISPATCH_DIRECT
    direct.facts.static_callee_name = "header::direct"
    virtual = response.call_sites.add(caller_node=1)
    virtual.facts.dispatch = match_result_pb2.CALL_DISPATCH_VIRTUAL
    virtual.facts.static_callee_name = "header::virtual"
    indirect = response.call_sites.add(caller_node=1)
    indirect.facts.dispatch = match_result_pb2.CALL_DISPATCH_INDIRECT
    response.call_sites.add(caller_node=1)

    grouped = CallGraph(response).grouped_calls()
    assert len(grouped) == 1
    assert grouped[0].call_site_count == 4
    assert grouped[0].unresolved_count == 2


def test_binding_lookup_resolves_local_node_for_composable_neighborhoods():
    value = graph()
    selected = match_result_pb2.MatchBinding(symbol_identity="usr:pkg::A")
    value.response.nodes[1].symbol_identity = selected.symbol_identity
    binding = BindingSelection(
        "f",
        CursorOwner(object(), "session", 1, lambda _: None),
        0,
        _binding_data=selected.SerializeToString(),
    )

    function = value.function(binding)
    assert function.node_index == 1
    outgoing = value.callees(function, depth=0)
    assert [node.node_index for node in outgoing.nodes] == [0]


def test_shortest_path_and_recursion_components_are_bounded_and_cycle_safe():
    value = graph()
    assert [node.node_index for node in value.shortest_path("pkg::A", "pkg::D")] == [
        1,
        2,
        3,
        4,
    ]
    assert value.shortest_path(4, "pkg::A") is None
    components = value.recursive_components()
    assert [[node.node_index for node in component] for component in components] == [
        [1, 2, 3]
    ]
    assert not value.is_complete
    route = value.shortest_route("pkg::A", "pkg::D")
    assert [len(step.call_sites) for step in route] == [1, 0, 0]
    grouped = value.grouped_calls()
    assert any(
        item.caller.node_index == 1
        and item.callee is None
        and item.call_site_count == 1
        and item.unresolved_count == 1
        for item in grouped
    )
    assert any(
        item.caller.node_index == 1
        and item.callee is not None
        and item.callee.node_index == 2
        and item.call_site_count == 1
        for item in grouped
    )


def test_local_queries_keep_source_metadata_and_handle_long_chains_iteratively():
    response = pb.CallGraphResponse(
        root_node=0,
        is_complete=False,
        snapshot_generation=42,
        selection_boundary_edges=7,
    )
    response.nodes.add(node_index=0, is_virtual_root=True)
    count = 10_000
    for index in range(1, count + 1):
        response.nodes.add(node_index=index).function.qualified_name = f"f{index}"
    for index in range(1, count):
        response.edges.add(caller_node=index, callee_node=index + 1)
        response.call_sites.add(caller_node=index, callee_node=index + 1)
    original = pb.CallGraphResponse()
    original.CopyFrom(response)
    value = CallGraph(response)

    path = value.shortest_path("f1", f"f{count}")
    assert len(path) == count
    route = value.shortest_route("f1", f"f{count}")
    assert len(route) == count - 1
    assert all(len(step.call_sites) == 1 for step in route)
    assert value.recursive_components() == ()
    focused = value.callers(f"f{count}", depth=0)
    assert len(focused.nodes) == 1 and not focused.edges
    assert focused.root_node == (1 << 64) - 1
    assert focused.focus_node == 0
    assert focused.selection_max_depth == 0
    assert focused.selection_boundary_edges == 8
    assert focused.snapshot_generation == 42
    assert response == original


def test_neighborhood_recomputes_coverage_from_retained_records_only():
    response = pb.CallGraphResponse(root_node=0, is_complete=False)
    response.availability.add(field_path="graph.stale")
    response.nodes.add(node_index=0, is_virtual_root=True)
    included = response.nodes.add(node_index=1, is_complete=True)
    included.function.qualified_name = "pkg::A"
    included.availability.add(field_path="included.fact")
    excluded = response.nodes.add(node_index=2, is_complete=False)
    excluded.function.qualified_name = "pkg::B"
    excluded.availability.add(field_path="excluded.fact")
    response.edges.add(caller_node=1, callee_node=2, is_complete=False)
    response.edges[-1].availability.add(field_path="excluded-edge.fact")

    focused = CallGraph(response).callees("pkg::A", depth=0)
    assert focused.HasField("is_complete") and focused.is_complete
    assert [entry.field_path for entry in focused.availability] == ["included.fact"]
    assert [node.function.qualified_name for node in focused.nodes] == ["pkg::A"]
    assert not focused.edges
