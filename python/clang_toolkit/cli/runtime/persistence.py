"""Versioned variable exchange in YAML, JSON, and flat typed CSV."""

from __future__ import annotations

import csv
import base64
import binascii
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from google.protobuf.message import DecodeError
from google.protobuf import descriptor_pool, message_factory
from google.protobuf.json_format import MessageToDict, ParseDict, ParseError
from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message

from clang_toolkit._value_lifecycle import MatchValueError
from .filesystem import Directory, File, FileSystemEntry
from .values import MatchSet, MatcherExpr, QualifiedName
from clang_toolkit.match_values import (
    BindingSelection, MatchRow, MatchValue, NativeMatchCollection, ParsedTree,
)
from .semantic import (
    BindingMapView, EnumValue, MapView, MessageView, RepeatedView,
    SemanticError, _availability_error, _availability_of, view as semantic_view,
)


class PersistenceError(ValueError):
    """A value cannot be saved or an external file cannot be loaded safely."""


_SUFFIXES = {"yaml": ".yaml", "json": ".json", "csv": ".csv", "proto": ".proto"}
_TYPES = {"str", "bool", "int", "float"}
_LEGACY_KINDS = {
    "null", "bool", "int", "float", "str", "bytes", "semantic_message",
    "semantic_repeated", "semantic_map", "binding_snapshot", "semantic_bindings",
    "semantic_enum", "file", "directory", "list", "record", "qualified_name",
    "matcher", "match_snapshot",
}
_COMPLETENESS_WRAPPERS = {
    "ctk.ast.v1.DeclarationValue",
    "ctk.ast.v1.ExpressionValue",
    "ctk.ast.v1.StatementValue",
    "ctk.ast.v1.TypeValue",
}
_BINDING_OPERATIONAL_FIELDS = {"availability", "is_complete", "supported_scopes"}
_SEMANTIC_RESULT_STATUS_FIELDS = {
    "availability", "is_complete", "unsupported_values"
}


def _plain_bytes(value: bytes) -> str:
    """Keep UTF-8 bytes readable; mark binary data with conventional base64 text."""
    try:
        return value.decode("utf-8")
    except UnicodeDecodeError:
        return "base64:" + base64.b64encode(value).decode("ascii")


def _plain_element(
    value: Any,
    field: FieldDescriptor,
    availability: tuple[tuple[str, int | None, str | None], ...] = (),
    path: str = "",
) -> Any:
    if field.type == FieldDescriptor.TYPE_BYTES:
        return _plain_bytes(value)
    if field.type == FieldDescriptor.TYPE_ENUM:
        enum = field.enum_type.values_by_number.get(int(value))
        return enum.name if enum is not None else int(value)
    if isinstance(value, Message):
        if value.DESCRIPTOR.full_name == "ctk.match.v1.MatchBinding":
            return _plain_binding(value, availability)
        if value.DESCRIPTOR.full_name == "ctk.match.v1.MatchResult":
            return _plain_row(value, availability)
        child_path = (
            value.DESCRIPTOR.full_name
            if value.DESCRIPTOR.full_name == "ctk.match.v1.MatchBinding"
            else path or field.name
        )
        return _plain_message(
            value,
            availability + _availability_of(value),
            child_path,
        )
    return value


def _plain_message(
    message: Message,
    availability: tuple[tuple[str, int | None, str | None], ...] = (),
    path: str = "",
) -> dict[str, Any]:
    """Export every present protobuf field without JSON format's int64 strings."""
    result: dict[str, Any] = {}
    if not path:
        path = message.DESCRIPTOR.full_name
    semantic_view = MessageView(message.SerializeToString(), type(message), availability, path)
    for field in message.DESCRIPTOR.fields:
        if (
            message.DESCRIPTOR.full_name == "ctk.ast.v1.SemanticResult"
            and field.name in _SEMANTIC_RESULT_STATUS_FIELDS
        ):
            continue
        if (
            message.DESCRIPTOR.full_name == "ctk.ast.v1.AstNode"
            and field.name in {"availability", "is_complete"}
        ):
            continue
        if (
            message.DESCRIPTOR.full_name in _COMPLETENESS_WRAPPERS
            and field.name == "is_complete"
        ):
            continue
        value = getattr(message, field.name)
        if _availability_error(semantic_view, field.name) is not None:
            continue
        field_path = f"{path}.{field.name}"
        if field.is_repeated:
            if not value:
                continue
            is_map = bool(
                field.message_type and field.message_type.GetOptions().map_entry
            )
            if is_map:
                value_field = field.message_type.fields_by_name["value"]
                result[field.name] = {
                    key: _plain_element(
                        item, value_field, availability, f"{field_path}[{key!r}]"
                    )
                    for key, item in value.items()
                }
            else:
                result[field.name] = [
                    _plain_element(item, field, availability, f"{field_path}[{index}]")
                    for index, item in enumerate(value)
                ]
            continue
        if field.containing_oneof is not None:
            if message.WhichOneof(field.containing_oneof.name) != field.name:
                continue
        elif field.has_presence:
            if not message.HasField(field.name):
                continue
        elif value == field.default_value:
            continue
        result[field.name] = _plain_element(value, field, availability, field_path)
    return result


