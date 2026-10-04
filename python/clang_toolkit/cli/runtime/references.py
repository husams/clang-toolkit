"""Typed property and method access for runtime values."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .filesystem import FileSystemEntry
from .values import render


class ReferenceError(ValueError):
    """A property or method is unavailable for a value."""


_FILE_PROPERTIES = frozenset(
    {"size", "modified", "basename", "dirname", "absolute", "parts"}
)


def property_value(value: Any, name: str) -> Any:
    if isinstance(value, list):
        if name == "length":
            return len(value)
        if name == "isEmpty":
            return not value
    if isinstance(value, FileSystemEntry) and name in _FILE_PROPERTIES:
        return getattr(value, name)
    if isinstance(value, Mapping) and name in value:
        return value[name]
    if name in getattr(type(value), "__dataclass_fields__", {}) and not name.startswith(
        "_"
    ):
        return getattr(value, name)
    raise ReferenceError(f"unknown field: {name}")


def call_method(value: Any, name: str, arguments: list[Any]) -> Any:
    if name == "joinWith" and isinstance(value, list):
        if len(arguments) != 1 or not isinstance(arguments[0], str):
            raise ReferenceError("joinWith requires one string separator")
        return arguments[0].join(render(item) for item in value)
    raise ReferenceError(f"unknown method: {name}")
