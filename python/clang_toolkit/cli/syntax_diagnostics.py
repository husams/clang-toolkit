"""Readable syntax diagnostics derived from the REPL's Lark grammar."""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections.abc import Iterable
from difflib import get_close_matches
from functools import cache
import re

from lark import Token, Tree
from lark.exceptions import UnexpectedInput
from prompt_toolkit.utils import get_cwidth

from clang_toolkit.cli.language import lex, parser


_VALUE_STARTERS = frozenset(
    {
        "ROOT_MATCHER_NAME",
        "MATCH",
        "FOREACH",
        "PARSE",
        "DOLLAR",
        "STRING",
        "FILE_STRING",
        "NUMBER",
        "TRUE",
        "FALSE",
        "LSQB",
        "GLOB",
    }
)
_EXPECTED_LABELS = {
    "RPAR": "`)`",
    "RSQB": "`]`",
    "RBRACE": "`}`",
    "LPAR": "`(`",
    "LSQB": "`[`",
    "COMMA": "`,`",
    "SEMICOLON": "`;`",
    "EQUAL": "`=`",
    "STRING": "a quoted string",
    "FILE_STRING": "a quoted path",
    "DIRECTORY_STRING": "a quoted directory",
    "PATH_STRING": "a quoted path pattern",
    "NUMBER": "a number",
    "TRUE": "`true`",
    "FALSE": "`false`",
    "NAME": "a name",
    "HELP_WORD": "a help topic",
    "DOLLAR": "a variable reference such as `$name`",
    "ROOT_MATCHER_NAME": "a matcher call such as `functionDecl()`",
    "MATCHER_NAME": "a nested matcher call",
    "ERROR": "a valid command character",
    "MATCH": "`match`",
    "IN": "`in`",
    "DO": "`do`",
    "DONE": "`done`",
    "TO": "`to`",
    "AS": "`as`",
    "BIND": "`.bind(...)`",
    "YIELD": "`yield`",
}
_EXPECTED_ORDER = (
    "RPAR", "RSQB", "RBRACE", "STRING", "FILE_STRING", "ROOT_MATCHER_NAME",
    "MATCH", "START", "DOLLAR", "NAME", "NUMBER", "TRUE", "FALSE", "LSQB", "COMMA",
    "BIND", "$END", "SEMICOLON", "IN", "DO", "DONE", "EQUAL",
)


@cache
def _grammar_labels() -> dict[str, str]:
    """Derive readable keyword and punctuation labels from Lark terminals."""
    labels = {"$END": "end of command"}
    for terminal in parser().terminals:
        pattern = terminal.pattern
        if pattern.type == "str":
            labels[terminal.name] = f"`{pattern.value}`"
        elif pattern.type == "re":
            keyword = pattern.value.split("(", 1)[0].lstrip("/^")
            if keyword.isidentifier():
                labels[terminal.name] = f"`{keyword}`"
    return labels


def _expected_tokens(error: UnexpectedInput) -> set[str]:
    interactive = getattr(error, "interactive_parser", None)
    if interactive is not None:
        try:
            return {str(item) for item in interactive.accepts()}
        except (AttributeError, TypeError, ValueError):
            pass
    expected = getattr(error, "expected", None) or getattr(error, "allowed", None) or ()
    return {str(item) for item in expected}


def _failure_position(error: UnexpectedInput, source_length: int) -> int:
    token = getattr(error, "token", None)
    if isinstance(token, Token) and token.type == "$END":
        return source_length
    if isinstance(token, Token) and token.type != "$END":
        return token.start_pos
    position = getattr(error, "pos_in_stream", None)
    return source_length if position is None else position


def _diagnostic_position(
    error: UnexpectedInput, tokens: list[Token], source: str
) -> int:
    failure_position = _failure_position(error, len(source))
    if (
        tokens
        and tokens[-1].type == "OPEN_STRING"
        and tokens[-1].start_pos <= failure_position
    ):
        # The opening quote is valid; the missing closing quote belongs at EOF.
        return len(source)
    return min(max(failure_position, 0), len(source))


def _scoped_match_guidance(
    source: str, error: UnexpectedInput
) -> tuple[int, str, str | None] | None:
    token = getattr(error, "token", None)
    if not isinstance(token, Token) or token.type != "IN":
        return None
    try:
        prefix_tree = parser().parse(source[: token.start_pos])
    except UnexpectedInput:
        return None
    statement = next(
        (child for child in prefix_tree.children if isinstance(child, Tree)), None
    )
    if statement is None or statement.data != "assignment":
        return None
    if any(isinstance(child, Token) and child.type == "SEMICOLON" for child in prefix_tree.children):
        return None
    expression = next(
        (child for child in reversed(statement.children) if isinstance(child, Tree)), None
    )
    if expression is None or expression.data != "matcher":
        return None
    insertion = expression.meta.start_pos
    corrected = source[:insertion] + "match " + source[insertion:]
    try:
        parser().parse(corrected)
    except UnexpectedInput:
        return None
    explanation = "missing `match` after `=` before the matcher when using `in`."
    if len(corrected) > 512:
        return insertion, explanation, None
    return insertion, explanation, f"Try: `{corrected}`"


