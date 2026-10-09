from __future__ import annotations

import pytest
import json

from clang_toolkit._generated.ast.v1 import common_pb2, semantic_pb2, semantic_types_pb2
from clang_toolkit._generated.match.v1 import match_result_pb2, match_service_pb2
from clang_toolkit._value_lifecycle import CursorOwner
from clang_toolkit.cli.runtime.references import (
    ReferenceError,
    call_method,
    field_names,
    index_value,
    inspect_value,
    property_value,
)
from clang_toolkit.match_values import MatchValue
from clang_toolkit.cli.runtime.values import render
from clang_toolkit.cli.runtime.semantic import (
    display_value,
    inspect_value as inspect_semantic_value,
    view as semantic_view,
)


def _collection(row: match_result_pb2.MatchResult) -> tuple[MatchValue[object], CursorOwner[object]]:
    owner = CursorOwner(object(), "session", 1, lambda _session: None)
    response = match_service_pb2.MatchResponse()
    response.results.add().CopyFrom(row)
    return MatchValue._from_response(response, owner), owner


def _binding() -> match_result_pb2.MatchBinding:
    value = match_result_pb2.MatchBinding()
    value.node.translation_unit_decl.SetInParent()
    value.is_complete = False
    value.supported_scopes.append(match_result_pb2.BINDING_MATCH_SCOPE_ROOT_ONLY)
    return value


def test_binding_value_is_a_detached_mutation_isolated_snapshot_readable_after_close() -> None:
    row = match_result_pb2.MatchResult()
    row.bindings["value"].CopyFrom(_binding())
    rows, owner = _collection(row)
    selected = rows[0].binding("value")
    value_view = property_value(selected, "value")
    assert property_value(value_view, "is_complete") is False
    assert call_method(value_view, "hasField", ["is_complete"]) is True
    assert property_value(property_value(value_view, "node"), "translation_unit_decl")

    copied = selected.value
    copied.is_complete = True
    assert selected.value.is_complete is False
    owner.close()
    assert property_value(value_view, "is_complete") is False


def test_optional_absence_oneofs_and_presence_capability_are_distinguished() -> None:
    binding = match_result_pb2.MatchBinding()
    view = __import__("clang_toolkit.cli.runtime.semantic", fromlist=["view"]).view(binding)
    assert call_method(view, "hasField", ["is_complete"]) is False
    with pytest.raises(ReferenceError, match="field is absent"):
        property_value(view, "is_complete")
    with pytest.raises(ReferenceError, match="inactive oneof"):
        property_value(view, "node")
    with pytest.raises(ReferenceError, match="field has no presence"):
        call_method(view, "hasField", ["availability"])
    with pytest.raises(ReferenceError, match="unknown semantic field"):
        property_value(view, "arbitrary_python_attribute")


def test_repeated_and_map_views_have_cardinality_indexing_and_iteration() -> None:
    row = match_result_pb2.MatchResult()
    row.bindings["f"].CopyFrom(_binding())
    row.bindings["length"].CopyFrom(_binding())
    view = __import__("clang_toolkit.cli.runtime.semantic", fromlist=["view"]).view(row)
    bindings = property_value(view, "bindings")
    assert len(bindings) == 2
    assert property_value(index_value(bindings, "f"), "is_complete") is False
    assert property_value(index_value(bindings, "length"), "is_complete") is False
    assert set(bindings) == {"f", "length"}
    scopes = property_value(index_value(bindings, "f"), "supported_scopes")
    assert len(scopes) == 1
    assert str(index_value(scopes, 0)) == "BINDING_MATCH_SCOPE_ROOT_ONLY"
    with pytest.raises(ReferenceError, match="out of range"):
        index_value(scopes, 1)
    with pytest.raises(ReferenceError, match="keys must be strings"):
        index_value(bindings, 0)


def test_explicit_row_binding_map_resolves_collisions_and_collection_value_needs_index() -> None:
    row = match_result_pb2.MatchResult()
    row.bindings["bindings"].CopyFrom(_binding())
    row.bindings["name"].CopyFrom(_binding())
    rows, _owner = _collection(row)
    selected_row = rows[0]
    explicit = property_value(property_value(selected_row, "bindings"), "length")
    assert explicit == 2
    selector = index_value(property_value(selected_row, "bindings"), "bindings")
    assert selector.name == "bindings"
    assert property_value(selector, "name") == "bindings"
    with pytest.raises(ReferenceError, match="explicit row index"):
        property_value(rows.binding("name"), "value")


