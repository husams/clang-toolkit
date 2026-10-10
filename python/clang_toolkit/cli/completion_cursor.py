"""Locate the grammar prefix and editable text at a prompt cursor."""

from __future__ import annotations

from dataclasses import dataclass

from lark import Token

from clang_toolkit.cli.completion_context import accepted_after
from clang_toolkit.cli.input_state import input_state
from clang_toolkit.cli.language import lex

_WORD_TYPES = {
    "HELP_WORD",
    "NAME",
    "ROOT_MATCHER_NAME",
    "MATCHER_NAME",
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
    "LIST", "ATTACH", "SERVER", "STATUS", "CACHE", "PRUNE", "BINDINGS", "BINDING",
    "DROP", "RENAME", "APPEND",
    "LABEL",
    "MODE",
    "REPLACE",
    "JOIN_WITH",
    "FLATTEN",
}
_SAFE_SUFFIX = frozenset(" \t\r\n()[]{},.\"'")


@dataclass(frozen=True)
class CursorContext:
    prefix_tokens: list[Token]
    partial: str
    after: str


def cursor_context(source: str, cursor: int) -> CursorContext | None:
    """Find complete grammar tokens before cursor and its current prefix."""
    after = source[cursor:]
    if (
        not set(after).issubset(_SAFE_SUFFIX)
        or input_state(source[:cursor]).error_at is not None
    ):
        return None

    tokens = lex(source)
    partial = ""
    skipped: set[int] = set()
    partial_token_id: int | None = None
    for token in tokens:
        start, end = _offset(token, "start_pos"), _offset(token, "end_pos")
        if start < cursor < end and token.type in _WORD_TYPES:
            return None
        if token.type == "DOT" and start <= cursor == end:
            before = _before(tokens, start)
            if "BIND" in accepted_after(before):
                partial = "."
                partial_token_id = id(token)
                skipped.add(id(token))
                break
        if token.type == "NAME" and start <= cursor == end:
            prior = _previous_token(tokens, start)
            if (
                prior is not None
                and prior.type == "DOT"
                and _offset(prior, "end_pos") == start
            ):
                if "BIND" in accepted_after(
                    _before(tokens, _offset(prior, "start_pos"))
                ):
                    partial = "." + str(token)
                    partial_token_id = id(token)
                    skipped.add(id(prior))
                    break
        if token.type == "MATCH" and str(token) == "match" and start <= cursor == end:
            # Keep the completed command token in parser context. Candidates
            # then come from the root matcher role and append after it.
            continue
        if token.type in _WORD_TYPES and start <= cursor == end:
            partial = str(token)
            partial_token_id = id(token)
            break

    prefix_tokens: list[Token] = []
    for token in tokens:
        if _offset(token, "end_pos") > cursor:
            continue
        if token.type in {"WS", "ERROR"}:
            if token.type == "ERROR":
                return None
            continue
        if id(token) not in skipped and id(token) != partial_token_id:
            prefix_tokens.append(token)
    return CursorContext(prefix_tokens, partial, after)


def _before(tokens: list[Token], offset: int) -> list[Token]:
    return [
        token
        for token in tokens
        if _offset(token, "end_pos") <= offset and token.type not in {"WS", "ERROR"}
    ]


def _previous_token(tokens: list[Token], offset: int) -> Token | None:
    return next(
        (
            token
            for token in reversed(tokens)
            if _offset(token, "end_pos") <= offset and token.type != "WS"
        ),
        None,
    )


def _offset(token: Token, name: str) -> int:
    value = getattr(token, name, None)
    return int(value) if value is not None else 0
