"""Shared selection rules for finite console collections."""

from __future__ import annotations

from typing import Any


OMITTED = object()


def selection_sequence(value: Any) -> Any:
    """Return only known finite collections, never consume arbitrary iterators."""
    from clang_toolkit.match_values import (
        MatchValue, NativeBindingCollection, NativeMatchCollection,
    )
    from ..semantic import RepeatedView
    from ..values import MatchSet

    if isinstance(value, MatchSet):
        return value.rows
    if isinstance(value, (list, tuple, MatchValue, NativeMatchCollection,
                          NativeBindingCollection, RepeatedView)):
        return value
    raise TypeError("selection requires a finite list, tuple, or supported collection view")


def make_slice(start: Any, stop: Any, step: Any) -> slice:
    bounds = []
    for name, value in zip(("start", "stop", "step"), (start, stop, step), strict=True):
        if value is OMITTED:
            bounds.append(None)
        elif type(value) is not int:
            raise TypeError(f"slice {name} must be an integer")
        else:
            bounds.append(value)
    if bounds[2] == 0:
        raise ValueError("slice step must not be zero")
    return slice(*bounds)


def normalized_index(key: Any, length: int) -> int:
    if type(key) is not int:
        raise TypeError("sequence index must be an integer")
    original = key
    if key < 0:
        key += length
    if key < 0 or key >= length:
        raise IndexError(f"List index {original} is out of range for length {length}")
    return key
