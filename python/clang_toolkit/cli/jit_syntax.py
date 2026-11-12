"""Standalone extensions to the shared CTK grammar and AST builder."""

from __future__ import annotations

from functools import cache

from lark import Lark
from lark.exceptions import VisitError

from .runtime.prototype import repl_language as shared
from .runtime.prototype.syntax import Node, _validate_control_scope


def _replace_rule(grammar: str, original: str, replacement: str) -> str:
    if grammar.count(original) != 1:
        raise ValueError(f"shared CTK grammar rule changed: {original}")
    return grammar.replace(original, replacement, 1)


@cache
def parser() -> Lark:
    grammar = shared.grammar_text()
    for command, role in (
        ("COMPILE_COMMANDS", "FILE_STRING"),
        ("INDEX LEGACY_START", "DIRECTORY_STRING"),
        ("INDEX LEGACY_RENAME", "DIRECTORY_STRING"),
        ("INDEX LEGACY_STATUS", "DIRECTORY_STRING"),
        ("INDEX LEGACY_PAUSE", "DIRECTORY_STRING"),
        ("INDEX LEGACY_RESUME", "DIRECTORY_STRING"),
        ("INDEX LEGACY_CANCEL", "DIRECTORY_STRING"),
    ):
        grammar = _replace_rule(
            grammar, f"LEGACY_{command} LEGACY_STRING", f"LEGACY_{command} LEGACY_{role}"
        )
    grammar = _replace_rule(
        grammar, "[LEGACY_IN LEGACY_STRING] -> index_find",
        "[LEGACY_IN LEGACY_DIRECTORY_STRING] -> index_find",
    )
    grammar = _replace_rule(
        grammar, "LEGACY_IN LEGACY_STRING  -> index_lookup",
        "LEGACY_IN LEGACY_DIRECTORY_STRING  -> index_lookup",
    )
    for command in ("PEEK", "STEP"):
        grammar = _replace_rule(
            grammar,
            f"LEGACY_{command} LEGACY_NAME [",
            f"LEGACY_{command} LEGACY_NAVIGATION_AXIS [",
        )
    grammar = _replace_rule(
        grammar,
        "legacy_navigation_option: LEGACY_NODES",
        r"LEGACY_NAVIGATION_AXIS: /[a-zA-Z_][a-zA-Z_0-9]*(?=\s)/"
        "\nlegacy_navigation_option: LEGACY_NODES",
    )
    grammar = _replace_rule(
        grammar,
        "[LEGACY_DO legacy_statement_block] -> match",
        "[LEGACY_DO legacy_callback_block] -> match",
    )
    # Apply this to the composed override, leaving the legacy rule intact.
    before, batch, after = grammar.partition("%override legacy_batch_statement:")
    after = _replace_rule(
        after,
        "LEGACY_DO legacy_statement_block -> durable_batch",
        "LEGACY_DO legacy_callback_block -> durable_batch",
    )
    grammar = before + batch + after + """
?legacy_callback_statement: legacy_assignment | legacy_statement | legacy_display_expression
                          | LEGACY_PRINT legacy_value_expression -> print
legacy_callback_block: LEGACY_LBRACE LEGACY_BATCH_SEPARATOR* (legacy_callback_statement (LEGACY_SEMICOLON | LEGACY_BATCH_SEPARATOR)+)* legacy_callback_statement? LEGACY_RBRACE -> statement_block
"""
    return Lark(
        grammar,
        parser="earley",
        lexer="dynamic_complete",
        ambiguity="resolve",
        start="repl_start",
        propagate_positions=True,
        maybe_placeholders=False,
    )


def parse(source: str) -> Node:
    try:
        result = shared._CombinedBuilder().transform(parser().parse(source))
    except VisitError as error:
        if isinstance(error.orig_exc, ValueError):
            raise error.orig_exc from None
        raise
    if not isinstance(result, Node):
        raise TypeError("combined REPL parser did not produce a prototype node")
    shared._validate_integer_ranges(result)
    _validate_control_scope(result)
    shared._validate_host_control_scope(result)
    return result
