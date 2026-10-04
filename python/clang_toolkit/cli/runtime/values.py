"""Immutable values shared by the interactive language evaluator."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .filesystem import FileSystemEntry
from typing import Any


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
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, FileSystemEntry):
        return value.path
    if isinstance(value, MatchSet):
        return "\n".join(render(row) for row in value.rows)
    if isinstance(value, list):
        return "\n".join(render(item) for item in value)
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
