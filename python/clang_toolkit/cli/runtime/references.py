"""Typed property, method, and index access for runtime values."""

from __future__ import annotations

from collections.abc import Mapping
from itertools import islice
from typing import Any

from .filesystem import FileSystemEntry
from .values import render
from .semantic import (
    BindingMapView,
    SemanticError,
    call_method as semantic_call_method,
    field_names as semantic_field_names,
    index_value as semantic_index_value,
    inspect_value as semantic_inspect_value,
    property_value as semantic_property_value,
    is_semantic_view,
    view as semantic_view,
)
from clang_toolkit.match_values import BindingSelection, MatchRow, MatchValue, MatchValueError, ParsedTree


class ReferenceError(ValueError):
    """A property, method, or index is unavailable for a value."""


_FILE_PROPERTIES = frozenset({"size", "modified", "basename", "dirname", "absolute", "parts"})


def property_value(value: Any, name: str) -> Any:
    if isinstance(value, MatchValue):
        if name == "length":
            return len(value)
        if name == "isEmpty":
            return not len(value)
        return value.binding(name)
    if isinstance(value, MatchRow):
        if name == "bindings":
            return BindingMapView(value)
        return value.binding(name)
    if isinstance(value, BindingSelection):
        if name == "name":
            return value.name
        if name == "scope":
            return value.scope
        if name == "value":
            try:
                return semantic_view(value.value)
            except MatchValueError as error:
                raise ReferenceError(str(error)) from error
        raise ReferenceError(f"unknown field: {name}")
    try:
        return semantic_property_value(value, name)
    except SemanticError as error:
        if is_semantic_view(value):
            raise ReferenceError(str(error)) from error
    if isinstance(value, list):
        if name == "length":
            return len(value)
        if name == "isEmpty":
            return not value
    if isinstance(value, FileSystemEntry) and name in _FILE_PROPERTIES:
        return getattr(value, name)
    if isinstance(value, Mapping) and name in value:
        return value[name]
    dataclass_fields = getattr(type(value), "__dataclass_fields__", {})
    if name in dataclass_fields and not name.startswith("_"):
        return getattr(value, name)
    raise ReferenceError(f"unknown field: {name}")


def call_method(value: Any, name: str, arguments: list[Any]) -> Any:
    try:
        return semantic_call_method(value, name, arguments)
    except SemanticError as error:
        if name == "hasField":
            raise ReferenceError(str(error)) from error
    if name == "joinWith" and isinstance(value, list):
        if len(arguments) != 1 or not isinstance(arguments[0], str):
            raise ReferenceError("joinWith requires one string separator")
        return arguments[0].join(render(item) for item in value)
    raise ReferenceError(f"unknown method: {name}")


def index_value(value: Any, key: Any) -> Any:
    if isinstance(value, MatchValue):
        try:
            return value[key]
        except (IndexError, ValueError, TypeError) as error:
            raise ReferenceError(str(error)) from error
    try:
        return semantic_index_value(value, key)
    except (SemanticError, IndexError, KeyError, TypeError) as error:
        raise ReferenceError(str(error)) from error


def field_names(value: Any) -> tuple[str, ...]:
    if isinstance(value, MatchValue):
        return ("length", "isEmpty", *tuple(sorted(value.binding_names())))
    if isinstance(value, MatchRow):
        return tuple(sorted(value.bindings)) + ("bindings",)
    if isinstance(value, BindingSelection):
        return ("name", "value", "scope")
    if isinstance(value, list):
        return ("length", "isEmpty", "joinWith")
    if isinstance(value, FileSystemEntry):
        return tuple(sorted(_FILE_PROPERTIES | {"path"}))
    if isinstance(value, Mapping):
        return tuple(str(key) for key in value)
    if not is_semantic_view(value):
        fields = getattr(type(value), "__dataclass_fields__", {})
        return tuple(name for name in fields if not name.startswith("_"))
    try:
        return semantic_field_names(value)
    except SemanticError as error:
        raise ReferenceError(str(error)) from error


def inspect_value(value: Any) -> Any:
    if isinstance(value, BindingSelection):
        result: dict[str, Any] = {
            "type": "BindingSelection",
            "name": value.name,
            "scope": value.scope,
            "row_index": value._index,
            "has_semantic_value": value._binding_data is not None,
        }
        if value._binding_data is not None:
            try:
                result["value"] = semantic_inspect_value(semantic_view(value.value))
            except (SemanticError, MatchValueError) as error:
                result["value"] = {"unavailable": str(error)}
        return result
    if isinstance(value, MatchRow):
        bindings = value.bindings
        limited = list(islice(bindings.items(), 20))
        result = {
            "type": "MatchRow",
            "source_match_index": value.source_match_index,
            "bindings": {
                name[:256]: semantic_inspect_value(semantic_view(binding))
                for name, binding in limited
            },
        }
        if len(bindings) > len(limited):
            result["truncated_bindings"] = len(bindings) - len(limited)
        return result
    if isinstance(value, MatchValue):
        names = sorted(value.binding_names())
        try:
            rows = [inspect_value(row) for row in islice(value.iter_rows(), 20)]
            result = {"type": "MatchValue", "length": len(value), "binding_names": names[:100], "rows": rows}
            if len(value) > len(rows):
                result["truncated_rows"] = len(value) - len(rows)
            if len(names) > 100:
                result["truncated_binding_names"] = len(names) - 100
            return result
        except (ValueError, RuntimeError) as error:
            return {"type": "MatchValue", "unavailable": str(error)}
    if isinstance(value, ParsedTree):
        return {"type": "ParsedTree", "path": value.path[:1024]}
    if isinstance(value, Mapping):
        items = list(islice(value.items(), 20))
        result = {str(key)[:256]: _bounded_inspection(item) for key, item in items}
        if len(value) > len(items):
            result["truncated_items"] = len(value) - len(items)
        return result
    if isinstance(value, list | tuple):
        items = list(islice(iter(value), 20))
        result = [_bounded_inspection(item) for item in items]
        if len(value) > len(items):
            result.append({"truncated": len(value) - len(items)})
        return result
    try:
        return semantic_inspect_value(value)
    except SemanticError as error:
        if is_semantic_view(value):
            raise ReferenceError(str(error)) from error
        return {"type": type(value).__name__}


def _bounded_inspection(value: Any) -> Any:
    if isinstance(value, str):
        return value[:256] + ("…" if len(value) > 256 else "")
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, Mapping):
        items = list(islice(value.items(), 20))
        result = {str(key)[:256]: _bounded_inspection(item) for key, item in items}
        if len(value) > len(items):
            result["truncated_items"] = len(value) - len(items)
        return result
    if isinstance(value, list | tuple):
        items = list(islice(iter(value), 20))
        result = [_bounded_inspection(item) for item in items]
        if len(value) > len(items):
            result.append({"truncated": len(value) - len(items)})
        return result
    return {"type": type(value).__name__}
