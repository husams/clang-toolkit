"""Immutable values shared by the interactive language evaluator."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .filesystem import FileSystemEntry
from typing import Any
from clang_toolkit.match_values import (
    BindingSelection, MatchRow, MatchValue, NativeMatchCollection, ParsedTree,
)

_MAX_RENDER_CHARS = 20_000
_PREVIEW_ITEMS = 20
_PREVIEW_DEPTH = 16
_PREVIEW_STRING_CHARS = 2_048


def _bounded_proto_dict(message: Any, budget: list[int], depth: int = 0) -> Any:
    """Build a JSON-compatible protobuf preview without converting the full message."""
    from google.protobuf.descriptor import FieldDescriptor
    from google.protobuf.message import Message

    if not isinstance(message, Message):
        if isinstance(message, str):
            limit = max(0, min(_PREVIEW_STRING_CHARS, budget[0]))
            if len(message) > limit:
                budget[0] = 0
                return message[:limit] + "… <truncated>"
            budget[0] -= len(message)
        elif isinstance(message, bytes):
            budget[0] -= min(len(message), 256)
        return message
    if depth >= _PREVIEW_DEPTH or budget[0] <= 0:
        return {"…": "truncated"}
    result: dict[str, Any] = {}
    for field in message.DESCRIPTOR.fields:
        if budget[0] <= 0:
            result["…"] = "truncated"
            break
        value = getattr(message, field.name)
        if field.is_repeated:
            if not value:
                continue
            budget[0] -= len(field.name) + 4
            is_map = field.message_type is not None and field.message_type.GetOptions().map_entry
            entries_count = len(value)
            if is_map:
                from itertools import islice

                selected = list(islice(value.items(), _PREVIEW_ITEMS))
            else:
                selected = value[:_PREVIEW_ITEMS]
            if is_map:
                mapped: dict[str, Any] = {}
                value_field = field.message_type.fields_by_name["value"]
                for key_index, (key, item) in enumerate(selected):
                    if budget[0] <= 0:
                        break
                    text_key = str(key)
                    key_limit = min(_PREVIEW_STRING_CHARS, budget[0])
                    preview_key = text_key[:key_limit]
                    if len(text_key) > key_limit:
                        preview_key += f"… [key {key_index} truncated]"
                    budget[0] -= len(preview_key)
                    mapped[preview_key] = _bounded_proto_element(item, value_field, budget, depth + 1)
                if entries_count > len(selected):
                    mapped["…"] = f"{entries_count - len(selected)} entries truncated"
                result[field.name] = mapped
            else:
                items = [_bounded_proto_element(item, field, budget, depth + 1) for item in selected]
                if entries_count > len(selected):
                    items.append({"…": f"{entries_count - len(selected)} entries truncated"})
                result[field.name] = items
            continue
        if field.has_presence:
            if not message.HasField(field.name):
                continue
        elif value == field.default_value:
            continue
        budget[0] -= len(field.name) + 4
        if field.type == FieldDescriptor.TYPE_STRING:
            remaining = max(0, min(_PREVIEW_STRING_CHARS, budget[0]))
            if len(value) > remaining:
                result[field.name] = value[:remaining] + "… <truncated>"
                budget[0] = 0
            else:
                result[field.name] = value
                budget[0] -= len(value)
        elif field.type == FieldDescriptor.TYPE_BYTES:
            import base64

            result[field.name] = base64.b64encode(value[:256]).decode("ascii")
            budget[0] -= 344
            if len(value) > 256:
                result[field.name] += "… <truncated>"
        elif field.type == FieldDescriptor.TYPE_ENUM:
            enum_value = field.enum_type.values_by_number.get(int(value))
            result[field.name] = enum_value.name if enum_value is not None else int(value)
            budget[0] -= len(str(result[field.name]))
        elif field.type in {
            FieldDescriptor.TYPE_INT64, FieldDescriptor.TYPE_UINT64,
            FieldDescriptor.TYPE_SINT64, FieldDescriptor.TYPE_FIXED64,
            FieldDescriptor.TYPE_SFIXED64,
        }:
            result[field.name] = str(value)
            budget[0] -= len(str(value))
        else:
            result[field.name] = _bounded_proto_dict(value, budget, depth + 1)
            if not isinstance(value, Message):
                budget[0] -= len(str(value))
    return result


def _bounded_proto_element(value: Any, field: Any, budget: list[int], depth: int) -> Any:
    """Convert one repeated/map value using its protobuf field descriptor."""
    from google.protobuf.descriptor import FieldDescriptor
    from google.protobuf.message import Message

    if isinstance(value, Message):
        return _bounded_proto_dict(value, budget, depth)
    if field.type == FieldDescriptor.TYPE_STRING:
        limit = max(0, min(_PREVIEW_STRING_CHARS, budget[0]))
        budget[0] -= min(len(value), limit)
        return value if len(value) <= limit else value[:limit] + "… <truncated>"
    if field.type == FieldDescriptor.TYPE_BYTES:
        import base64

        result = base64.b64encode(value[:256]).decode("ascii")
        budget[0] -= min(344, len(result))
        return result if len(value) <= 256 else result + "… <truncated>"
    if field.type == FieldDescriptor.TYPE_ENUM:
        enum_value = field.enum_type.values_by_number.get(int(value))
        result = enum_value.name if enum_value is not None else int(value)
        budget[0] -= len(str(result))
        return result
    if field.type in {
        FieldDescriptor.TYPE_INT64, FieldDescriptor.TYPE_UINT64,
        FieldDescriptor.TYPE_SINT64, FieldDescriptor.TYPE_FIXED64,
        FieldDescriptor.TYPE_SFIXED64,
    }:
        budget[0] -= len(str(value))
        return str(value)
    budget[0] -= len(str(value))
    return value


def _bounded_row_dict(value: MatchRow) -> dict[str, Any]:
    """Preserve MatchResult JSON fields while bounding nested semantic payloads."""
    message = value._message()
    preview = _bounded_proto_dict(message, [16_000])
    return preview if isinstance(preview, dict) else {}


def _bounded_inspection(value: Any) -> Any:
    """Limit the total scalar content of an inspect preview before JSON encoding."""
    budget = [16_000]

    def walk(item: Any, depth: int = 0) -> Any:
        if budget[0] <= 0:
            return "… <truncated>"
        if depth >= _PREVIEW_DEPTH:
            return {"…": "maximum depth reached"}
        if isinstance(item, bytes):
            try:
                item = item.decode("utf-8")
            except UnicodeDecodeError:
                item = repr(item)
        if isinstance(item, str):
            limit = min(len(item), budget[0], _PREVIEW_STRING_CHARS)
            result = item[:limit]
            budget[0] -= limit
            return result if limit == len(item) else result + "… <truncated>"
        if isinstance(item, dict):
            result: dict[str, Any] = {}
            for key_index, (key, child) in enumerate(item.items()):
                if key_index >= _PREVIEW_ITEMS:
                    result["truncated_items"] = len(item) - key_index
                    break
                if budget[0] <= 0:
                    result["…"] = "truncated"
                    break
                text_key = str(key)
                key_limit = min(_PREVIEW_STRING_CHARS, budget[0])
                selected_key = text_key[:key_limit]
                if len(text_key) > key_limit:
                    selected_key += f"… [key {key_index} truncated]"
                budget[0] -= len(selected_key)
                result[selected_key] = walk(child, depth + 1)
            return result
        if isinstance(item, list):
            result = []
            for index, child in enumerate(item):
                if index >= _PREVIEW_ITEMS:
                    result.append({"truncated_items": len(item) - index})
                    break
                if budget[0] <= 0:
                    result.append("… <truncated>")
                    break
                result.append(walk(child, depth + 1))
            return result
        if item is None or isinstance(item, bool | int | float):
            return item
        return {"type": type(item).__name__}

    return walk(value)


def render_inspection(value: Any) -> str:
    """Render inspect output with a total display bound and plain scalar output."""
    from .references import inspect_value

    inspected = inspect_value(value)
    if isinstance(inspected, str | int | float | bool):
        rendered = render(inspected)
        return rendered if len(rendered) <= _MAX_RENDER_CHARS else rendered[: _MAX_RENDER_CHARS - 16] + "… <truncated>"
    import json

    return json.dumps(_bounded_inspection(inspected), sort_keys=True, ensure_ascii=False)


def _render_sequence(values: Any) -> str:
    """Render incrementally, stopping at the REPL display limit."""
    chunks: list[str] = []
    size = 0
    for item in values:
        chunk = render(item)
        if chunks:
            chunk = "\n" + chunk
        if size + len(chunk) > _MAX_RENDER_CHARS:
            marker = "… <truncated>"
            remaining = max(0, _MAX_RENDER_CHARS - size - len(marker))
            if remaining:
                chunks.append(chunk[:remaining])
            chunks.append(marker)
            break
        chunks.append(chunk)
        size += len(chunk)
    return "".join(chunks)


@dataclass(frozen=True)
class MatcherExpr:
    name: str
    arguments: tuple[Any, ...] = ()
    binding: str | None = None


@dataclass(frozen=True)
class QualifiedName:
    text: str


@dataclass(frozen=True)
class MatchSet:
    rows: tuple[Any, ...]


def render(value: Any) -> str:
    """Return a stable, human-readable result for the REPL output sink."""
    from clang_toolkit.resources import FileBatch, FileHandle, FileSet, InputDescriptor
    from .semantic import EnumValue, is_semantic_view, display_value

    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, EnumValue):
        return value.name
    if is_semantic_view(value):
        import json

        rendered = json.dumps(_bounded_inspection(display_value(value)), sort_keys=True, ensure_ascii=False)
        return rendered if len(rendered) <= _MAX_RENDER_CHARS else rendered[: _MAX_RENDER_CHARS - 16] + "… <truncated>"
    if isinstance(value, FileSystemEntry):
        return value.path
    if isinstance(value, FileSet):
        return f"FileSet({len(value)} inputs, {len(value.diagnostics)} diagnostics)"
    if isinstance(value, FileBatch):
        return f"FileBatch({value.index}, {value.length} inputs)"
    if isinstance(value, InputDescriptor):
        return f"{value.path} [{value.profile_id or 'default profile'}]"
    if isinstance(value, FileHandle):
        return f"FileHandle({value.path}, lease {value.lease_id})"
    if isinstance(value, MatchSet):
        return _render_sequence(value.rows)
    if isinstance(value, MatchValue):
        return _render_sequence(value.iter_rows())
    if isinstance(value, NativeMatchCollection):
        return _render_sequence(value)
    if isinstance(value, MatchRow):
        import json
        rendered = json.dumps(_bounded_row_dict(value), sort_keys=True, ensure_ascii=False)
        return rendered if len(rendered) <= _MAX_RENDER_CHARS else rendered[: _MAX_RENDER_CHARS - 16] + "… <truncated>"
    if isinstance(value, ParsedTree):
        return f"parsed {value.path}"
    if isinstance(value, BindingSelection):
        if value._index is None or value._binding_data is None:
            return f"binding {value.name}"
        from .semantic import view
        return render(view(value.value))
    if isinstance(value, list):
        return _render_sequence(value)
    if isinstance(value, bytes):
        try:
            return value.decode("utf-8")
        except UnicodeDecodeError:
            return repr(value)
    if type(value) is dict:
        import json

        rendered = json.dumps(
            _bounded_inspection(value),
            sort_keys=True, ensure_ascii=False,
        )
        return rendered if len(rendered) <= _MAX_RENDER_CHARS else rendered[: _MAX_RENDER_CHARS - 16] + "… <truncated>"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, MatcherExpr):
        return matcher_text(value)
    return str(value)


def matcher_text(value: MatcherExpr) -> str:
    """Serialize a typed matcher tree; references are resolved before this step."""
    import json

    def argument_text(argument: Any) -> str:
        if isinstance(argument, MatcherExpr):
            return matcher_text(argument)
        if isinstance(argument, QualifiedName):
            return argument.text
        if isinstance(argument, FileSystemEntry):
            return json.dumps(argument.absolute, ensure_ascii=False)
        if isinstance(argument, str):
            return json.dumps(argument, ensure_ascii=False)
        if isinstance(argument, bool):
            return "true" if argument else "false"
        if isinstance(argument, int | float):
            return str(argument)
        raise TypeError(f"unsupported matcher argument: {type(argument).__name__}")

    result = f"{value.name}({', '.join(map(argument_text, value.arguments))})"
    if value.binding is not None:
        result += f".bind({json.dumps(value.binding, ensure_ascii=False)})"
    return result
