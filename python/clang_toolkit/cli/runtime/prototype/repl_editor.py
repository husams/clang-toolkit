"""Prompt-toolkit editing support for the combined legacy/prototype grammar."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from functools import cache
import re

from lark import Lark, Token
from lark.exceptions import UnexpectedInput
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.validation import ValidationError, Validator

from clang_toolkit.cli.highlight import TOKEN_STYLES
from clang_toolkit.cli.input_state import InputState
from clang_toolkit.cli.runtime.prototype.repl_language import grammar_text, parser

_CLOSERS = {"(": ")", "[": "]", "{": "}"}
_OPENERS = frozenset(_CLOSERS)
_CLOSING = {value: key for key, value in _CLOSERS.items()}
_KEYWORDS = frozenset(
    {
        "and",
        "do",
        "does",
        "defined",
        "then",
        "else",
        "false",
        "foreach",
        "has",
        "have",
        "if",
        "in",
        "is",
        "let",
        "not",
        "null",
        "or",
        "print",
        "true",
        "unless",
        "set",
    }
)
_WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")


@cache
def _editor_parser() -> Lark:
    """Use the combined grammar's lossless editor start and basic lexer."""
    return Lark(
        grammar_text(),
        parser="lalr",
        lexer="basic",
        start="editor_start",
        propagate_positions=True,
    )


def _kind(token: Token) -> str:
    name = token.type
    for prefix in ("LEGACY_", "PROTO_"):
        if name.startswith(prefix):
            return name[len(prefix) :]
    return name


def lex(source: str) -> list[Token]:
    """Return the composed grammar's full-coverage, lossless token stream."""
    return list(_editor_parser().lex(source, dont_ignore=True))


def _position(source: str, position: int) -> tuple[int, int]:
    before = source[:position]
    return before.count("\n") + 1, len(before.rsplit("\n", 1)[-1]) + 1


def input_state(source: str) -> InputState:
    """Track delimiters and parser-requested continuation without `done` blocks."""
    stack: list[str] = []
    error_at: int | None = None
    open_string = False
    for token in lex(source):
        kind = _kind(token)
        if kind == "OPEN_STRING":
            open_string = True
            continue
        if kind in {"COMMENT", "WS", "BATCH_SEPARATOR", "NEWLINE"}:
            continue
        if kind == "ERROR" and error_at is None:
            error_at = int(token.start_pos or 0)
            continue
        value = str(token)
        if value in _OPENERS:
            stack.append(value)
        elif value in _CLOSING:
            if not stack or stack[-1] != _CLOSING[value]:
                if error_at is None:
                    error_at = int(token.start_pos or 0)
            else:
                stack.pop()

    if error_at is not None:
        return InputState(tuple(stack), open_string, error_at)
    if stack or open_string:
        return InputState(tuple(stack), open_string, None)

    try:
        parser().parse(source)
    except UnexpectedInput as error:
        if _is_end_of_input(error, source):
            return InputState((), False, None, block_depth=1)
        position = getattr(error, "pos_in_stream", None)
        token = getattr(error, "token", None)
        if position is None and token is not None:
            position = getattr(token, "start_pos", None)
        if position is None:
            position = len(source)
        return InputState((), False, min(int(position), len(source)))
    return InputState((), False, None)


def _is_end_of_input(error: UnexpectedInput, source: str) -> bool:
    token = getattr(error, "token", None)
    if token is not None and getattr(token, "type", None) in {"$END", "EOF"}:
        return True
    position = getattr(error, "pos_in_stream", None)
    if position is not None and int(position) >= len(source):
        return True
    return error.__class__.__name__ in {"UnexpectedEOF", "UnexpectedToken"} and (
        token is None or str(token) in {"", "$END"}
    )


