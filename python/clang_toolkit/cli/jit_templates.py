"""Compile CTK interpolation parts for standalone LLVM IR."""

from __future__ import annotations

import ast
from collections.abc import Callable, Iterator

from lark import Tree
from lark.exceptions import UnexpectedInput

from .language import reference_parser
from .runtime.prototype.syntax import Node
from .runtime.prototype.templates import _end
from .runtime.templates import (
    _ESCAPED_DOLLAR,
    _SHORT_NAME,
    _closing_brace,
    _mask_escaped_dollars,
    TemplateError,
)
from .syntax_diagnostics import syntax_diagnostic


def template_parts(
    raw: str, parse_expression: Callable[[str], Node]
) -> tuple[str | Node, ...] | None:
    # Preserve older libraries while new scripts use bare brace expressions.
    if not raw.startswith('"') or "$" in raw or not any(c in raw for c in "{}"):
        return None
    value = ast.literal_eval(raw)
    parts: list[str | Node] = []
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
            program = parse_expression(expression)
            if len(program.children) != 1 or program.children[0].kind in {
                "let", "destructure", "assign", "runnable", "print"} or (
                    program.children[0].kind == "host" and program.children[0].value[1] == "statement"):
                raise ValueError("interpolation requires one value expression")
            parts.extend(("".join(literal), program))
            literal = []
            index = end + 1
        elif char == "}":
            raise ValueError("unexpected `}` in interpolation; use `}}` for a literal brace")
        else:
            literal.append(char)
            index += 1
    parts.append("".join(literal))
    return tuple(parts)



def string_parts(raw: str) -> Iterator[str | Tree]:
    """Parse a quoted string into literal fragments and reference expressions."""
    if not raw or raw[0] not in "\"'" or raw[-1] != raw[0]:
        raise TemplateError("invalid string literal")
    source = _mask_escaped_dollars(raw) if raw[0] == '"' else raw
    try:
        value = ast.literal_eval(source)
    except SyntaxError as exc:
        line = exc.lineno or 1
        column = exc.offset or 1
        detail = (exc.msg or "invalid syntax").replace("\n", " ")[:120]
        raise TemplateError(
            f"invalid string literal: {detail} at line {line}, column {column}"
        ) from exc
    except ValueError as exc:
        raise TemplateError("invalid string literal") from exc
    if not isinstance(value, str):
        raise TemplateError("expected string literal")
    if raw[0] == "'":
        yield value
        return

    def reference(expression: str) -> Tree:
        try:
            tree = reference_parser().parse("$" + expression).children[0]
        except UnexpectedInput as exc:
            detail = syntax_diagnostic("$" + expression, exc).replace(
                "syntax error at", "interpolation syntax error at", 1
            )
            raise TemplateError(f"invalid interpolation: {detail}") from exc
        return tree

    literal: list[str] = []
    index = 0
    while index < len(value):
        if value[index] == _ESCAPED_DOLLAR:
            literal.append("$")
            index += 1
        elif value[index] == "$" and value[index : index + 2] == "${":
            end = _closing_brace(value, index + 2)
            if literal:
                yield "".join(literal)
                literal.clear()
            yield reference(value[index + 2 : end])
            index = end + 1
        elif value[index] == "$":
            match = _SHORT_NAME.match(value, index + 1)
            if match is None:
                literal.append("$")
                index += 1
            else:
                if literal:
                    yield "".join(literal)
                    literal.clear()
                yield reference(match.group())
                index = match.end()
        else:
            literal.append(value[index])
            index += 1
    if literal:
        yield "".join(literal)