def _plain_binding(
    message: Message,
    inherited_availability: tuple[tuple[str, int | None, str | None], ...] = (),
) -> dict[str, Any]:
    """Export the selected AST payload and copied AST facts of one MatchBinding."""
    active = message.WhichOneof("value")
    result: dict[str, Any] = {}
    availability = inherited_availability + _availability_of(message)
    path = message.DESCRIPTOR.full_name
    semantic_view = MessageView(message.SerializeToString(), type(message), availability, path)
    if active is not None:
        field = message.DESCRIPTOR.fields_by_name[active]
        if _availability_error(semantic_view, active) is None:
            payload = _plain_element(
                getattr(message, active), field, availability, f"{path}.{active}"
            )
            if isinstance(payload, dict):
                result.update(payload)
            else:
                result[active] = payload

    for field in message.DESCRIPTOR.fields:
        if field.containing_oneof is not None or field.name in _BINDING_OPERATIONAL_FIELDS:
            continue
        if _availability_error(semantic_view, field.name) is not None:
            continue
        value = getattr(message, field.name)
        if field.has_presence and not message.HasField(field.name):
            continue
        if not field.has_presence and value == field.default_value:
            continue
        result[field.name] = _plain_element(
            value, field, availability, f"{path}.{field.name}"
        )
    return result


def _plain_row(
    message: Message,
    inherited_availability: tuple[tuple[str, int | None, str | None], ...] = (),
) -> dict[str, Any]:
    """Export named AST bindings while dropping row provenance metadata."""
    bindings = message.bindings
    return {
        "bindings": {
            name: _plain_binding(binding, inherited_availability)
            for name, binding in bindings.items()
        }
    }


def _plain_encode(value: Any) -> Any:
    """Turn runtime values into ordinary JSON/YAML containers and scalars."""
    if isinstance(value, BindingSelection):
        try:
            return _plain_encode(semantic_view(value.value))
        except MatchValueError as error:
            raise PersistenceError(f"binding selection cannot be saved: {error}") from error
    if isinstance(value, MessageView):
        message = value._message_type()
        message.ParseFromString(value._data)
        if message.DESCRIPTOR.full_name == "ctk.match.v1.MatchBinding":
            return _plain_binding(message, value._availability)
        if message.DESCRIPTOR.full_name == "ctk.match.v1.MatchResult":
            return _plain_row(message, value._availability)
        return _plain_message(message, value._availability, value._path)
    if isinstance(value, (RepeatedView, MapView)):
        message = value._message_type()
        message.ParseFromString(value._data)
        field = message.DESCRIPTOR.fields_by_name[value._field_name]
        selected = getattr(message, value._field_name)
        if isinstance(value, MapView):
            value_field = field.message_type.fields_by_name["value"]
            return {
                key: _plain_element(item, value_field, value._availability, value._path)
                for key, item in selected.items()
            }
        return [
            _plain_element(item, field, value._availability, f"{value._path}[{index}]")
            for index, item in enumerate(selected)
        ]
    if isinstance(value, BindingMapView):
        return {
            key: _plain_binding(binding)
            for key, binding in value._row.bindings.items()
        }
    if isinstance(value, EnumValue):
        return value.number if value.name.startswith("UNKNOWN_") else value.name
    if isinstance(value, MatchRow):
        return _plain_row(value._message())
    if isinstance(value, (MatchValue, NativeMatchCollection)):
        return [_plain_encode(row) for row in value.iter_rows()]
    if isinstance(value, ParsedTree):
        raise PersistenceError("native trees cannot be saved")
    if isinstance(value, bytes):
        return _plain_bytes(value)
    if isinstance(value, FileSystemEntry):
        return {
            "path": value.path,
            "absolute": value.absolute,
            "size": value.size,
            "modified": value.modified.isoformat(),
        }
    if isinstance(value, list):
        return [_plain_encode(item) for item in value]
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        return {key: _plain_encode(item) for key, item in value.items()}
    if isinstance(value, MatcherExpr):
        return {
            "name": value.name,
            "arguments": [_plain_encode(arg) for arg in value.arguments],
            "binding": value.binding,
        }
    if isinstance(value, QualifiedName):
        return value.text
    if isinstance(value, MatchSet):
        return [_plain_encode(row) for row in value.rows]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise PersistenceError(f"cannot save value of type {type(value).__name__}")


