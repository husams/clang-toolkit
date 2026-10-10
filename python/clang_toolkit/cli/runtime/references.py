"""Typed property, method, and index access for runtime values."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from itertools import islice
from typing import Any

from .filesystem import FileSystemEntry
from clang_toolkit.resources import FileBatch, FileHandle, FileSet, InputDescriptor
from .values import MatchSet, render
from .semantic import (
    BindingMapView,
    SemanticError,
    call_method as semantic_call_method,
    field_names as semantic_field_names,
    field_sources,
    index_value as semantic_index_value,
    inspect_value as semantic_inspect_value,
    property_value as semantic_property_value,
    is_semantic_view,
    view as semantic_view,
)
from clang_toolkit.match_values import (
    BindingSelection, MatchRow, MatchValue, MatchValueError, NativeBindingCollection,
    NativeMatchCollection, ParsedTree,
)


class ReferenceError(ValueError):
    """A property, method, or index is unavailable for a value."""


_FILE_PROPERTIES = frozenset({"size", "modified", "basename", "dirname", "absolute", "parts"})
_BINDING_SELECTOR_PROPERTIES = frozenset({
    "name", "source_file", "scope", "value", "decl_name", "decl_type",
    "parameter_name", "record_name", "type_name", "location", "range",
    "symbol_identity", "documentation", "call_site",
})


def _binding_keys(value: BindingSelection) -> list[str]:
    """Discover readable AST properties rather than the native binding carrier."""
    semantic = semantic_view(value.value)
    sources = field_sources(semantic)
    keys = []
    readable = semantic_property_value(semantic, "keys")
    readable.sort(key=lambda name: sources[name][0].descriptor.full_name == "ctk.match.v1.MatchBinding")
    for name in readable:
        owner, descriptor = sources[name]
        if owner.descriptor.full_name == "ctk.match.v1.MatchBinding" and (
            descriptor.containing_oneof is not None
            or name in {"availability", "is_complete", "supported_scopes"}
        ):
            continue
        if owner.descriptor.full_name == "ctk.ast.v1.AstNode" and name == "availability":
            continue
        keys.append(name)
    # Selector conveniences are useful direct properties too, but only list
    # them when their declaration/type data is readable in this projection.
    for source_names, aliases in (
        (("qualified_name", "name"), ("decl_name", "parameter_name", "record_name")),
        (("declared_type", "type", "description"), ("decl_type", "type_name")),
    ):
        if not any(name in keys for name in source_names):
            continue
        for name in aliases:
            if getattr(value, name) is not None and name not in keys:
                keys.append(name)
    return keys


def property_value(value: Any, name: str) -> Any:
    if isinstance(value, FileSet) and name in {"length", "isEmpty"}:
        return len(value) if name == "length" else not len(value)
    if isinstance(value, FileBatch) and name == "paths":
        return value.paths
    if isinstance(value, FileHandle) and name in {"path", "profile_id"}:
        return getattr(value, name)
    if isinstance(value, MatchSet):
        if name == "length":
            return len(value.rows)
        if name == "isEmpty":
            return not value.rows
        if name == "rows":
            return value.rows
        raise ReferenceError(f"unknown field: {name}")
    if isinstance(value, NativeMatchCollection):
        if name == "rows":
            return value
        if name == "length":
            return len(value)
        if name == "isEmpty":
            return not len(value)
        if name in value.binding_names():
            try:
                return value.binding(name)
            except MatchValueError as error:
                raise ReferenceError(str(error)) from error
        raise ReferenceError("select a row before accessing a binding on a multi-file result")
    if isinstance(value, NativeBindingCollection):
        if name == "rows":
            return value
        if name == "length":
            return len(value)
        if name == "isEmpty":
            return not len(value)
        raise ReferenceError("select a binding selection before accessing its value")
    if isinstance(value, MatchValue):
        if name == "rows":
            return value.rows
        if name == "source_file":
            return value.source_file
        if name == "length":
            return len(value)
        if name == "isEmpty":
            return not len(value)
        return value.binding(name)
    if isinstance(value, MatchRow):
        if name == "bindings":
            return BindingMapView(value)
        if name == "source_match_index":
            return value.source_match_index
        if name == "source_file":
            return value.source_file
        return value.binding(name)
    if isinstance(value, BindingSelection):
        if name == "keys":
            try:
                return _binding_keys(value)
            except (SemanticError, MatchValueError) as error:
                raise ReferenceError(str(error)) from error
        if name == "name":
            return value.name
        if name == "source_file":
            return value.source_file
        if name in {
            "decl_name", "parameter_name", "record_name", "decl_type", "type_name"
        }:
            return getattr(value, name)
        if name == "scope":
            return value.scope
        if name == "value":
            try:
                return semantic_view(value.value)
            except MatchValueError as error:
                raise ReferenceError(str(error)) from error
        if name in {"location", "range", "symbol_identity", "documentation", "call_site"}:
            try:
                return semantic_property_value(semantic_view(value.value), name)
            except (SemanticError, MatchValueError) as error:
                raise ReferenceError(str(error)) from error
        try:
            return semantic_property_value(semantic_view(value.value), name)
        except (SemanticError, MatchValueError) as error:
            raise ReferenceError(str(error)) from error
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
    if type(value) is dict:
        if name == "keys":
            return list(value)
        if name == "values":
            return list(value.values())
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
    if isinstance(value, BindingSelection) and name in {"hasField", "fieldState", "fieldOr"}:
        try:
            return semantic_call_method(semantic_view(value.value), name, arguments)
        except (SemanticError, MatchValueError) as error:
            raise ReferenceError(str(error)) from error
    try:
        return semantic_call_method(value, name, arguments)
    except SemanticError as error:
        if name in {"hasField", "fieldState", "fieldOr"}:
            raise ReferenceError(str(error)) from error
    if isinstance(value, list):
        from .collections import ensure_insertable

        if name == "push":
            if len(arguments) != 1:
                raise ReferenceError("push requires one value")
            ensure_insertable(value, arguments[0])
            value.append(arguments[0])
            return value
        if name == "pop":
            if len(arguments) > 1 or (arguments and type(arguments[0]) is not int):
                raise ReferenceError("pop accepts an optional integer index")
            if not value:
                raise ReferenceError("cannot pop from an empty list")
            index = arguments[0] if arguments else -1
            try:
                return value.pop(index)
            except IndexError as error:
                raise ReferenceError("list pop index is out of range") from error
        if name == "insert":
            if len(arguments) != 2 or type(arguments[0]) is not int:
                raise ReferenceError("insert requires an integer index and a value")
            ensure_insertable(value, arguments[1])
            if arguments[0] < 0 or arguments[0] > len(value):
                raise ReferenceError("list insert index is out of range")
            value.insert(arguments[0], arguments[1])
            return value
        if name == "remove":
            if len(arguments) != 1:
                raise ReferenceError("remove requires one value")
            try:
                value.remove(arguments[0])
            except ValueError as error:
                raise ReferenceError("list value was not found") from error
            return value
        if name == "clear":
            if arguments:
                raise ReferenceError("clear takes no arguments")
            value.clear()
            return value
    if type(value) is dict:
        from .collections import ensure_insertable

        if name == "get":
            if len(arguments) not in {1, 2} or not isinstance(arguments[0], str):
                raise ReferenceError("get requires a string key and optional default")
            return value.get(*arguments)
        if name == "set":
            if len(arguments) != 2 or not isinstance(arguments[0], str):
                raise ReferenceError("set requires a string key and a value")
            ensure_insertable(value, arguments[1])
            value[arguments[0]] = arguments[1]
            return arguments[1]
        if name in {"delete", "hasKey"}:
            if len(arguments) != 1 or not isinstance(arguments[0], str):
                raise ReferenceError(f"{name} requires one string key")
            if name == "hasKey":
                return arguments[0] in value
            if arguments[0] not in value:
                raise ReferenceError(f"dictionary key not found: {arguments[0]}")
            return value.pop(arguments[0])
        if name == "clear":
            if arguments:
                raise ReferenceError("clear takes no arguments")
            value.clear()
            return value
    if name == "joinWith" and isinstance(value, list):
        if len(arguments) != 1 or not isinstance(arguments[0], str):
            raise ReferenceError("joinWith requires one string separator")
        return arguments[0].join(render(item) for item in value)
    if name in {"unique", "sort", "filter"} and isinstance(
        value, (MatchValue, NativeMatchCollection, MatchSet, list)
    ):
        if name == "filter":
            if len(arguments) != 2 or not isinstance(arguments[0], str):
                raise ReferenceError("filter requires a field selector and expected value")
            selector, expected = arguments
        else:
            if len(arguments) != 1 or not isinstance(arguments[0], str):
                raise ReferenceError(f"{name} requires one string field selector")
            selector, expected = arguments[0], None
        if isinstance(value, MatchValue):
            rows = list(value.iter_rows())
        elif isinstance(value, NativeMatchCollection):
            rows = list(value)
        elif isinstance(value, MatchSet):
            rows = list(value.rows)
        else:
            rows = list(value)
        selected = [(row, _selector_value(row, selector)) for row in rows]
        if name == "filter":
            return [row for row, item in selected if _matches(item, expected)]
        if name == "unique":
            seen: set[Any] = set()
            result = []
            for row, item in selected:
                key = _freeze(item)
                if key not in seen:
                    seen.add(key)
                    result.append(row)
            return result
        try:
            return [row for row, _ in sorted(
                selected, key=lambda pair: _sort_key(pair[1])
            )]
        except (TypeError, ValueError) as error:
            raise ReferenceError(f"sort selector is not orderable: {error}") from error
    raise ReferenceError(f"unknown method: {name}")


def _selector_value(value: Any, selector: str) -> Any:
    current = value
    for component in selector.split("."):
        if not component:
            raise ReferenceError("field selector cannot contain an empty component")
        if isinstance(current, Mapping) and component in current:
            current = current[component]
        else:
            current = property_value(current, component)
    return current


def _freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return tuple(sorted((str(key), _freeze(item)) for key, item in value.items()))
    if isinstance(value, list | tuple):
        return tuple(_freeze(item) for item in value)
    if hasattr(value, "_data") and isinstance(value._data, bytes):
        return (type(value).__name__, value._data)
    try:
        hash(value)
    except TypeError:
        return json.dumps(value, sort_keys=True, default=str)
    return value


def _matches(value: Any, expected: Any) -> bool:
    if hasattr(value, "name") and type(getattr(value, "name")) is str:
        value = value.name
    return value == expected or str(value) == str(expected)


def _sort_key(value: Any) -> tuple[Any, ...]:
    if hasattr(value, "name") and type(getattr(value, "name")) is str:
        value = value.name
    if value is None:
        return (0,)
    if type(value) is bool:
        return (1, int(value))
    if type(value) in {int, float}:
        if type(value) is float and math.isnan(value):
            return (2, 1, repr(value))
        return (2, 0, value)
    if isinstance(value, str):
        return (3, value)
    return (4, type(value).__module__, type(value).__qualname__, str(value))


def index_value(value: Any, key: Any) -> Any:
    if type(value) is dict:
        if not isinstance(key, str):
            raise ReferenceError("dictionary keys must be strings")
        if key not in value:
            raise ReferenceError(f"dictionary key not found: {key}")
        return value[key]
    if type(value) is list:
        if type(key) is not int or key < 0:
            raise ReferenceError("list index must be a nonnegative integer")
        try:
            return value[key]
        except IndexError as error:
            raise ReferenceError("list index is out of range") from error
    if type(key) is int and key < 0:
        raise ReferenceError("index must be a nonnegative zero-based integer or string key")
    if type(key) is not int and not isinstance(key, str):
        raise ReferenceError("index must be a nonnegative zero-based integer or string key")
    if isinstance(value, MatchSet):
        if type(key) is not int or key < 0 or key >= len(value.rows):
            raise ReferenceError("match row index must be a valid zero-based integer")
        return value.rows[key]
    if isinstance(value, MatchValue | NativeMatchCollection | NativeBindingCollection):
        try:
            return value[key]
        except (IndexError, ValueError, TypeError) as error:
            raise ReferenceError(str(error)) from error
    if isinstance(value, BindingSelection):
        try:
            if isinstance(key, str) and key in {
                "decl_name", "parameter_name", "record_name", "decl_type", "type_name"
            } and key in _binding_keys(value):
                return getattr(value, key)
            return semantic_index_value(semantic_view(value.value), key)
        except (SemanticError, MatchValueError, IndexError, KeyError, TypeError) as error:
            raise ReferenceError(str(error)) from error
    try:
        return semantic_index_value(value, key)
    except (SemanticError, IndexError, KeyError, TypeError) as error:
        raise ReferenceError(str(error)) from error


def field_names(value: Any) -> tuple[str, ...]:
    if isinstance(value, FileSet):
        return ("inputs", "diagnostics", "metadata_bytes", "length", "isEmpty")
    if isinstance(value, FileBatch):
        return ("index", "length", "inputs", "paths")
    if isinstance(value, FileHandle):
        return ("path", "profile_id", "source_revision", "snapshot_id", "state")
    if isinstance(value, InputDescriptor):
        return tuple(value.__dataclass_fields__)
    if isinstance(value, MatchSet):
        return ("length", "isEmpty", "unique", "sort", "filter")
    if isinstance(value, MatchValue):
        return ("length", "isEmpty", "unique", "sort", "filter",
                *tuple(sorted(value.binding_names())))
    if isinstance(value, NativeMatchCollection):
        return ("length", "isEmpty", "rows", "unique", "sort", "filter",
                *tuple(sorted(value.binding_names())))
    if isinstance(value, NativeBindingCollection):
        return ("length", "isEmpty", "rows")
    if isinstance(value, MatchRow):
        return tuple(sorted(value.bindings)) + ("bindings", "source_match_index", "source_file")
    if isinstance(value, BindingSelection):
        metadata = (
            "name", "value", "scope", "source_file", "decl_name", "decl_type",
            "parameter_name", "record_name", "type_name", "location", "range",
            "symbol_identity", "documentation", "call_site",
        )
        semantic_fields: tuple[str, ...] = ()
        if value._binding_data is not None and value._index is not None:
            try:
                semantic_fields = tuple(
                    name for name in semantic_field_names(semantic_view(value.value))
                    if name not in _BINDING_SELECTOR_PROPERTIES
                )
            except (SemanticError, MatchValueError):
                pass
        return (*metadata, *semantic_fields)
    if isinstance(value, list):
        return ("length", "isEmpty", "push", "pop", "insert", "remove", "clear", "joinWith", "unique", "sort", "filter")
    if type(value) is dict:
        keys = tuple(str(key) for key in value)
        properties = tuple(
            name for name in ("keys", "values", "length", "isEmpty")
            if name not in value
        )
        methods = ("get", "set", "delete", "hasKey", "clear")
        return (*keys, *properties, *methods)
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
    if isinstance(value, FileSet):
        return {
            "type": "FileSet",
            "input_count": len(value),
            "diagnostics": list(value.diagnostics[:20]),
            "metadata_bytes": value.metadata_bytes,
        }
    if isinstance(value, FileBatch):
        return {"type": "FileBatch", "index": value.index, "length": value.length,
                "paths": list(value.paths[:20])}
    if isinstance(value, FileHandle):
        return {"type": "FileHandle", "lease_id": value.lease_id,
                "path": value.path, "profile_id": value.profile_id,
                "source_revision": value.source_revision, "state": value.state}
    if isinstance(value, InputDescriptor):
        return {"type": "InputDescriptor", "path": value.path,
                "profile_id": value.profile_id,
                "estimated_parse_bytes": value.estimated_parse_bytes}
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
    if isinstance(value, MatchValue | NativeMatchCollection | NativeBindingCollection):
        names = sorted(value.binding_names())
        try:
            rows = [inspect_value(row) for row in islice(iter(value), 20)]
            result = {
                "type": "NativeBindingCollection" if isinstance(value, NativeBindingCollection)
                else "MatchValue",
                "length": len(value), "binding_names": names[:100], "rows": rows,
            }
            if len(value) > len(rows):
                result["truncated_rows"] = len(value) - len(rows)
            if len(names) > 100:
                result["truncated_binding_names"] = len(names) - 100
            return result
        except (ValueError, RuntimeError) as error:
            return {"type": "MatchValue", "unavailable": str(error)}
    if isinstance(value, MatchSet):
        return {"type": "MatchSet", "length": len(value.rows),
                "rows": [_bounded_inspection(row) for row in value.rows[:20]]}
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
