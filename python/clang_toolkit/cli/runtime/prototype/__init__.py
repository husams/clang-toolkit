"""Public API for the experimental scripting runtime prototype.

The parser, tree evaluator, and compiler remain separate modules so the two
execution engines can be compared directly.  This module provides the small
source-oriented convenience API used by experiments and host integrations.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from .compiler import compile_program
from .semantics import Context
from .syntax import Node, parse
from .tree import evaluate


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    """The value and observable state produced by one source execution.

    ``bindings`` and ``output`` are shallow snapshots.  Their contained
    values are intentionally left untouched so typed CTK selections and other
    native handles retain their ownership and identity.
    """

    value: Any
    bindings: dict[str, Any]
    output: list[Any]
    steps: int


def run_source(
    source: str,
    *,
    engine: str = "compiled",
    bindings: Mapping[str, Any] | None = None,
    functions: Mapping[str, Callable[..., Any]] | None = None,
    max_steps: int = 1_000_000,
    max_items: int = 10_000,
) -> ExecutionResult:
    """Parse and execute source once with a fresh :class:`Context`.

    The caller's mapping objects are never used as mutable execution state;
    host function results and native values are otherwise returned unchanged.
    """
    if not isinstance(source, str):
        raise TypeError("source must be a string")
    if engine not in {"tree", "compiled"}:
        raise ValueError(f"unknown prototype engine {engine!r}")

    program = parse(source)
    context = Context(
        bindings=dict(bindings) if bindings is not None else None,
        functions=functions,
        max_steps=max_steps,
        max_items=max_items,
    )
    if engine == "tree":
        value = evaluate(program, context)
    else:
        value = compile_program(program)(context)
    return ExecutionResult(
        value=value,
        bindings=dict(context.bindings),
        output=list(context.output),
        steps=context.steps,
    )


__all__ = [
    "Context",
    "ExecutionResult",
    "Node",
    "compile_program",
    "evaluate",
    "parse",
    "run_source",
]
