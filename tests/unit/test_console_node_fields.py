from __future__ import annotations

import pytest

from clang_toolkit._generated.ast.v1 import node_pb2
from clang_toolkit.cli.runtime.references import (
    ReferenceError,
    call_method,
    field_names,
    property_value,
)
from clang_toolkit.cli.runtime.semantic import field_sources, view
from clang_toolkit.cli.runtime.semantic import inspect_value


_DECLARATION_BASES = {
    "function_decl": ("function", "declarator", "value", "named"),
    "cxx_deduction_guide_decl": ("function", "declarator", "value", "named"),
    "cxx_method_decl": ("method", "function", "declarator", "value", "named"),
    "cxx_constructor_decl": ("method", "function", "declarator", "value", "named"),
    "cxx_destructor_decl": ("method", "function", "declarator", "value", "named"),
    "cxx_conversion_decl": ("method", "function", "declarator", "value", "named"),
}


def _node_with_decl_name(payload_name: str) -> node_pb2.AstNode:
    node = node_pb2.AstNode()
    payload = getattr(node, payload_name)
    owner = payload
    for field_name in _DECLARATION_BASES[payload_name]:
        owner = getattr(owner, field_name)
    owner.name.identifier = "run"
    owner.qualified_name = "Widget::run"
    owner.declaration.SetInParent()
    return node


def _raw_path_value(node_view, payload_name: str, fields: tuple[str, ...]):
    value = property_value(node_view, payload_name)
    for field_name in fields:
        value = property_value(value, field_name)
    return value


@pytest.mark.parametrize("payload_name", tuple(_DECLARATION_BASES))
def test_active_declaration_payload_exposes_typed_inherited_fields(payload_name):
    raw_node = _node_with_decl_name(payload_name)
    node_view = view(raw_node)

    direct_name = property_value(node_view, "name")
    direct_qualified_name = property_value(node_view, "qualified_name")

    assert direct_name.descriptor.full_name == "ctk.ast.v1.DeclarationName"
    assert property_value(direct_name, "identifier") == "run"
    assert direct_qualified_name == "Widget::run"
    assert direct_qualified_name == _raw_path_value(
        node_view, payload_name, (*_DECLARATION_BASES[payload_name], "qualified_name")
    )
    assert direct_name._path.endswith(
        "." + ".".join((*_DECLARATION_BASES[payload_name], "name"))
    )


def test_field_sources_keep_actual_owners_and_include_inactive_payload_presence():
    node_view = view(_node_with_decl_name("cxx_method_decl"))

    visible = field_sources(node_view)
    all_sources = field_sources(node_view, include_inactive=True)

    assert "cxx_method_decl" in visible
    assert "function_decl" not in visible
    assert all(name in all_sources for name in _DECLARATION_BASES)
    owner, descriptor = visible["qualified_name"]
    assert owner.descriptor.full_name == "ctk.ast.v1.NamedDeclInfo"
    assert descriptor.name == "qualified_name"
    assert owner._path.endswith(
        ".cxx_method_decl.method.function.declarator.value.named"
    )
    assert all_sources["cxx_constructor_decl"][0] is node_view

    assert "cxx_method_decl" in field_names(node_view)
    assert "function_decl" not in field_names(node_view)
    assert call_method(node_view, "hasField", ["cxx_method_decl"]) is True
    assert call_method(node_view, "hasField", ["function_decl"]) is False
    assert call_method(node_view, "hasField", ["qualified_name"]) is True
    assert call_method(node_view, "hasField", ["is_invalid"]) is False
    with pytest.raises(ReferenceError, match="field is absent"):
        property_value(node_view, "is_invalid")
    with pytest.raises(ReferenceError, match="unknown semantic field"):
        call_method(node_view, "hasField", ["not_a_schema_field"])


def test_direct_node_fields_do_not_flatten_arbitrary_descendant_names():
    node_view = view(_node_with_decl_name("cxx_method_decl"))

    names = set(field_names(node_view))

    assert {"method", "function", "declarator", "value", "named"} <= names
    assert {"parent_record", "parameters", "body", "return_type"} <= names
    assert "spelling" not in names
    assert "canonical_spelling" not in names


def test_inspection_includes_inherited_typed_fields_and_unavailable_direct_fields():
    node_view = view(_node_with_decl_name("cxx_method_decl"))

    inspected = inspect_value(node_view, max_items=40)
    fields = inspected["fields"]

    assert fields["name"]["type"] == "ctk.ast.v1.DeclarationName"
    assert fields["name"]["fields"]["identifier"] == "run"
    assert fields["qualified_name"] == "Widget::run"
    assert fields["body"] == {
        "unavailable": "field is absent: "
        "ctk.ast.v1.AstNode.cxx_method_decl.method.function.body"
    }

    body_owner, body_descriptor = field_sources(node_view, include_inactive=True)["body"]
    assert body_descriptor.name == "body"
    assert body_owner.descriptor.full_name == "ctk.ast.v1.FunctionDeclInfo"
    assert body_owner._path.endswith(".cxx_method_decl.method.function")


def test_inactive_ast_payload_names_keep_their_raw_owner_when_included():
    node_view = view(_node_with_decl_name("cxx_method_decl"))

    source = field_sources(node_view, include_inactive=True)["function_decl"]

    assert source == (node_view, node_view.descriptor.fields_by_name["function_decl"])