def _encode(value: Any) -> dict[str, Any]:
    if isinstance(value, BindingSelection):
        try:
            # Export one copied binding and its display metadata, never the
            # cursor owner, scope, session, or revision.
            snapshot = {
                "name": value.name,
                "value": _encode(semantic_view(value.value)),
            }
            if value.source_file is not None:
                snapshot["source_file"] = value.source_file
            return {"type": "binding_snapshot", "value": snapshot}
        except (MatchValueError, SemanticError) as error:
            raise PersistenceError(f"binding selection cannot be saved: {error}") from error
    if isinstance(value, MessageView):
        return {"type": "semantic_message", "value": _semantic_snapshot(value)}
    if isinstance(value, RepeatedView):
        return {
            "type": "semantic_repeated",
            "value": {**_semantic_snapshot(value), "field": value._field_name},
        }
    if isinstance(value, MapView):
        return {
            "type": "semantic_map",
            "value": {**_semantic_snapshot(value), "field": value._field_name},
        }
    if isinstance(value, BindingMapView):
        return {
            "type": "semantic_bindings",
            "value": {
                key: _encode(semantic_view(binding))
                for key, binding in value._row.bindings.items()
            },
        }
    if isinstance(value, EnumValue):
        return {"type": "semantic_enum", "value": {"name": value.name, "number": value.number}}
    if isinstance(value, MatchValue):
        return {"type": "match_snapshot", "value": [_encode(_detached_row(row)) for row in value.iter_rows()]}
    if isinstance(value, MatchRow):
        return _encode(_detached_row(value))
    if isinstance(value, NativeMatchCollection):
        return {"type": "match_snapshot", "value": [_encode(_detached_row(row)) for row in value]}
    if isinstance(value, ParsedTree):
        raise PersistenceError("native trees cannot be saved")
    if value is None:
        return {"type": "null", "value": None}
    if isinstance(value, bool):
        return {"type": "bool", "value": value}
    if isinstance(value, int):
        return {"type": "int", "value": value}
    if isinstance(value, float):
        return {"type": "float", "value": value}
    if isinstance(value, str):
        return {"type": "str", "value": value}
    if isinstance(value, bytes):
        return {"type": "bytes", "value": base64.b64encode(value).decode("ascii")}
    if isinstance(value, FileSystemEntry):
        return {
            "type": "directory" if isinstance(value, Directory) else "file",
            "value": {
                "path": value.path,
                "absolute": value.absolute,
                "size": value.size,
                "modified": value.modified.isoformat(),
            },
        }
    if isinstance(value, list):
        return {"type": "list", "value": [_encode(item) for item in value]}
    if isinstance(value, dict) and all(isinstance(key, str) for key in value):
        return {
            "type": "record",
            "value": {key: _encode(item) for key, item in value.items()},
        }
    if isinstance(value, MatcherExpr):
        return {
            "type": "matcher",
            "value": {
                "name": value.name,
                "arguments": [_encode(arg) for arg in value.arguments],
                "binding": value.binding,
            },
        }
    if isinstance(value, QualifiedName):
        return {"type": "qualified_name", "value": value.text}
    if isinstance(value, MatchSet):
        return {"type": "match_snapshot", "value": [_encode(row) for row in value.rows]}
    raise PersistenceError(f"cannot save value of type {type(value).__name__}")


def _semantic_snapshot(value: MessageView | RepeatedView | MapView) -> dict[str, Any]:
    availability = getattr(value, "_availability", ())
    message = value._message_type()
    message.ParseFromString(value._data)
    if isinstance(value, RepeatedView | MapView):
        for field in message.DESCRIPTOR.fields:
            if field.name != value._field_name:
                message.ClearField(field.name)
    return {
        "message_type": value._message_type.DESCRIPTOR.full_name,
        "message": MessageToDict(message, preserving_proto_field_name=True),
        "availability": [list(item) for item in availability],
        "path": getattr(value, "_path", ""),
    }


