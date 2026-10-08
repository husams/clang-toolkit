"""Double-quoted interpolation using the shared reference grammar."""

from __future__ import annotations

import ast
import re
from collections.abc import Callable
from typing import Any

from lark import Tree
from lark.exceptions import UnexpectedInput

from clang_toolkit.cli.language import reference_parser
from clang_toolkit.cli.syntax_diagnostics import syntax_diagnostic

from .values import render


class TemplateError(ValueError):
    """A string literal or interpolation is invalid."""


_ESCAPED_DOLLAR = "\ue000"
_SHORT_NAME = re.compile(r"[A-Za-z_][A-Za-z_0-9]*")


def _mask_escaped_dollars(raw: str) -> str:
    body = raw[1:-1]
    result: list[str] = []
    index = 0
    while index < len(body):
        if body[index] != "\\":
            result.append(body[index])
            index += 1
            continue
        end = index
        while end < len(body) and body[end] == "\\":
            end += 1
        count = end - index
        if end < len(body) and body[end] == "$" and count % 2:
            result.append("\\" * (count - 1) + _ESCAPED_DOLLAR)
            index = end + 1
        else:
            result.append("\\" * count)
            index = end
    return raw[0] + "".join(result) + raw[-1]


def _closing_brace(value: str, start: int) -> int:
    quote: str | None = None
    index = start
    while index < len(value):
        char = value[index]
        if quote is not None:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = None
        elif char in "\"'":
            quote = char
        elif char == "}":
            return index
        index += 1
    line = value.count("\n") + 1
    column = len(value.rsplit("\n", 1)[-1]) + 1
    raise TemplateError(
        "unclosed interpolation placeholder: expected `}` "
        f"at line {line}, column {column} (end of string)"
    )


def evaluate_string(raw: str, resolve: Callable[[Tree], Any]) -> str:
    """Decode a quoted string; only double quotes interpolate references."""
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
        return value

    def substitute(expression: str) -> str:
        try:
            tree = reference_parser().parse("$" + expression).children[0]
        except UnexpectedInput as exc:
            detail = syntax_diagnostic("$" + expression, exc).replace(
                "syntax error at", "interpolation syntax error at", 1
            )
            raise TemplateError(f"invalid interpolation: {detail}") from exc
        return render(resolve(tree))

    result: list[str] = []
    index = 0
    while index < len(value):
        if value[index] == _ESCAPED_DOLLAR:
            result.append("$")
            index += 1
        elif value[index] == "$" and value[index : index + 2] == "${":
            end = _closing_brace(value, index + 2)
            result.append(substitute(value[index + 2 : end]))
            index = end + 1
        elif value[index] == "$":
            match = _SHORT_NAME.match(value, index + 1)
            if match is None:
                result.append("$")
                index += 1
            else:
                result.append(substitute(match.group()))
                index = match.end()
        else:
            result.append(value[index])
            index += 1
    return "".join(result)