def _line_column(source: str, position: int) -> tuple[int, int]:
    before = source[:position]
    return before.count("\n") + 1, len(before.rsplit("\n", 1)[-1]) + 1


def _visible_character(character: str, column: int = 0) -> str:
    if character == "\t":
        return " " * (4 - column % 4)
    return _escaped_character(character)


def _escaped_character(character: str) -> str:
    escapes = {"\n": r"\n", "\r": r"\r", "\t": r"\t", "\0": r"\0"}
    if character in escapes:
        return escapes[character]
    # Escape invisible printable marks too, so display-cell bounds also bound
    # retained text even when input contains thousands of combining characters.
    if character.isprintable() and get_cwidth(character) > 0:
        return character
    codepoint = ord(character)
    if codepoint <= 0xFF:
        return f"\\x{codepoint:02x}"
    if codepoint <= 0xFFFF:
        return f"\\u{codepoint:04x}"
    return f"\\U{codepoint:08x}"


def _visible_text(text: str) -> tuple[str, list[int], list[int]]:
    """Return printable text with per-character cell and rendered offsets."""
    output: list[str] = []
    display_offsets = [0]
    text_offsets = [0]
    column = 0
    for character in text:
        rendered = _visible_character(character, column)
        output.append(rendered)
        column += get_cwidth(rendered)
        display_offsets.append(column)
        text_offsets.append(text_offsets[-1] + len(rendered))
    return "".join(output), display_offsets, text_offsets


def _safe_preview(text: str, max_chars: int = 32) -> str:
    pieces: list[str] = []
    used = 0
    for character in text:
        visible = _escaped_character(character)
        if used + len(visible) > max_chars:
            return "".join(pieces) + "…"
        pieces.append(visible)
        used += len(visible)
    return "".join(pieces)


