"""Parser-state helpers shared by completion context and suggestions."""

from __future__ import annotations

from collections.abc import Iterable

from lark import Token
from lark.exceptions import UnexpectedInput

from clang_toolkit.cli.language import parser, reference_parser

_KEYWORD_TYPES = {
    "PARSE",
    "YIELD",
    "LET",
    "MATCH",
    "CFG",
    "CALLGRAPH",
    "TRAVERSE",
    "SCRIPT",
    "HELP",
    "QUIT",
    "EXIT",
    "PRINT",
    "FOREACH",
    "IN",
    "DO",
    "DONE",
    "GLOB",
    "TRUE",
    "FALSE",
    "SET",
    "CLEAR",
    "ADD",
    "EXTRA_ARG",
    "EXTRA_ARGS",
    "TRAVERSAL",
    "CACHE_DIR",
    "FILES",
    "OUTPUT",
    "STDOUT",
    "SAVE",
    "LOAD",
    "TO",
    "AS",
    "INTO",
    "USER",
    "HISTORY",
    "SESSION",
    "LABEL",
    "MODE",
    "REPLACE",
    "JOIN_WITH",
}


def accepted_after(tokens: Iterable[Token]) -> set[str]:
    """Return grammar terminals valid after tokens, or an empty set if invalid."""
    interactive = parser().parse_interactive("")
    try:
        for token in tokens:
            accepted = set(interactive.accepts())
            if (
                token.type in _KEYWORD_TYPES
                and token.type not in accepted
                and "NAME" in accepted
            ):
                token = Token.new_borrow_pos("NAME", str(token), token)
            interactive.feed_token(token)
        return set(interactive.accepts())
    except UnexpectedInput:
        return set()


def reference_base(tokens: list[Token]) -> str:
    """Return the root variable after a reference marker, when present."""
    for index in range(len(tokens) - 1, -1, -1):
        if tokens[index].type == "DOLLAR" and index + 1 < len(tokens):
            return str(tokens[index + 1])
    return ""


def has_field_argument(
    tokens: list[Token], source_before_cursor: str
) -> tuple[str, str, str, int, bool] | None:
    """Return the reference and editable quoted argument in a hasField call."""
    if tokens and tokens[-1].type == "OPEN_STRING":
        if (
            len(tokens) < 5
            or tokens[-2].type != "LPAR"
            or tokens[-3].type != "HAS_FIELD"
            or tokens[-4].type != "DOT"
        ):
            return None
        string = tokens[-1]
        quote = str(string)[:1]
        partial = str(string)[1:]
        dot = tokens[-4]
        start_position = -len(partial)
        quote_open = True
    else:
        if len(tokens) < 4 or tokens[-1].type != "LPAR":
            return None
        if tokens[-2].type != "HAS_FIELD" or tokens[-3].type != "DOT":
            return None
        argument_prefix = source_before_cursor[int(tokens[-1].end_pos) :]
        if argument_prefix.startswith(("'", '"')):
            quote = argument_prefix[0]
            partial = argument_prefix[1:]
            quote_open = True
            start_position = -len(partial)
        else:
            quote = '"'
            partial = ""
            quote_open = False
            start_position = 0
        dot = tokens[-3]

    dot_start = int(getattr(dot, "start_pos", 0))
    dollar_positions = [
        int(token.start_pos)
        for token in tokens
        if token.type == "DOLLAR" and int(token.start_pos) < dot_start
    ]
    for start in reversed(dollar_positions):
        reference = source_before_cursor[start:dot_start]
        try:
            reference_parser().parse(reference)
        except UnexpectedInput:
            continue
        return reference, quote, partial, start_position, quote_open
    return None
