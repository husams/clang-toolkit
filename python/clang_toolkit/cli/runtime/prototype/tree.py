"""Reference tree-walking execution engine for the prototype language."""

from __future__ import annotations

from typing import Any

from .semantics import Context, Node, eval_program


def evaluate(program: Node, context: Context) -> Any:
    """Evaluate *program* using the reference interpreter."""
    return eval_program(context, program)