def _source_caret(source: str, position: int, max_chars: int = 160) -> str:
    """Show bounded source text and align its caret in terminal display cells."""
    line_start = source.rfind("\n", 0, position) + 1
    line_end = source.find("\n", position)
    if line_end < 0:
        line_end = len(source)
    line = source[line_start:line_end]
    expanded, display_offsets, text_offsets = _visible_text(line)
    offset = display_offsets[min(max(position - line_start, 0), len(line))]
    if display_offsets[-1] <= max_chars:
        return expanded + "\n" + " " * offset + "^"

    target_start = max(0, offset - max_chars // 2)
    start_index = max(0, bisect_right(display_offsets, target_start) - 1)
    crop_start = display_offsets[start_index]
    prefix_marker = crop_start > 0
    budget = max_chars - int(prefix_marker)
    end_index = min(
        len(line), bisect_left(display_offsets, crop_start + budget)
    )
    if end_index <= start_index:
        end_index = min(len(line), start_index + 1)
    crop_end = display_offsets[end_index]
    suffix_marker = crop_end < display_offsets[-1]
    while (
        int(prefix_marker)
        + crop_end
        - crop_start
        + int(suffix_marker)
        > max_chars
        and end_index > start_index
    ):
        end_index -= 1
        crop_end = display_offsets[end_index]
        suffix_marker = crop_end < display_offsets[-1]
    shown = (
        ("…" if prefix_marker else "")
        + expanded[text_offsets[start_index] : text_offsets[end_index]]
        + ("…" if suffix_marker else "")
    )
    caret_column = int(prefix_marker) + offset - crop_start
    return shown + "\n" + " " * caret_column + "^"


def unknown_command_diagnostic(
    source: str, command_name: str, command_names: Iterable[str]
) -> str:
    """Explain an unknown leading command using the app's known command names."""
    token = next(
        (
            item
            for item in lex(source)
            if item.type != "WS" and item.type == "NAME" and str(item) == command_name
        ),
        None,
    )
    position = token.start_pos if token is not None else 0
    line, column = _line_column(source, position)
    safe_name = _safe_preview(command_name)
    candidates = sorted({name for name in command_names if isinstance(name, str)})
    suggestions = get_close_matches(command_name, candidates, n=2, cutoff=0.55)
    message = f"unknown command: {safe_name} at line {line}, column {column}."
    if suggestions:
        suggestion_text = ", ".join(f"`{name}`" for name in suggestions)
        message += f" Did you mean {suggestion_text}?"
    message += " Use `help` to see available commands."
    return message + "\n" + _source_caret(source, position)


def _expected_summary(expected: Iterable[str]) -> str:
    available = set(expected)
    labels: list[str] = []
    ordered = [token_type for token_type in _EXPECTED_ORDER if token_type in available]
    ordered.extend(
        terminal.name
        for terminal in parser().terminals
        if terminal.name in available and terminal.name not in ordered
    )
    ordered.extend(sorted(available - set(ordered)))
    grammar_labels = _grammar_labels()
    used = 0
    for token_type in ordered:
        used += 1
        label = _EXPECTED_LABELS.get(token_type) or grammar_labels.get(token_type)
        if label is None:
            readable = token_type.replace("_", " ").lower()
            label = f"a {readable} value"
        if token_type in available and label is not None and label not in labels:
            labels.append(label)
        if len(labels) == 4:
            break
    if len(available) > used and labels:
        labels.append("other valid syntax")
    if not labels:
        return " Expected a valid command continuation, such as a command, matcher, or value."
    if len(labels) == 1:
        return f" Expected {labels[0]}."
    return " Expected " + ", ".join(labels[:-1]) + f", or {labels[-1]}."


def syntax_diagnostic(source: str, error: UnexpectedInput) -> str:
    """Format a parser or lexer failure using bounded, user-facing syntax terms."""
    tokens = [token for token in lex(source) if token.type != "WS"]
    position = _diagnostic_position(error, tokens, source)
    line, column = _line_column(source, position)
    prefix = f"syntax error at line {line}, column {column}: "
    failure_position = _failure_position(error, len(source))
    if (
        tokens
        and tokens[-1].type == "OPEN_STRING"
        and tokens[-1].start_pos <= failure_position
    ):
        quote = str(tokens[-1])[0]
        return (
            prefix
            + f"unterminated quoted string; add the closing {quote} at end of input.\n"
            + _source_caret(source, position)
        )

    repair = _scoped_match_guidance(source, error)
    if repair is not None:
        insertion, explanation, suggestion = repair
        line, column = _line_column(source, insertion)
        prefix = f"syntax error at line {line}, column {column}: "
        result = prefix + explanation + "\n" + _source_caret(source, insertion)
        if suggestion is not None:
            result += "\n" + suggestion
        return result

    expected = _expected_tokens(error)
    error_token = getattr(error, "token", None)
    at_end = isinstance(error_token, Token) and error_token.type == "$END"
    failure_position = _failure_position(error, len(source))
    before_failure = [
        token for token in tokens if token.end_pos <= failure_position
    ]
    if (
        len(before_failure) >= 3
        and before_failure[-3].type == "DOT"
        and before_failure[-2].type == "HAS_FIELD"
        and before_failure[-1].type == "LPAR"
    ):
        position = failure_position
        line, column = _line_column(source, position)
        return (
            f"syntax error at line {line}, column {column}: "
            'hasField requires a field name: `hasField("field_name")`.\n'
            + _source_caret(source, position)
        )
    if at_end:
        previous = tokens[-1] if tokens else None
    else:
        error_position = getattr(error, "pos_in_stream", None)
        if error_position is None:
            error_position = len(source)
        previous = next(
            (token for token in reversed(tokens) if token.end_pos <= error_position),
            None,
        )
    if previous is not None and previous.type == "EQUAL" and expected & _VALUE_STARTERS:
        message = (
            "expected a value after `=` (a matcher, `match`, reference, string, number, "
            "boolean, or list)."
        )
    elif at_end and "RPAR" in expected:
        message = "unexpected end of input; expected `)` to close the current matcher call or group."
    elif at_end and "RSQB" in expected:
        message = "unexpected end of input; expected `]` to close the current list or index."
    elif at_end and "RBRACE" in expected:
        message = "unexpected end of input; expected `}` to close the current analysis block."
    elif at_end:
        message = "unexpected end of input."
    elif isinstance(error_token, Token):
        text = str(error_token)
        found = f"`{_safe_preview(text)}`"
        if error_token.type in {"RPAR", "RSQB", "RBRACE"} and error_token.type not in expected:
            message = f"unexpected {found} (closing delimiter)."
        else:
            message = f"unexpected {found}."
    elif getattr(error, "char", None) is not None:
        char = _safe_preview(str(error.char), 16)
        message = f"unexpected character `{char}`."
    else:
        message = "unexpected input."
    return (
        prefix
        + message
        + _expected_summary(expected)
        + "\n"
        + _source_caret(source, position)
    )
