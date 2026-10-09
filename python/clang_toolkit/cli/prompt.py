"""prompt_toolkit integration for balanced multiline commands."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.document import Document
from prompt_toolkit.filters import is_searching
from prompt_toolkit.input import Input
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.output import Output
from prompt_toolkit.history import History
from prompt_toolkit.search import accept_search
from prompt_toolkit.validation import ValidationError, Validator
from lark.exceptions import UnexpectedInput

from clang_toolkit.cli.completion import ReplCompleter
from clang_toolkit.cli.highlight import STYLE, ReplLexer
from clang_toolkit.cli.input_state import input_state
from clang_toolkit.cli.language import lex, parser
from clang_toolkit.cli.syntax_diagnostics import syntax_diagnostic
from clang_toolkit.cli.runtime.history import HistoryStore


class PersistentPromptHistory(History):
    """Load command history from the JSONL store without writing it twice."""

    def __init__(self, store: HistoryStore) -> None:
        super().__init__()
        self.store = store
        self._loaded_strings = list(reversed(store.read_commands()))
        self._loaded = True
        store.add_clear_listener(self.clear_cache)

    def load_history_strings(self) -> Iterable[str]:
        yield from self._loaded_strings

    def store_string(self, string: str) -> None:
        # Runtime.execute / dispatch owns persistent writes and session labels.
        return None

    def clear_cache(self) -> None:
        self._loaded_strings.clear()
        self._loaded = True


class InputValidator(Validator):
    def validate(self, document: Document) -> None:
        source = document.text
        state = input_state(source)
        if state.error_at is not None:
            raise ValidationError(
                cursor_position=state.error_at,
                message=_source_syntax_message(source, state.error_at),
            )
        if state.needs_more:
            raise ValidationError(
                cursor_position=len(source),
                message=_incomplete_input_message(source, state),
            )


def _source_syntax_message(source: str, error_position: int | None = None) -> str:
    try:
        parser().parse(source)
    except UnexpectedInput as error:
        parse_position = getattr(getattr(error, "token", None), "start_pos", None)
        if parse_position is None:
            parse_position = getattr(error, "pos_in_stream", None)
        if error_position is None or parse_position == error_position:
            # The prompt's validation toolbar has one line; its cursor marks
            # the failure in the editable source above it.
            return syntax_diagnostic(source, error).splitlines()[0]
    if error_position is not None:
        line, column = _line_column(source, error_position)
        character = source[error_position : error_position + 1]
        if character in {")", "]", "}"}:
            before = input_state(source[:error_position])
            expected = {"(": ")", "[": "]", "{": "}"}.get(
                before.stack[-1] if before.stack else ""
            )
            detail = f"unexpected `{character}` (closing delimiter)."
            if expected is not None:
                detail = f"unexpected `{character}`; expected `{expected}` to close the open delimiter."
        else:
            detail = f"unexpected character `{ascii(character)[1:-1]}`."
        return f"syntax error at line {line}, column {column}: {detail}"
    return "syntax error: input is incomplete or malformed."


def _incomplete_input_message(source: str, state) -> str:
    if state.open_string:
        message = _source_syntax_message(source)
        if "unterminated quoted string" in message:
            return message
        token = next(
            (item for item in reversed(lex(source)) if item.type == "OPEN_STRING"),
            None,
        )
        quote = source[token.start_pos] if token is not None else '"'
        line, column = _line_column(source, len(source))
        return (
            f"syntax error at line {line}, column {column}: unterminated quoted "
            f"string; expected the closing {quote} at end of input."
        )
    if state.stack:
        opener = state.stack[-1]
        expected = {"(": ")", "[": "]", "{": "}"}[opener]
        message = _source_syntax_message(source)
        if f"expected `{expected}`" in message:
            return message
        line, column = _line_column(source, len(source))
        return (
            f"syntax error at line {line}, column {column}: expected `{expected}` "
            f"to close `{opener}` at end of input."
        )
    if state.block_depth:
        line, column = _line_column(source, len(source))
        return (
            f"syntax error at line {line}, column {column}: expected `done` "
            "to close the multiline foreach body."
        )
    return _source_syntax_message(source)


def _line_column(source: str, position: int) -> tuple[int, int]:
    before = source[:position]
    return before.count("\n") + 1, len(before.rsplit("\n", 1)[-1]) + 1


def create_session(
    *,
    input: Input | None = None,
    output: Output | None = None,
    references: Mapping[str, Iterable[str]]
    | Callable[[], Mapping[str, Iterable[str]]]
    | None = None,
    field_resolver: Callable[[str], Iterable[object]] | None = None,
    presence_resolver: Callable[[str], Iterable[str]] | None = None,
    matcher_functions: Iterable[str] | Callable[[], Iterable[str]] | None = None,
    history: History | None = None,
    cwd: Path | None = None,
) -> PromptSession[str]:
    bindings = KeyBindings()

    @bindings.add("enter", filter=~is_searching)
    def enter(event: KeyPressEvent) -> None:
        buffer = event.current_buffer
        if input_state(buffer.text).needs_more or buffer.cursor_position != len(
            buffer.text
        ):
            buffer.newline(copy_margin=True)
        else:
            buffer.validate_and_handle()

    @bindings.add("enter", filter=is_searching)
    def accept_history_search(event: KeyPressEvent) -> None:
        target = event.app.layout.search_target_buffer_control
        accept_search()
        if target is not None:
            target.buffer.cursor_position = len(target.buffer.text)

    return PromptSession(
        completer=ReplCompleter(
            references=references,
            field_resolver=field_resolver,
            presence_resolver=presence_resolver,
            matcher_functions=matcher_functions,
            cwd=cwd,
        ),
        lexer=ReplLexer(),
        style=STYLE,
        multiline=True,
        prompt_continuation="...> ",
        key_bindings=bindings,
        validator=InputValidator(),
        history=history,
        validate_while_typing=False,
        input=input,
        output=output,
    )