def test_exact_large_integer_enum_unknown_and_bounded_inspection() -> None:
    large = (1 << 64) - 1
    component = semantic_types_pb2.OffsetOfComponent(array_index=large)
    component_view = __import__("clang_toolkit.cli.runtime.semantic", fromlist=["view"]).view(component)
    assert property_value(component_view, "array_index") == large

    unknown_scope = match_result_pb2.MatchBinding()
    unknown_scope.supported_scopes.append(999)
    unknown_view = __import__("clang_toolkit.cli.runtime.semantic", fromlist=["view"]).view(unknown_scope)
    enum_value = index_value(property_value(unknown_view, "supported_scopes"), 0)
    assert enum_value.number == 999
    assert enum_value.name == "UNKNOWN_999"

    long_value = match_result_pb2.MatchBinding(unsupported={"detail": "x" * 1000})
    inspected = inspect_value(__import__("clang_toolkit.cli.runtime.semantic", fromlist=["view"]).view(long_value))
    assert len(inspected["fields"]["unsupported"]["fields"]["detail"]) <= 257
    assert "hasField" not in inspected["fields"]
    assert inspected["methods"] == ["hasField"]


def test_qual_type_shallow_description_is_directly_readable() -> None:
    qualified_type = semantic_pb2.QualType()
    qualified_type.description.spelling = "int"
    type_view = __import__("clang_toolkit.cli.runtime.semantic", fromlist=["view"]).view(qualified_type)

    description = property_value(type_view, "description")
    assert property_value(description, "spelling") == "int"
    assert call_method(type_view, "hasField", ["description"]) is True


def test_explicitly_empty_optional_string_is_present_and_empty() -> None:
    unsupported = match_result_pb2.MatchBinding()
    unsupported.unsupported.detail = ""
    view = __import__("clang_toolkit.cli.runtime.semantic", fromlist=["view"]).view(unsupported)
    detail = property_value(property_value(view, "unsupported"), "detail")
    assert detail == ""
    assert call_method(property_value(view, "unsupported"), "hasField", ["detail"]) is True


def test_unavailable_and_unsupported_values_keep_their_reasons() -> None:
    unavailable = match_result_pb2.MatchBinding()
    entry = unavailable.availability.add()
    entry.field_path = "MatchBinding.node"
    entry.state = common_pb2.FIELD_STATE_UNAVAILABLE
    entry.reason = "serializer deliberately omitted this payload"
    unavailable_view = __import__("clang_toolkit.cli.runtime.semantic", fromlist=["view"]).view(unavailable)
    with pytest.raises(ReferenceError, match="serializer deliberately omitted"):
        property_value(unavailable_view, "node")

    unsupported = match_result_pb2.MatchBinding()
    unsupported.unsupported.detail = "unsupported class"
    unsupported_view = __import__("clang_toolkit.cli.runtime.semantic", fromlist=["view"]).view(unsupported)
    with pytest.raises(ReferenceError, match="unsupported class"):
        property_value(unsupported_view, "node")


def test_unrequested_nested_fields_are_not_advertised_or_reported_as_present() -> None:
    binding = match_result_pb2.MatchBinding()
    binding.node.function_decl.function.declarator.value.named.qualified_name = "alpha"
    binding.is_complete = True
    entry = binding.availability.add()
    entry.field_path = "FunctionDeclInfo.parameters"
    entry.state = common_pb2.FIELD_STATE_UNREQUESTED
    entry.reason = "request a parameter match to inspect children"
    binding_view = __import__("clang_toolkit.cli.runtime.semantic", fromlist=["view"]).view(binding)
    node_view = property_value(binding_view, "node")

    assert property_value(binding_view, "is_complete") is True
    assert "qualified_name" in field_names(node_view)
    assert "parameters" not in field_names(node_view)
    assert call_method(node_view, "hasField", ["parameters"]) is False
    with pytest.raises(ReferenceError, match="field was not requested.*parameter match"):
        property_value(node_view, "parameters")

    inspected = inspect_semantic_value(node_view, max_items=80)
    assert inspected["fields"]["qualified_name"] == "alpha"
    assert "parameters" not in inspected["fields"]