def _detached_row(row: Any) -> dict[str, Any]:
    value = row.to_dict()
    if row.source_file is not None:
        value["source_file"] = row.source_file
    return value


def _decode(envelope: Any) -> Any:
    if not isinstance(envelope, dict) or set(envelope) != {"type", "value"}:
        raise PersistenceError("invalid typed value envelope")
    kind, value = envelope["type"], envelope["value"]
    if kind == "null" and value is None:
        return None
    if kind == "bool" and type(value) is bool:
        return value
    if kind == "int" and type(value) is int:
        return value
    if kind == "float" and type(value) in {int, float}:
        return float(value)
    if kind == "str" and isinstance(value, str):
        return value
    if kind == "bytes" and isinstance(value, str):
        try:
            return base64.b64decode(value, validate=True)
        except (ValueError, binascii.Error) as error:
            raise PersistenceError("invalid bytes snapshot") from error
    if kind in {"semantic_message", "semantic_repeated", "semantic_map"}:
        return _decode_semantic(kind, value)
    if kind == "binding_snapshot" and isinstance(value, dict):
        if set(value) not in ({"name", "value"}, {"name", "value", "source_file"}):
            raise PersistenceError("invalid binding snapshot envelope")
        name = value["name"]
        source_file = value.get("source_file")
        semantic = _decode(value["value"])
        if (
            not isinstance(name, str)
            or (source_file is not None and not isinstance(source_file, str))
            or not isinstance(semantic, MessageView)
            or semantic.descriptor.full_name != "ctk.match.v1.MatchBinding"
        ):
            raise PersistenceError("invalid binding snapshot data")
        result = {"name": name, "value": semantic}
        if source_file is not None:
            result["source_file"] = source_file
        return result
    if kind == "semantic_bindings" and isinstance(value, dict) and all(
        isinstance(key, str) for key in value
    ):
        bindings = {key: _decode(item) for key, item in value.items()}
        if any(
            not isinstance(binding, MessageView)
            or binding.descriptor.full_name != "ctk.match.v1.MatchBinding"
            for binding in bindings.values()
        ):
            raise PersistenceError("invalid semantic binding map entry")
        return bindings
    if kind == "semantic_enum" and isinstance(value, dict):
        if set(value) == {"name", "number"} and isinstance(value["name"], str) and type(value["number"]) is int:
            return EnumValue(value["name"], value["number"])
    if kind in {"file", "directory"} and isinstance(value, dict):
        if (
            set(value) == {"path", "absolute", "size", "modified"}
            and isinstance(value["path"], str)
            and isinstance(value["absolute"], str)
            and type(value["size"]) is int
            and isinstance(value["modified"], str)
        ):
            try:
                modified = datetime.fromisoformat(value["modified"])
            except ValueError as exc:
                raise PersistenceError("invalid file modification time") from exc
            if Path(value["absolute"]).is_absolute() and modified.tzinfo is not None:
                entry_type = File if kind == "file" else Directory
                return entry_type(
                    value["path"], value["absolute"], value["size"], modified
                )
    if kind == "list" and isinstance(value, list):
        return [_decode(item) for item in value]
    if (
        kind == "record"
        and isinstance(value, dict)
        and all(isinstance(key, str) for key in value)
    ):
        return {key: _decode(item) for key, item in value.items()}
    if kind == "qualified_name" and isinstance(value, str):
        return QualifiedName(value)
    if kind == "matcher" and isinstance(value, dict):
        name = value.get("name")
        args = value.get("arguments")
        binding = value.get("binding")
        if (
            isinstance(name, str)
            and isinstance(args, list)
            and (binding is None or isinstance(binding, str))
        ):
            return MatcherExpr(name, tuple(_decode(item) for item in args), binding)
    if kind == "match_snapshot" and isinstance(value, list):
        return MatchSet(tuple(_decode(item) for item in value))
    raise PersistenceError(f"invalid or unsupported typed value: {kind}")


