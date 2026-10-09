"""Lossless binary encoding for the runtime's existing typed value envelope."""

from __future__ import annotations

from typing import Any

from clang_toolkit._generated.match.v1.saved_value_pb2 import SavedData, SavedValue


def _pack(value: Any) -> SavedData:
    result = SavedData()
    if value is None:
        result.null_value = SavedData.NULL_VALUE
    elif type(value) is bool:
        result.bool_value = value
    elif type(value) is int:
        result.integer_value = str(value)
    elif type(value) is float:
        result.float_value = value
    elif isinstance(value, str):
        result.string_value = value
    elif isinstance(value, list):
        result.list_value.SetInParent()
        for item in value:
            result.list_value.items.add().CopyFrom(_pack(item))
    elif isinstance(value, dict):
        result.record_value.SetInParent()
        for key, item in value.items():
            result.record_value.fields[key].CopyFrom(_pack(item))
    else:
        raise ValueError(f"unsupported protobuf snapshot data: {type(value).__name__}")
    return result


def _unpack(value: SavedData) -> Any:
    kind = value.WhichOneof("value")
    if kind == "null_value":
        if value.null_value != SavedData.NULL_VALUE:
            raise ValueError("invalid null snapshot value")
        return None
    if kind == "integer_value":
        return int(value.integer_value)
    if kind == "list_value":
        return [_unpack(item) for item in value.list_value.items]
    if kind == "record_value":
        return {key: _unpack(item) for key, item in value.record_value.fields.items()}
    if kind in {"bool_value", "float_value", "string_value"}:
        return getattr(value, kind)
    raise ValueError("missing protobuf snapshot value")


def encode(envelope: dict[str, Any]) -> bytes:
    snapshot = SavedValue(schema_version=1, envelope=_pack(envelope))
    return snapshot.SerializeToString(deterministic=True)


def decode(data: bytes) -> dict[str, Any]:
    snapshot = SavedValue.FromString(data)
    if snapshot.schema_version != 1:
        raise ValueError("unsupported or missing schema_version")
    envelope = _unpack(snapshot.envelope)
    if not isinstance(envelope, dict):
        raise ValueError("invalid protobuf typed value envelope")
    return envelope
