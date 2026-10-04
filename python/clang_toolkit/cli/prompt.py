"""prompt_toolkit integration for balanced multiline commands."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping

from prompt_toolkit import PromptSession
from prompt_toolkit.document import Document
from prompt_toolkit.input import Input
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.output import Output
from prompt_toolkit.validation import ValidationError, Validator

from clang_toolkit.cli.completion import ReplCompleter
from clang_toolkit.cli.highlight import STYLE, ReplLexer
from clang_toolkit.cli.input_state import input_state


class InputValidator(Validator):
    def validate(self, document: Document) -> None:
        state = input_state(document.text)
        if state.error_at is not None:
            raise ValidationError(
                cursor_position=state.error_at,
                message="Unexpected character or mismatched closing delimiter",
            )
        if state.needs_more:
            raise ValidationError(
                cursor_position=len(document.text),
                message="Close the open string or delimiter before submitting",
            )


def create_session(
    *,
    input: Input | None = None,
    output: Output | None = None,
    references: Mapping[str, Iterable[str]]
    | Callable[[], Mapping[str, Iterable[str]]]
    | None = None,
) -> PromptSession[str]:
    bindings = KeyBindings()

    @bindings.add("enter")
    def enter(event: KeyPressEvent) -> None:
        buffer = event.current_buffer
        if input_state(buffer.text).needs_more or buffer.cursor_position != len(
            buffer.text
        ):
            buffer.newline(copy_margin=True)
        else:
            buffer.validate_and_handle()

    return PromptSession(
        completer=ReplCompleter(references=references),
        lexer=ReplLexer(),
        style=STYLE,
        multiline=True,
        prompt_continuation="...> ",
        key_bindings=bindings,
        validator=InputValidator(),
        validate_while_typing=False,
        input=input,
        output=output,
    )