def _decode_semantic(kind: str, value: Any) -> Any:
    required = {"message_type", "message", "availability", "path"}
    if kind in {"semantic_repeated", "semantic_map"}:
        required.add("field")
    if not isinstance(value, dict) or set(value) != required:
        raise PersistenceError("invalid semantic snapshot envelope")
    message_type_name = value["message_type"]
    message_fields = value["message"]
    path = value["path"]
    availability = value["availability"]
    if (
        not isinstance(message_type_name, str)
        or not isinstance(message_fields, dict)
        or not isinstance(path, str)
        or not isinstance(availability, list)
        or any(
            not isinstance(item, list)
            or len(item) != 3
            or not isinstance(item[0], str)
            or (item[1] is not None and type(item[1]) is not int)
            or (item[2] is not None and not isinstance(item[2], str))
            for item in availability
        )
    ):
        raise PersistenceError("invalid semantic snapshot metadata")
    try:
        descriptor = descriptor_pool.Default().FindMessageTypeByName(message_type_name)
        message_type = message_factory.GetMessageClass(descriptor)
        message = message_type()
        ParseDict(message_fields, message, ignore_unknown_fields=False)
        data = message.SerializeToString()
    except (KeyError, TypeError, ValueError, binascii.Error, DecodeError, ParseError) as error:
        raise PersistenceError("invalid semantic protobuf snapshot") from error
    normalized_availability = tuple(tuple(item) for item in availability)
    if kind == "semantic_message":
        return MessageView(data, message_type, normalized_availability, path)
    field_name = value["field"]
    if not isinstance(field_name, str) or field_name not in descriptor.fields_by_name:
        raise PersistenceError("invalid semantic snapshot field")
    field = descriptor.fields_by_name[field_name]
    if kind == "semantic_repeated" and (
        not field.is_repeated
        or (
            field.message_type is not None
            and field.message_type.GetOptions().map_entry
        )
    ):
        raise PersistenceError("semantic repeated snapshot does not name a repeated field")
    if kind == "semantic_map" and not (
        field.is_repeated
        and field.message_type is not None
        and field.message_type.GetOptions().map_entry
    ):
        raise PersistenceError("semantic map snapshot does not name a map field")
    wrapper = RepeatedView if kind == "semantic_repeated" else MapView
    return wrapper(data, message_type, field_name, normalized_availability, path)


def _scalar_kind(value: Any) -> str:
    if type(value) is bool:
        return "bool"
    if type(value) is int:
        return "int"
    if type(value) is float:
        return "float"
    if type(value) is str:
        return "str"
    raise PersistenceError(
        "CSV supports only flat lists of primitive values or records"
    )


def _csv_rows(value: Any) -> tuple[list[str], list[list[str]]]:
    if not isinstance(value, list):
        raise PersistenceError("CSV requires a list")
    if not value:
        return ["value:str"], []
    if all(isinstance(item, dict) for item in value):
        keys = list(value[0])
        if not keys or any(set(row) != set(keys) for row in value):
            raise PersistenceError("CSV records must have the same nonempty fields")
        kinds = {key: _scalar_kind(value[0][key]) for key in keys}
        if any(_scalar_kind(row[key]) != kinds[key] for row in value for key in keys):
            raise PersistenceError("CSV column types must be consistent")
        return [f"{key}:{kinds[key]}" for key in keys], [
            [
                str(row[key]).lower() if kinds[key] == "bool" else str(row[key])
                for key in keys
            ]
            for row in value
        ]
    kind = _scalar_kind(value[0])
    if any(_scalar_kind(item) != kind for item in value):
        raise PersistenceError("CSV scalar list must have one type")
    return [f"value:{kind}"], [
        [str(item).lower() if kind == "bool" else str(item)] for item in value
    ]


def _csv_load(path: Path) -> list[Any]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames:
            raise PersistenceError("CSV is missing a header")
        names: list[str] = []
        kinds: list[str] = []
        for header in reader.fieldnames:
            if ":" in header and header.rsplit(":", 1)[1] in _TYPES:
                name, kind = header.rsplit(":", 1)
            else:
                name, kind = header, "str"
            if not name or name in names:
                raise PersistenceError("CSV has duplicate or empty columns")
            names.append(name)
            kinds.append(kind)

        def decode_cell(raw: str, kind: str) -> Any:
            if kind == "str":
                return raw
            if kind == "bool":
                if raw not in {"true", "false"}:
                    raise PersistenceError("CSV boolean must be true or false")
                return raw == "true"
            try:
                return int(raw) if kind == "int" else float(raw)
            except ValueError as exc:
                raise PersistenceError(f"invalid CSV {kind} value: {raw}") from exc

        rows: list[Any] = []
        for row in reader:
            if None in row or any(
                row.get(header) is None for header in reader.fieldnames
            ):
                raise PersistenceError("CSV row has wrong number of fields")
            record = {
                name: decode_cell(row[header], kind)
                for header, name, kind in zip(reader.fieldnames, names, kinds)
            }
            rows.append(record["value"] if names == ["value"] else record)
        return rows


