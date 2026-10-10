"""Input completeness tracking driven by the shared editor token stream."""

from __future__ import annotations

from dataclasses import dataclass

from .language import lex

_CLOSERS = {"(": ")", "[": "]", "{": "}"}
_OPENERS = frozenset(_CLOSERS)


@dataclass(frozen=True)
class InputState:
    """Completeness state for a potentially multi-line REPL input."""

    stack: tuple[str, ...]
    open_string: bool
    error_at: int | None
    block_depth: int = 0

    @property
    def needs_more(self) -> bool:
        return self.error_at is None and (
            bool(self.stack) or self.open_string or self.block_depth > 0
        )


def input_state(text: str) -> InputState:
    """Return unmatched delimiter/string state and the first lexical mismatch."""
    stack: list[str] = []
    error_at: int | None = None
    open_string = False
    block_depth = 0

    tokens = lex(text)
    for index, token in enumerate(tokens):
        if token.type == "DO":
            remainder = text[token.end_pos :]
            next_token_index = index + 1
            while next_token_index < len(tokens) and tokens[next_token_index].type in {
                "WS", "COMMENT"
            }:
                next_token_index += 1
            opens_brace_block = (
                next_token_index < len(tokens)
                and tokens[next_token_index].type == "LBRACE"
            )
            if (
                not opens_brace_block
                and (not remainder.strip() or remainder.lstrip(" \t\r").startswith("\n"))
            ):
                block_depth += 1
        elif token.type in {"DONE", "DONE_AFTER_NEWLINE"} and block_depth:
            block_depth -= 1
        if token.type == "OPEN_STRING":
            open_string = True
            continue
        if token.type == "ERROR":
            if error_at is None:
                error_at = token.start_pos
            continue
        if token.type not in {"LPAR", "RPAR", "LSQB", "RSQB", "LBRACE", "RBRACE"}:
            continue

        value = str(token)
        if value in _OPENERS:
            stack.append(value)
        elif not stack or _CLOSERS[stack[-1]] != value:
            if error_at is None:
                error_at = token.start_pos
        else:
            stack.pop()

    return InputState(tuple(stack), open_string, error_at, block_depth)
