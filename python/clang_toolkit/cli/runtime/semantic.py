"""Read-only, descriptor-driven views over copied protobuf semantic values."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from itertools import islice
from typing import Any

from google.protobuf.descriptor import FieldDescriptor
from google.protobuf.message import Message


class SemanticError(ValueError):
    """A semantic protobuf field is absent, unsupported, or incorrectly indexed."""


@dataclass(frozen=True)
class EnumValue:
    name: str
    number: int

    def __str__(self) -> str:
        return self.name


@dataclass(frozen=True)
class MessageView:
    """A protobuf message snapshot exposed only through its descriptor fields."""

    _data: bytes
    _message_type: type[Message]
    _availability: tuple[tuple[str, int | None, str | None], ...] = ()
    _path: str = ""

    def _message(self) -> Message:
        message = self._message_type()
        message.ParseFromString(self._data)
        return message

    @property
    def descriptor(self):
        return self._message_type.DESCRIPTOR


@dataclass(frozen=True)
class RepeatedView:
    _data: bytes
    _message_type: type[Message]
    _field_name: str
    _availability: tuple[tuple[str, int | None, str | None], ...] = ()
    _path: str = ""

    def __len__(self) -> int:
        return len(getattr(_parse(self._data, self._message_type), self._field_name))

    def __iter__(self) -> Iterator[Any]:
        field = self._message_type.DESCRIPTOR.fields_by_name[self._field_name]
        parent = _parse(self._data, self._message_type)
        for i, value in enumerate(getattr(parent, self._field_name)):
            yield _convert(value, field, self._availability, f"{self._path}[{i}]")


@dataclass(frozen=True)
class MapView:
    _data: bytes
    _message_type: type[Message]
    _field_name: str
    _availability: tuple[tuple[str, int | None, str | None], ...] = ()
    _path: str = ""

    def __len__(self) -> int:
        return len(getattr(_parse(self._data, self._message_type), self._field_name))

    def __iter__(self) -> Iterator[Any]:
        return iter(getattr(_parse(self._data, self._message_type), self._field_name))


@dataclass(frozen=True)
class BindingMapView:
    """Explicit row binding lookup that returns native continuation selectors."""

    _row: Any

    def __len__(self) -> int:
        return len(self._row.bindings)

    def __iter__(self) -> Iterator[str]:
        return iter(self._row.bindings)


def _parse(data: bytes, message_type: type[Message]) -> Message:
    message = message_type()
    message.ParseFromString(data)
    return message


def _availability_of(value: Message) -> tuple[tuple[str, int | None, str | None], ...]:
    field = value.DESCRIPTOR.fields_by_name.get("availability")
    if field is None or not field.is_repeated:
        return ()
    items = []
    for entry in getattr(value, "availability"):
        path = entry.field_path if entry.HasField("field_path") else ""
        state = entry.state if entry.HasField("state") else None
        reason = entry.reason if entry.HasField("reason") else None
        items.append((path, state, reason))
    return tuple(items)


def _is_synthetic_oneof(field: FieldDescriptor) -> bool:
    oneof = field.containing_oneof
    return bool(oneof and oneof.name == f"_{field.name}" and len(oneof.fields) == 1)


def view(value: Message | MessageView) -> MessageView:
    if isinstance(value, MessageView):
        return value
    if not isinstance(value, Message):
        raise SemanticError(f"expected a protobuf message, got {type(value).__name__}")
    return MessageView(value.SerializeToString(), type(value), _availability_of(value), value.DESCRIPTOR.full_name)


def is_semantic_view(value: Any) -> bool:
    return isinstance(value, (MessageView, RepeatedView, MapView, BindingMapView, EnumValue))


def _availability_error(view_value: MessageView, field_name: str) -> str | None:
    path = f"{view_value._path}.{field_name}" if view_value._path else field_name
    path_parts = tuple(part for part in path.split(".") if part)
    for candidate, state, reason in view_value._availability:
        message_name = view_value.descriptor.name
        candidate_parts = tuple(part for part in (candidate or "").split(".") if part)
        # Availability paths are rooted at the serialized AST node, whereas
        # views retain descriptor names in their internal path. Compare the
        # meaningful suffix so nested paths such as
        # function_decl.function.parameters still match after projection.
        path_matches = (
            candidate == path
            or candidate == field_name
            or candidate == f"{message_name}.{field_name}"
            or candidate == f"{view_value.descriptor.full_name}.{field_name}"
            or bool(candidate_parts and len(candidate_parts) <= len(path_parts)
                    and path_parts[-len(candidate_parts):] == candidate_parts)
        )
        if path_matches:
            detail = f" ({reason})" if reason else ""
            if state == 2:
                return f"field is semantically absent: {path}{detail}"
            if state == 3:
                return f"field was not requested: {path}{detail}"
            if state == 4:
                return f"field is inapplicable: {path}{detail}"
            if state in (5, 6):
                return f"field is unavailable: {path}{detail}"
            if state == 0:
                return f"field state is unspecified: {path}{detail}"
    return None


_AST_NODE_TYPE = "ctk.ast.v1.AstNode"
_AST_BASE_FIELDS = {
    "ctk.ast.v1.FunctionDecl": "function",
    "ctk.ast.v1.CXXMethodDecl": "method",
    "ctk.ast.v1.CXXConstructorDecl": "method",
    "ctk.ast.v1.CXXDeductionGuideDecl": "function",
    "ctk.ast.v1.CXXDestructorDecl": "method",
    "ctk.ast.v1.CXXConversionDecl": "method",
    "ctk.ast.v1.CXXMethodDeclInfo": "function",
    "ctk.ast.v1.FunctionDeclInfo": "declarator",
    "ctk.ast.v1.DeclaratorDeclInfo": "value",
    "ctk.ast.v1.ValueDeclInfo": "named",
    "ctk.ast.v1.NamedDeclInfo": "declaration",
}


def _read_direct_field(value: MessageView, descriptor: FieldDescriptor) -> Any:
    """Read one field from its schema owner, without applying alias lookup."""
    name = descriptor.name
    message = value._message()
    field_path = f"{value._path}.{name}" if value._path else name
    availability_error = _availability_error(value, name)
    if availability_error is not None:
        raise SemanticError(availability_error)
    if descriptor.is_repeated:
        data = value._data
        if descriptor.message_type is not None and descriptor.message_type.GetOptions().map_entry:
            return MapView(data, value._message_type, name, value._availability, field_path)
        return RepeatedView(data, value._message_type, name, value._availability, field_path)
    if descriptor.containing_oneof is not None and not _is_synthetic_oneof(descriptor):
        active = message.WhichOneof(descriptor.containing_oneof.name)
        if active != name:
            if value.descriptor.full_name == "ctk.match.v1.MatchBinding" and active == "unsupported":
                detail = message.unsupported.detail if message.unsupported.HasField("detail") else "unsupported value kind"
                raise SemanticError(f"unsupported semantic payload: {detail}")
            raise SemanticError(_availability_error(value, name) or f"inactive oneof field: {field_path}")
    elif descriptor.has_presence and not message.HasField(name):
        raise SemanticError(_availability_error(value, name) or f"field is absent: {field_path}")
    return _convert(getattr(message, name), descriptor, value._availability, field_path)


def field_sources(
    value: MessageView, *, include_inactive: bool = False
) -> dict[str, tuple[MessageView, FieldDescriptor]]:
    """Map visible direct and explicitly inherited names to their schema owners.

    AST aliases follow only the known declaration field-1 base chain. The raw
    protobuf path remains available because every alias retains its real owner.
    """
    if not isinstance(value, MessageView):
        return {}

    sources: dict[str, tuple[MessageView, FieldDescriptor]] = {}
    shadowed: set[str] = set()

    def add_owner(owner: MessageView, message: Message) -> None:
        for descriptor in owner.descriptor.fields:
            if descriptor.name in shadowed:
                continue
            oneof = descriptor.containing_oneof
            inactive = (
                oneof is not None
                and not _is_synthetic_oneof(descriptor)
                and message.WhichOneof(oneof.name) != descriptor.name
            )
            if include_inactive or not inactive:
                sources[descriptor.name] = (owner, descriptor)
        # Even inactive direct schema fields reserve their names. A deeper
        # alias must not make an inactive field appear to belong to another
        # message in this flattened view.
        shadowed.update(field.name for field in owner.descriptor.fields)

    root_message = value._message()
    add_owner(value, root_message)
    current = value
    if value.descriptor.full_name == _AST_NODE_TYPE:
        active_payload = root_message.WhichOneof("payload")
        if active_payload is None:
            return sources
        payload_descriptor = value.descriptor.fields_by_name[active_payload]
        try:
            payload = _read_direct_field(value, payload_descriptor)
        except SemanticError:
            return sources
        if not isinstance(payload, MessageView):
            return sources
        current = payload

    visited: set[str] = set()
    while current.descriptor.full_name not in visited:
        message_type = current.descriptor.full_name
        visited.add(message_type)
        message = current._message()
        add_owner(current, message)
        base_name = _AST_BASE_FIELDS.get(message_type)
        if base_name is None:
            break
        base_descriptor = current.descriptor.fields_by_name.get(base_name)
        if base_descriptor is None:
            break
        try:
            base_value = _read_direct_field(current, base_descriptor)
        except SemanticError:
            break
        if not isinstance(base_value, MessageView):
            break
        current = base_value
    return sources


def _field_value(value: MessageView, name: str) -> Any:
    source = field_sources(value, include_inactive=True).get(name)
    if source is None:
        raise SemanticError(f"unknown semantic field: {name}")
    owner, descriptor = source
    return _read_direct_field(owner, descriptor)


def _convert(value: Any, field: FieldDescriptor, availability: tuple[tuple[str, int | None, str | None], ...], path: str) -> Any:
    if field.message_type is not None:
        # Semantic availability can be carried on the nested AstNode itself;
        # keep both binding-level and node-level records as the view descends.
        nested_availability = availability + _availability_of(value)
        return MessageView(value.SerializeToString(), type(value), nested_availability, path)
    if field.enum_type is not None:
        number = int(value)
        enum = field.enum_type.values_by_number.get(number)
        return EnumValue(enum.name if enum is not None else f"UNKNOWN_{number}", number)
    return value


def field_names(value: Any) -> tuple[str, ...]:
    if isinstance(value, MessageView):
        names = []
        for name, (owner, descriptor) in field_sources(value).items():
            unavailable = _availability_error(owner, descriptor.name)
            if unavailable is None or not unavailable.startswith("field was not requested:"):
                names.append(name)
        return tuple(names) + ("hasField",)
    if isinstance(value, EnumValue):
        return ("name", "number")
    if isinstance(value, (RepeatedView, MapView, BindingMapView)):
        return ("length", "isEmpty")
    return ()


def index_value(value: Any, key: Any) -> Any:
    if isinstance(value, MessageView):
        if not isinstance(key, str):
            raise SemanticError("semantic message fields require a string key")
        return _field_value(value, key)
    if isinstance(value, MapView):
        if not isinstance(key, str):
            raise SemanticError("semantic map keys must be strings")
        field = value._message_type.DESCRIPTOR.fields_by_name[value._field_name]
        parent = _parse(value._data, value._message_type)
        mapping = getattr(parent, value._field_name)
        if key not in mapping:
            raise SemanticError(f"unknown semantic map key: {key}")
        entry_field = field.message_type.fields_by_name["value"]
        return _convert(mapping[key], entry_field, value._availability, f'{value._path}[{key!r}]')
    if isinstance(value, BindingMapView):
        if not isinstance(key, str):
            raise SemanticError("binding map keys must be strings")
        try:
            return value._row.binding(key)
        except (KeyError, ValueError) as error:
            raise SemanticError(f"unknown binding: {key}") from error
    if isinstance(value, RepeatedView):
        if type(key) is not int or key < 0:
            raise SemanticError("semantic repeated index must be a nonnegative integer")
        field = value._message_type.DESCRIPTOR.fields_by_name[value._field_name]
        sequence = getattr(_parse(value._data, value._message_type), value._field_name)
        if key >= len(sequence):
            raise SemanticError(f"semantic repeated index out of range: {key}")
        return _convert(sequence[key], field, value._availability, f"{value._path}[{key}]")
    if isinstance(value, EnumValue) and key in ("name", "number"):
        return getattr(value, key)
    if isinstance(value, (list, tuple, str, Mapping)):
        if type(key) is int and isinstance(value, (list, tuple, str)):
            return value[key]
        if isinstance(key, str) and isinstance(value, Mapping):
            return value[key]
    raise SemanticError(f"value does not support indexing: {type(value).__name__}")


def property_value(value: Any, name: str) -> Any:
    if isinstance(value, MessageView):
        return _field_value(value, name)
    if isinstance(value, EnumValue) and name in ("name", "number"):
        return getattr(value, name)
    if isinstance(value, (RepeatedView, MapView, BindingMapView)) and name in ("length", "isEmpty"):
        size = len(value)
        return size if name == "length" else size == 0
    raise SemanticError(f"unknown field: {name}")


def call_method(value: Any, name: str, arguments: list[Any]) -> Any:
    if isinstance(value, MessageView) and name == "hasField":
        if len(arguments) != 1 or not isinstance(arguments[0], str):
            raise SemanticError("hasField requires one string field name")
        source = field_sources(value, include_inactive=True).get(arguments[0])
        if source is None:
            raise SemanticError(f"unknown semantic field: {arguments[0]}")
        owner, descriptor = source
        availability_error = _availability_error(owner, descriptor.name)
        if availability_error is not None and availability_error.startswith("field was not requested:"):
            return False
        if not descriptor.has_presence:
            raise SemanticError(f"field has no presence: {arguments[0]}")
        message = owner._message()
        if descriptor.containing_oneof is not None and not _is_synthetic_oneof(descriptor):
            return message.WhichOneof(descriptor.containing_oneof.name) == descriptor.name
        return message.HasField(descriptor.name)
    raise SemanticError(f"unknown method: {name}")


def inspect_value(value: Any, *, max_depth: int = 3, max_items: int = 20) -> Any:
    """Return a JSON-compatible, bounded representation for console inspection."""
    def walk(item: Any, depth: int) -> Any:
        if isinstance(item, EnumValue):
            return {"name": item.name, "number": item.number}
        if isinstance(item, MessageView):
            if depth >= max_depth:
                return {"type": item.descriptor.full_name, "truncated": True}
            fields: dict[str, Any] = {}
            sources = field_sources(item)
            # Stable alphabetical selection keeps useful aliases from a
            # deep base descriptor visible even when max_items is small.
            names = tuple(
                name for name in sorted(sources)
                if not (
                    (error := _availability_error(sources[name][0], sources[name][1].name)) is not None
                    and error.startswith("field was not requested:")
                )
            )
            for name in names[:max_items]:
                try:
                    owner, descriptor = sources[name]
                    fields[name] = walk(_read_direct_field(owner, descriptor), depth + 1)
                except SemanticError as error:
                    fields[name] = {"unavailable": str(error)}
            if len(names) > max_items:
                fields["…"] = "fields truncated"
            active = {oneof.name: item._message().WhichOneof(oneof.name) for oneof in item.descriptor.oneofs}
            return {"type": item.descriptor.full_name, "fields": fields, "active_oneof": active,
                    "methods": ["hasField"]}
        if isinstance(item, BindingMapView):
            count = len(item)
            names = list(islice(iter(item), max_items))
            result = [{name[:256]: walk(index_value(item, name), depth + 1)} for name in names]
            if count > len(names):
                result.append({"truncated": count - len(names)})
            return result
        if isinstance(item, (RepeatedView, MapView)):
            count = len(item)
            limit = min(count, max_items)
            if depth >= max_depth:
                return {"length": count, "truncated": True}
            items = [walk(index_value(item, i), depth + 1) for i in range(limit)] if isinstance(item, RepeatedView) else [
                {key[:256]: walk(index_value(item, key), depth + 1)} for key in islice(iter(item), limit)
            ]
            if count > limit:
                items.append({"truncated": count - limit})
            return items
        if isinstance(item, bytes):
            if len(item) > 128:
                return {"hex_prefix": item[:128].hex(), "truncated_bytes": len(item) - 128}
            return item.hex()
        if isinstance(item, str) and len(item) > 256:
            return item[:256] + "…"
        return item

    return walk(value, 0)
