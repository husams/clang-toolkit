"""Parser-state helpers shared by completion context and suggestions."""

from __future__ import annotations

from collections.abc import Iterable

from lark import Token
from lark.exceptions import UnexpectedInput

from clang_toolkit.cli.language import parser

_KEYWORD_TYPES = {
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
