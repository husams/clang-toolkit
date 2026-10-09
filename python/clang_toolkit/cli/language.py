"""Shared command grammar and lossless editor tokenization for the REPL."""

from __future__ import annotations

from functools import cache
from pathlib import Path

from lark import Lark, Token
from lark.exceptions import UnexpectedInput

GRAMMAR = Path(__file__).with_name("grammar.lark")


@cache
def parser() -> Lark:
    """Build the cached command parser with source positions enabled."""
    return Lark(
        GRAMMAR.read_text() + "\n%ignore BATCH_SEPARATOR\n",
        parser="lalr",
        start="start",
        propagate_positions=True,
    )


@cache
def batch_parser() -> Lark:
    """Build the formal multi-command parser used by noninteractive runs."""
    return Lark(
        GRAMMAR.read_text(),
        parser="lalr",
        start="batch_start",
        propagate_positions=True,
    )


@cache
def reference_parser() -> Lark:
    """Parse template references with the same formal grammar as commands."""
    return Lark(
        GRAMMAR.read_text(),
        parser="lalr",
        start="reference_start",
        propagate_positions=True,
    )


@cache
def _editor_parser() -> Lark:
    """Build the lossless lexer used by editor features and completeness checks."""
    return Lark(
        GRAMMAR.read_text(),
        parser="lalr",
        start="editor_start",
        lexer="basic",
        propagate_positions=True,
    )


def lex(text: str) -> list[Token]:
    """Tokenize all input, retaining whitespace and representing bad chars.

    The editor lexer guarantees full coverage, while the command parser's
    contextual lexer supplies the token types for every valid prefix. This
    keeps identifiers such as ``match`` usable where the grammar expects a
    name, and distinguishes ``.bind`` from ``.`` followed by ``bind``.
    """
    editor_tokens = []
    for token in _editor_parser().lex(text, dont_ignore=True):
        if token.type == "EDITOR_NAME":
            token = Token.new_borrow_pos("NAME", str(token), token)
        elif token.type == "BATCH_SEPARATOR":
            # Newlines delimit batch statements, but remain ordinary
            # whitespace for editor context, highlighting and completeness.
            token = Token.new_borrow_pos("WS", str(token), token)
        editor_tokens.append(token)
    contextual_tokens: list[Token] = []
    interactive = parser().parse_interactive(text)
    try:
        contextual_tokens.extend(interactive.iter_parse())
    except UnexpectedInput:
        # Invalid or incomplete suffixes remain represented by the lossless
        # editor tokens; the prefix already emitted by the parser stays typed.
        pass

    merged: list[Token] = []
    context_index = 0
    for token in editor_tokens:
        while (
            context_index < len(contextual_tokens)
            and contextual_tokens[context_index].end_pos <= token.start_pos
        ):
            context_index += 1
        overlap_end = context_index
        while (
            overlap_end < len(contextual_tokens)
            and contextual_tokens[overlap_end].start_pos < token.end_pos
        ):
            overlap_end += 1

        overlaps = contextual_tokens[context_index:overlap_end]
        cursor = token.start_pos
        tiles_token = bool(overlaps)
        for contextual_token in overlaps:
            if (
                contextual_token.start_pos != cursor
                or contextual_token.end_pos > token.end_pos
            ):
                tiles_token = False
                break
            cursor = contextual_token.end_pos
        tiles_token = tiles_token and cursor == token.end_pos

        if tiles_token:
            merged.extend(overlaps)
        else:
            merged.append(token)
        context_index = overlap_end

    return merged
