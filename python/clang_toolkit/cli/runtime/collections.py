"""Mutable collection helpers for console-owned Python values."""

from __future__ import annotations

from typing import Any

from .references import ReferenceError


def ensure_insertable(target: list[Any] | dict[str, Any], value: Any) -> None:
    """Reject a value that would make a console collection recursive."""
    target_id = id(target)
    active: set[int] = set()
    complete: set[int] = set()

    def visit(item: Any) -> None:
        if not isinstance(item, (list, dict)):
            return
        identity = id(item)
        if identity == target_id:
            raise ReferenceError("cannot create a cyclic collection")
        if identity in active:
            raise ReferenceError("cannot insert a cyclic collection")
        if identity in complete:
            return
        active.add(identity)
        children = item.values() if isinstance(item, dict) else item
        for child in children:
            visit(child)
        active.remove(identity)
        complete.add(identity)

    visit(value)


def mutable_index_target(value: Any, key: Any) -> None:
    if type(value) is dict:
        if not isinstance(key, str):
            raise ReferenceError("dictionary keys must be strings")
        return
    if type(value) is list:
        if type(key) is not int or key < 0:
            raise ReferenceError("list index must be a nonnegative integer")
        return
    raise ReferenceError("collection item assignment requires a mutable list or dictionary")