def test_inspect_supports_rows_collections_selectors_and_detached_values() -> None:
    row = match_result_pb2.MatchResult()
    row.bindings["f"].CopyFrom(_binding())
    rows, owner = _collection(row)
    selected = property_value(rows[0], "f")
    assert inspect_value(selected)["has_semantic_value"] is True
    assert inspect_value(property_value(selected, "value"))["type"] == "ctk.match.v1.MatchBinding"
    assert inspect_value(rows[0])["type"] == "MatchRow"
    assert inspect_value(rows)["length"] == 1
    owner.close()
    assert inspect_value(property_value(selected, "value"))["type"] == "ctk.match.v1.MatchBinding"


def test_row_render_preserves_proto_json_enum_and_uint64_contracts() -> None:
    row = match_result_pb2.MatchResult(source_match_index=(1 << 64) - 1)
    row.bindings["f"].CopyFrom(_binding())
    rows, _owner = _collection(row)
    selected = rows[0]

    rendered = json.loads(render(selected))
    assert rendered["source_match_index"] == str((1 << 64) - 1)
    assert rendered["bindings"]["f"]["supported_scopes"] == ["BINDING_MATCH_SCOPE_ROOT_ONLY"]

    semantic_result = __import__("clang_toolkit.cli.runtime.semantic", fromlist=["view"]).view(selected._message())
    assert property_value(semantic_result, "source_match_index") == (1 << 64) - 1
    assert selected.source_match_index == (1 << 64) - 1


def test_row_render_truncates_huge_binding_keys_and_payloads() -> None:
    key = "binding-" + "k" * 50_000
    row = match_result_pb2.MatchResult()
    row.bindings[key].unsupported.detail = "payload-" + "p" * 50_000
    rows, _owner = _collection(row)

    rendered = render(rows[0])
    assert len(rendered) <= 20_000
    assert "[key 0 truncated]" in rendered
    assert "… <truncated>" in rendered


def test_ordinary_semantic_render_shows_fields_without_inspection_metadata() -> None:
    qualified_type = semantic_pb2.QualType()
    qualified_type.description.spelling = "int"
    qualified_type.description.qualifiers.is_const = True
    qualified_type.type.builtin_type.kind = semantic_pb2.BUILTIN_KIND_INT

    rendered = json.loads(render(semantic_view(qualified_type)))

    assert rendered == {
        "description": {"qualifiers": {"is_const": True}, "spelling": "int"},
        "type": {"builtin_type": {"kind": "BUILTIN_KIND_INT"}},
    }
    assert "ctk.ast.v1.QualType" not in json.dumps(rendered)
    assert "active_oneof" not in json.dumps(rendered)
    assert "methods" not in json.dumps(rendered)


def test_ordinary_semantic_render_preserves_declaration_name_variant_and_bounds() -> None:
    name = semantic_pb2.DeclarationName(literal_operator_suffix="_km")
    rendered = json.loads(render(semantic_view(name)))
    assert rendered == {"literal_operator_suffix": "_km"}

    long_value = semantic_pb2.TypeDescription(spelling="x" * 30_000)
    bounded = render(semantic_view(long_value))
    assert len(bounded) <= 20_000
    assert "truncated" in bounded


def test_ordinary_semantic_projection_bounds_depth_and_repeated_values() -> None:
    binding = match_result_pb2.MatchBinding()
    binding.supported_scopes.extend([
        match_result_pb2.BINDING_MATCH_SCOPE_ROOT_ONLY,
        match_result_pb2.BINDING_MATCH_SCOPE_SUBTREE,
    ])
    value = semantic_view(binding)
    assert json.loads(render(value))["supported_scopes"] == [
        "BINDING_MATCH_SCOPE_ROOT_ONLY",
        "BINDING_MATCH_SCOPE_SUBTREE",
    ]

    nested = semantic_pb2.QualType()
    nested.description.spelling = "int"
    assert display_value(semantic_view(nested), max_depth=1) == {"description": {"…": "depth truncated"}}


def test_ordinary_semantic_projection_renders_maps_as_objects() -> None:
    row = match_result_pb2.MatchResult()
    row.bindings["f"].CopyFrom(_binding())
    bindings = property_value(semantic_view(row), "bindings")

    assert json.loads(render(bindings)) == {
        "f": {
            "is_complete": False,
            "node": {"translation_unit_decl": {}},
            "supported_scopes": ["BINDING_MATCH_SCOPE_ROOT_ONLY"],
        }
    }