def _syntax_message(source: str, position: int) -> str:
    line, column = _position(source, position)
    character = source[position : position + 1]
    if character in _CLOSING:
        return f"syntax error at line {line}, column {column}: unexpected `{character}` (closing delimiter)."
    return f"syntax error at line {line}, column {column}: unexpected character `{ascii(character)[1:-1]}`."


class PrototypeInputValidator(Validator):
    """Validate combined REPL submissions and request more input at incomplete EOF."""

    def __init__(
        self, state_provider: Callable[[str], InputState] = input_state
    ) -> None:
        self.state_provider = state_provider

    def validate(self, document: Document) -> None:
        source = document.text
        state = self.state_provider(source)
        if state.error_at is not None:
            raise ValidationError(
                cursor_position=state.error_at,
                message=_syntax_message(source, state.error_at),
            )
        if state.needs_more:
            if state.open_string:
                message = "syntax error: unterminated quoted string; expected its closing quote at end of input."
            elif state.stack:
                opener = state.stack[-1]
                expected = _CLOSERS[opener]
                message = f"syntax error: expected `{expected}` to close `{opener}` at end of input."
            else:
                message = "syntax error: input is incomplete; continue the script or complete its expression."
            raise ValidationError(cursor_position=len(source), message=message)


class PrototypeReplLexer(Lexer):
    """Highlight all characters using terminals from the composed grammar."""

    def lex_document(self, document: Document) -> Callable[[int], StyleAndTextTuples]:
        lines: list[StyleAndTextTuples] = [[]]
        for token in lex(document.text):
            kind = _kind(token)
            if kind == "COMMENT":
                style = "comment"
            elif kind in {
                "OPEN_STRING",
                "STRING",
                "PREDICATE_STRING",
                "FILE_STRING",
                "DIRECTORY_STRING",
                "PATH_STRING",
            }:
                style = "string"
            elif kind in {"NUMBER", "INT", "FLOAT"}:
                style = "number"
            elif kind in {"TRUE", "FALSE", "NULL"}:
                style = "value"
            elif kind in {"ERROR"}:
                style = "error"
            elif kind in {"DOLLAR", "BIND"}:
                style = "reference"
            elif str(token) in {
                "+",
                "-",
                "*",
                "/",
                "%",
                "=",
                "==",
                "!=",
                "<",
                "<=",
                ">",
                ">=",
                "+=",
                "-=",
                "*=",
                "/=",
                "%=",
                "?",
            }:
                style = "operator"
            elif str(token) in _KEYWORDS or kind in {
                "LET",
                "PRINT",
                "FOREACH",
                "IN",
                "DO",
                "THEN",
                "DONE",
                "IF",
                "ELSE",
                "UNLESS",
                "AND",
                "OR",
                "NOT",
                "PARSE",
                "MATCH",
                "SET",
            }:
                style = "keyword"
            elif str(token) in "()[]{}:,;." and len(str(token)) == 1:
                style = "punctuation"
            else:
                style = TOKEN_STYLES.get(kind, "")
            text = str(token)
            for index, part in enumerate(text.split("\n")):
                if index:
                    lines.append([])
                if part:
                    lines[-1].append((f"class:{style}" if style else "", part))
        return lambda lineno: lines[lineno] if 0 <= lineno < len(lines) else []


class PrototypeCompleter(Completer):
    """Keep legacy suggestions and add the compact prototype keyword set."""

    def __init__(self, base: Completer) -> None:
        self.base = base

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        existing = list(self.base.get_completions(document, complete_event))
        yield from existing
        before = document.text_before_cursor
        tokens = lex(before)
        if any(_kind(token) in {"COMMENT", "OPEN_STRING"} for token in tokens):
            return
        match = _WORD.search(before)
        if match is None:
            return
        partial = match.group(0)
        known = {item.text for item in existing}
        for keyword in sorted(_KEYWORDS):
            if (
                keyword.startswith(partial)
                and keyword != partial
                and keyword not in known
            ):
                yield Completion(
                    keyword, start_position=-len(partial), display_meta="script keyword"
                )
