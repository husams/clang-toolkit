"""Local field-presence and exact semantic-node predicates for the prototype."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from google.protobuf.message import Message

from clang_toolkit._generated.ast.v1 import node_pb2
from clang_toolkit.match_values import BindingSelection

from ..references import call_method
from ..semantic import (
    BindingMapView,
    MapView,
    MessageView,
    SemanticError,
    _availability_error,
    field_sources,
    property_value,
    view,
)

_NODE_DESCRIPTOR = node_pb2.AstNode.DESCRIPTOR
_NODE_KINDS = {
    field.message_type.name: field.message_type.full_name
    for field in _NODE_DESCRIPTOR.oneofs_by_name["payload"].fields
}
_NODE_KIND_TYPES = frozenset(_NODE_KINDS.values())
_NODE_ALIASES = {"CXXRecord": "CXXRecordDecl"}
_AST_NODE = _NODE_DESCRIPTOR.full_name
_MATCH_BINDING = "ctk.match.v1.MatchBinding"


def has_field(value: Any, key: Any) -> bool:
    """Test existing keys or presence-bearing schema fields without reading them."""
    if not isinstance(key, str):
        raise SemanticError(f"field name requires a string, got {type(key).__name__}")
    if isinstance(value, Mapping):
        return key in value
    if isinstance(value, (MapView, BindingMapView)):
        return key in value
    if isinstance(value, BindingSelection):
        value = view(value.value)
    elif isinstance(value, Message):
        value = view(value)
    if isinstance(value, MessageView):
        source = field_sources(value, include_inactive=True).get(key)
        if source is not None:
            owner, descriptor = source
            availability = _availability_error(owner, descriptor.name)
            if availability is not None and not availability.startswith((
                "field is semantically absent:", "field is inapplicable:"
            )):
                raise SemanticError(availability)
        return call_method(value, "hasField", [key])
    raise SemanticError(
        f"field presence requires a dictionary or semantic record, got {type(value).__name__}"
    )


def is_node_kind(value: Any, kind: Any) -> bool:
    """Test an explicit row's copied AST payload; retain its owning cursor."""
    if not isinstance(kind, str):
        raise SemanticError(f"node kind requires a name, got {type(kind).__name__}")
    canonical = _NODE_ALIASES.get(kind, kind)
    expected = _NODE_KINDS.get(canonical)
    if expected is None:
        raise SemanticError(f"unknown node kind: {kind}")
    if isinstance(value, BindingSelection):
        value = view(value.value)
    elif isinstance(value, Message):
        value = view(value)
    if not isinstance(value, MessageView):
        raise SemanticError(
            f"node kind requires one selected semantic node, got {type(value).__name__}"
        )
    if value.descriptor.full_name == _MATCH_BINDING:
        binding = value._message()
        active = binding.WhichOneof("value")
        if active == "unsupported":
            unsupported = property_value(value, "unsupported")
            detail = (
                property_value(unsupported, "detail")
                if unsupported._message().HasField("detail")
                else "unsupported value kind"
            )
            raise SemanticError(f"unsupported semantic payload: {detail}")
        if active != "node":
            raise SemanticError(f"binding has no AST node payload (value: {active or 'absent'})")
        value = property_value(value, "node")
    if value.descriptor.full_name == _AST_NODE:
        payload = value._message().WhichOneof("payload")
        if payload is None:
            raise SemanticError("AST node has no active payload")
        value = property_value(value, payload)
    if value.descriptor.full_name not in _NODE_KIND_TYPES:
        raise SemanticError(
            f"node kind requires an AST node payload, got {value.descriptor.name}"
        )
    return value.descriptor.full_name == expected

