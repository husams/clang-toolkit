"""Brace interpolation compiled through the same checked Python AST engine."""

from __future__ import annotations

import ast
from collections.abc import Callable
from dataclasses import dataclass

from .semantics import Context
from .syntax import Node


@dataclass(frozen=True)
class Template:
    parts: tuple[str | Callable[[Context], object], ...]
    expressions: tuple[Node, ...]

    def render(self, context: Context) -> str:
        from clang_toolkit.cli.runtime.values import render

        return "".join(part if isinstance(part, str) else render(part(context))
                       for part in self.parts)


def _end(value: str, start: int) -> int:
    depth = 1
    quote = None
    index = start
    while index < len(value):
        char = value[index]
        if quote:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    raise ValueError("unclosed interpolation placeholder: expected `}`")


def compile_template(raw: str) -> Template | None:
    # Preserve older libraries while new scripts use bare brace expressions.
    if not raw.startswith('"') or "$" in raw or not any(c in raw for c in "{}"):
        return None
    from .compiler import compile_program
    from .repl_language import parse

    value = ast.literal_eval(raw)
    parts = []
    expressions = []
    literal = []
    index = 0
    while index < len(value):
        char = value[index]
        if value[index:index + 2] in {"{{", "}}"}:
            literal.append(char)
            index += 2
        elif char == "{":
            end = _end(value, index + 1)
            expression = value[index + 1:end].strip()
            if not expression:
                raise ValueError("empty interpolation expression")
            program = parse(expression)
            if len(program.children) != 1 or program.children[0].kind in {
                "let", "assign", "runnable", "print"} or (
                    program.children[0].kind == "host" and program.children[0].value[1] == "statement"):
                raise ValueError("interpolation requires one value expression")
            parts.extend(("".join(literal), compile_program(program)))
            expressions.append(program)
            literal = []
            index = end + 1
        elif char == "}":
            raise ValueError("unexpected `}` in interpolation; use `}}` for a literal brace")
        else:
            literal.append(char)
            index += 1
    parts.append("".join(literal))
    return Template(tuple(parts), tuple(expressions))
