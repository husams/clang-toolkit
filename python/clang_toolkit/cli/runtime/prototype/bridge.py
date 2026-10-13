"""Adapters between the prototype runtime and the released console runtime."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol


class _Runtime(Protocol):
    def evaluate(self, source: str) -> Any: ...


def ctk_function(runtime: _Runtime) -> Callable[[str], Any]:
    """Return a host function that evaluates one console expression.

    The adapter deliberately delegates exactly once and returns the value
    unchanged.  This keeps native selection ownership with the supplied
    ``Runtime`` and prevents the prototype from gaining arbitrary Python
    evaluation or a second copy of typed handles.
    """
    evaluate = getattr(runtime, "evaluate", None)
    if not callable(evaluate):
        raise TypeError("runtime must provide a callable evaluate(source) method")

    def evaluate_source(source: str) -> Any:
        if not isinstance(source, str):
            raise TypeError("ctk expression must be a string")
        return evaluate(source)

    return evaluate_source


__all__ = ["ctk_function"]
