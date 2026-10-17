"""Smart command editing, enabled only in the workspace's input buffer."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from lark import Token
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import Completion, get_common_complete_suffix
from prompt_toolkit.filters import Filter
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent
from prompt_toolkit.keys import Keys
from prompt_toolkit.input.ansi_escape_sequences import ANSI_SEQUENCES

from clang_toolkit.cli.input_state import input_state
from clang_toolkit.cli.language import lex
from clang_toolkit.cli.input_state import InputState

PAIRS = {"(": ")", "[": "]", "{": "}", '"': '"', "'": "'"}
INDENT = " " * 4
Tokenizer = Callable[[str], list[Token]]


@contextmanager
def control_enter_keys() -> Iterator[None]:
    """Decode Ctrl/Alt/Shift+Enter as newlines; restore terminal defaults."""
    sequences = tuple(
        sequence
        for modifier in (2, 3, 5, 6)
        for sequence in (f"\x1b[27;{modifier};13~", f"\x1b[13;{modifier}u")
    )
    previous = {sequence: ANSI_SEQUENCES.get(sequence) for sequence in sequences}
    try:
        for sequence in sequences:
            ANSI_SEQUENCES[sequence] = (Keys.Escape, Keys.ControlM)
        yield
    finally:
        for sequence, key in previous.items():
            if key is None:
                ANSI_SEQUENCES.pop(sequence, None)
            else:
                ANSI_SEQUENCES[sequence] = key


def _kind(token: object) -> str:
    name = getattr(token, "type", "")
    for prefix in ("LEGACY_", "PROTO_"):
        if name.startswith(prefix):
            return name[len(prefix) :]
    return name


def literal_context(prefix: str, *, tokenizer: Tokenizer = lex) -> tuple[bool, bool]:
    """Use the lossless grammar tokens to distinguish strings and comments."""
    tokens = tokenizer(prefix)
    return (
        bool(tokens and _kind(tokens[-1]) == "OPEN_STRING"),
        bool(tokens and _kind(tokens[-1]) == "COMMENT"),
    )


def insert_pair(
    buffer: Buffer,
    char: str,
    *,
    tokenizer: Tokenizer = lex,
    input_state_fn: Callable[[str], InputState] = input_state,
) -> None:
    before = buffer.document.text_before_cursor
    after = buffer.document.text_after_cursor
    in_string, in_comment = literal_context(before, tokenizer=tokenizer)
    escaped = (len(before) - len(before.rstrip("\\"))) % 2 == 1
    if in_comment or (in_string and (char not in "\"'" or escaped)):
        buffer.insert_text(char)
        return
    if in_string:
        # Only the delimiter opening this string can close it.
        quote = str(tokenizer(before)[-1])[0]
        if char == quote and after.startswith(char):
            buffer.cursor_right()
        else:
            buffer.insert_text(char)
        return
    if char in PAIRS:
        buffer.insert_text(char + PAIRS[char])
        buffer.cursor_left()
        return
    state = input_state_fn(before)
    if state.stack and PAIRS[state.stack[-1]] == char:
        line = buffer.document.current_line_before_cursor
        if not line.strip():
            # Find the unmatched opener's indentation from grammar positions.
            openers = []
            for token in tokenizer(before):
                if str(token) in {"(", "[", "{"} and _kind(token) not in {
                    "STRING",
                    "OPEN_STRING",
                    "COMMENT",
                }:
                    openers.append(token)
                elif (
                    str(token) in {")", "]", "}"}
                    and _kind(token) not in {"STRING", "OPEN_STRING", "COMMENT"}
                    and openers
                ):
                    openers.pop()
            if openers:
                start = int(openers[-1].start_pos or 0)
                opener_line = before[:start].rsplit("\n", 1)[-1]
                margin = opener_line[
                    : len(opener_line) - len(opener_line.lstrip(" \t"))
                ]
                buffer.delete_before_cursor(len(line))
                buffer.insert_text(margin)
            # Closing on a blank line joins an already inserted closer.
            if after.startswith("\n"):
                gap = len(after) - len(after.lstrip("\n \t"))
                if after[gap:].startswith(char):
                    buffer.delete(gap)
                    after = buffer.document.text_after_cursor
        if after.startswith(char):
            buffer.cursor_right()
            return
    buffer.insert_text(char)


def smart_newline(
    buffer: Buffer,
    *,
    tokenizer: Tokenizer = lex,
    input_state_fn: Callable[[str], InputState] = input_state,
) -> None:
    before = buffer.document.text_before_cursor
    after = buffer.document.text_after_cursor
    line = buffer.document.current_line_before_cursor
    margin = line[: len(line) - len(line.lstrip(" \t"))]
    in_string, in_comment = literal_context(before, tokenizer=tokenizer)
    tokens = [
        token for token in tokenizer(before) if _kind(token) not in {"WS", "COMMENT"}
    ]
    opener = str(tokens[-1]) if tokens else ""
    on_this_line = bool(
        tokens and tokens[-1].end_line == buffer.document.cursor_position_row + 1
    )
    opens = not in_string and on_this_line and opener in {"(", "[", "{"}
    indent = margin + INDENT if opens else margin
    # The original closing bracket keeps its own line and indentation.
    if opens and after.startswith(PAIRS[opener]):
        buffer.insert_text("\n" + indent + "\n" + margin, move_cursor=False)
        buffer.cursor_position += 1 + len(indent)
    else:
        if (
            not in_string
            and not in_comment
            and on_this_line
            and _kind(tokens[-1]) == "DO"
        ):
            indent += INDENT
        buffer.insert_text("\n" + indent)


class CompletionPairs:
    """Pair completion insertions and previews in this workspace buffer only.

    Toolkit completion selection bypasses the ordinary character bindings.
    Keep its original document for cycling/cancellation and always insert a
    fresh closer, even if the suffix already contains an outer closing bracket.
    """

    def __init__(self, buffer: Buffer) -> None:
        self.pasting = False
        insert = buffer.insert_text
        select = buffer.go_to_completion
        apply = buffer.apply_completion

        def close(text: str) -> None:
            if not text or text[-1] not in PAIRS:
                return
            before = buffer.document.text_before_cursor
            in_string, in_comment = literal_context(before[:-1])
            if not in_string and not in_comment:
                insert(PAIRS[text[-1]], move_cursor=False, fire_event=False)

        def insert_text(
            data: str,
            overwrite: bool = False,
            move_cursor: bool = True,
            fire_event: bool = True,
        ) -> None:
            state = buffer.complete_state
            completing = (
                not self.pasting
                and not overwrite
                and move_cursor
                and state is not None
                and state.complete_index is None
                and buffer.document == state.original_document
                and data
                == get_common_complete_suffix(buffer.document, state.completions)
            )
            insert(
                data,
                overwrite=overwrite,
                move_cursor=move_cursor,
                fire_event=fire_event,
            )
            if completing:
                close(data)

        def go_to_completion(index: int | None) -> None:
            select(index)
            state = buffer.complete_state
            if state is not None and index is not None:
                completion = state.current_completion
                if completion is not None:
                    close(completion.text)
                    # Selection remains a preview until accepted by typing/click.
                    buffer.complete_state = state

        def apply_completion(completion: Completion) -> None:
            apply(completion)
            close(completion.text)

        buffer.insert_text = insert_text  # type: ignore[method-assign]
        buffer.go_to_completion = go_to_completion  # type: ignore[method-assign]
        buffer.apply_completion = apply_completion  # type: ignore[method-assign]


def editing_bindings(
    buffer: Buffer,
    enabled: Filter,
    *,
    input_state_fn: Callable[[str], InputState] = input_state,
    tokenizer: Tokenizer = lex,
) -> KeyBindings:
    bindings = KeyBindings()
    completion_pairs = CompletionPairs(buffer)

    @bindings.add(Keys.BracketedPaste, filter=enabled)
    def paste(event: KeyPressEvent) -> None:
        completion_pairs.pasting = True
        try:
            buffer.insert_text(event.data.replace("\r\n", "\n").replace("\r", "\n"))
        finally:
            completion_pairs.pasting = False

    @bindings.add("enter", filter=enabled, eager=True)
    def enter(event: KeyPressEvent) -> None:
        if input_state_fn(buffer.text).needs_more or buffer.cursor_position != len(
            buffer.text
        ):
            smart_newline(buffer, tokenizer=tokenizer, input_state_fn=input_state_fn)
        else:
            buffer.validate_and_handle()

    @bindings.add("c-j", filter=enabled, eager=True)
    def execute(event: KeyPressEvent) -> None:
        buffer.validate_and_handle()

    @bindings.add("escape", "enter", filter=enabled, eager=True)
    @bindings.add("escape", "c-j", filter=enabled, eager=True)
    def newline(event: KeyPressEvent) -> None:
        smart_newline(buffer, tokenizer=tokenizer, input_state_fn=input_state_fn)

    def typed(event: KeyPressEvent) -> None:
        insert_pair(
            buffer, event.data, tokenizer=tokenizer, input_state_fn=input_state_fn
        )

    for char in (*PAIRS, ")", "]", "}"):
        bindings.add(char, filter=enabled)(typed)

    @bindings.add("backspace", filter=enabled)
    def backspace(event: KeyPressEvent) -> None:
        before = buffer.document.text_before_cursor
        after = buffer.document.text_after_cursor
        in_string, in_comment = (
            literal_context(before[:-1], tokenizer=tokenizer)
            if before
            else (False, False)
        )
        if (
            before
            and not in_string
            and not in_comment
            and PAIRS.get(before[-1]) == after[:1]
        ):
            buffer.delete()
        buffer.delete_before_cursor()

    return bindings