def _format_from_path(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        return "yaml"
    for kind, extension in _SUFFIXES.items():
        if suffix == extension:
            return kind
    raise PersistenceError(f"unsupported file extension: {suffix}")


def _save_path(path: Path, format_name: str | None) -> tuple[Path, str]:
    if format_name is not None and format_name not in _SUFFIXES:
        raise PersistenceError(f"unsupported format: {format_name}")
    kind = format_name or (_format_from_path(path) if path.suffix else "yaml")
    if not path.suffix:
        path = path.with_suffix(_SUFFIXES[kind])
    elif _format_from_path(path) != kind:
        raise PersistenceError("file extension and requested format disagree")
    return path, kind


def save(value: Any, path: Path, *, format_name: str | None = None) -> Path:
    path, kind = _save_path(path, format_name)
    temp_name: str | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="wb" if kind == "proto" else "w",
            **({} if kind == "proto" else {"encoding": "utf-8", "newline": ""}),
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as handle:
            temp_name = handle.name
            if kind == "proto":
                from .protobuf_persistence import encode
                handle.write(encode(_encode(value)))
            elif kind == "csv":
                headers, rows = _csv_rows(value)
                writer = csv.writer(handle)
                writer.writerow(headers)
                writer.writerows(rows)
            else:
                document = _plain_encode(value)
                if kind == "json":
                    json.dump(document, handle, ensure_ascii=False, indent=2)
                else:
                    yaml.safe_dump(
                        document, handle, allow_unicode=True, sort_keys=False
                    )
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except (OSError, yaml.YAMLError, TypeError, ValueError) as exc:
        raise PersistenceError(f"cannot save {path}: {exc}") from exc
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
    return path


def load(path: Path) -> Any:
    if not path.suffix:
        candidates = [
            path.with_suffix(extension)
            for extension in (".yaml", ".yml", ".json", ".csv", ".proto")
        ]
        existing = [candidate for candidate in candidates if candidate.exists()]
        if len(existing) != 1:
            raise PersistenceError("extensionless load needs exactly one matching file")
        path = existing[0]
    kind = _format_from_path(path)
    try:
        if kind == "proto":
            from .protobuf_persistence import decode
            return _decode(decode(path.read_bytes()))
        if kind == "csv":
            return _csv_load(path)
        with path.open(encoding="utf-8") as handle:
            document = json.load(handle) if kind == "json" else yaml.safe_load(handle)
    except (OSError, ValueError, DecodeError, yaml.YAMLError, csv.Error) as exc:
        raise PersistenceError(f"cannot load {path}: {exc}") from exc
    if (
        isinstance(document, dict)
        and set(document) == {"schema_version", "type", "value"}
        and type(document["schema_version"]) is int
        and document["schema_version"] == 1
        and isinstance(document["type"], str)
        and document["type"] in _LEGACY_KINDS
    ):
        return _decode({"type": document["type"], "value": document["value"]})
    _check_document(document, set())
    return document


def read_document(path: Path) -> Any:
    """Read ordinary JSON/YAML without interpreting CTK persistence envelopes."""
    if path.suffix.lower() not in {".json", ".yaml", ".yml"}:
        raise PersistenceError("read requires a .json, .yaml or .yml file")
    try:
        with path.open(encoding="utf-8") as handle:
            value = json.load(handle) if path.suffix.lower() == ".json" else yaml.safe_load(handle)
        _check_document(value, set())
        return value
    except (OSError, ValueError, RecursionError, yaml.YAMLError) as exc:
        raise PersistenceError(f"cannot read {path}: {exc}") from exc


def _check_document(value: Any, ancestors: set[int]) -> None:
    # YAML aliases may form cycles, which console field traversal cannot render.
    if not isinstance(value, (dict, list)):
        return
    identity = id(value)
    if identity in ancestors:
        raise PersistenceError("recursive YAML aliases are not supported")
    ancestors.add(identity)
    try:
        for item in value.values() if isinstance(value, dict) else value:
            _check_document(item, ancestors)
    finally:
        ancestors.remove(identity)
