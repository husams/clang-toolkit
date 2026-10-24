"""Prompt-toolkit editing support for the combined legacy/prototype grammar."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from functools import cache
import re

from lark import Lark, Token
from lark.lexer import PatternStr
from lark.exceptions import UnexpectedInput
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import StyleAndTextTuples
from prompt_toolkit.lexers import Lexer
from prompt_toolkit.validation import ValidationError, Validator

from clang_toolkit.cli.highlight import TOKEN_STYLES
from clang_toolkit.cli.completion_candidates import _REGEX_LITERALS
from clang_toolkit.cli.completion_context import accepted_after
from clang_toolkit.cli.completion_cursor import cursor_context
from clang_toolkit.cli.matcher_catalog import MATCHER_METADATA
from clang_toolkit.cli.parser_cache import cached_lalr
from clang_toolkit.cli.input_state import InputState
from clang_toolkit.cli.runtime.prototype.repl_language import (
    grammar_text,
    parser,
    parse,
)
from clang_toolkit.cli.runtime.prototype.syntax import Node

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
        "while",
        "repeat",
        "until",
        "on",
        "error",
        "exit",
        "break",
        "continue",
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
    return cached_lalr(
        grammar_text(),
        lexer="basic",
        start="editor_start",
        propagate_positions=True,
    )


def _kind(token: Token) -> str:
    name = token.type
    if name.startswith("__IGNORE"):
        return "WS" if str(token).isspace() else "COMMENT"
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
        if kind in {"OPEN_STRING", "OPEN_CPP_SOURCE"}:
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


@cache
def _keyword_patterns() -> tuple[re.Pattern[str], ...]:
    """Read keyword vocabulary from the grammar, including legacy commands."""
    return tuple(
        re.compile(terminal.pattern.to_regexp())
        for terminal in _editor_parser().terminals
        if _kind(Token(terminal.name, "")) in _REGEX_LITERALS
        or (
            isinstance(terminal.pattern, PatternStr)
            and terminal.pattern.value.isidentifier()
        )
    )


def highlight(source: str) -> StyleAndTextTuples:
    """Share lossless combined-language colors with the editor and Markdown."""
    tokens = lex(source)
    significant = [
        token
        for token in tokens
        if not str(token).isspace() and _kind(token) != "COMMENT"
    ]
    following = {
        id(token): str(significant[i + 1]) if i + 1 < len(significant) else ""
        for i, token in enumerate(significant)
    }
    fragments: StyleAndTextTuples = []
    for token in tokens:
        kind = _kind(token)
        text = str(token)
        if kind == "COMMENT":
            style = "comment"
        elif kind in {
            "CPP_SOURCE",
            "OPEN_CPP_SOURCE",
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
        elif text in {"true", "false", "null"}:
            style = "null" if text == "null" else "boolean"
        elif kind in {"ERROR"}:
            style = "error"
        elif kind == "DOLLAR":
            style = "reference"
        elif kind == "BIND" or text == ".bind":
            style = "bind"
        elif text in _KEYWORDS and text not in MATCHER_METADATA:
            style = "keyword"
        elif text.isidentifier() and following.get(id(token)) == "(":
            metadata = MATCHER_METADATA.get(text)
            style = (
                {
                    "node": "matcher-root",
                    "narrowing": "matcher-predicate",
                    "traversal": "matcher",
                }.get(metadata[0], "matcher")
                if metadata
                else "function"
            )
            if text in {"unless", "anyOf", "allOf", "eachOf", "optionally"}:
                style = "matcher"
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
            "|",
            "+=",
            "-=",
            "*=",
            "/=",
            "%=",
            "?",
        }:
            style = "operator"
        elif text in _KEYWORDS or any(
            pattern.fullmatch(text) for pattern in _keyword_patterns()
        ):
            style = "keyword"
        elif str(token) in "()[]{}:,;." and len(str(token)) == 1:
            style = "punctuation"
        else:
            style = "variable" if text.isidentifier() else TOKEN_STYLES.get(kind, "")
        fragments.append((f"class:{style}" if style else "", text))
    return fragments


class PrototypeReplLexer(Lexer):
    """Highlight all characters using terminals from the composed grammar."""

    def lex_document(self, document: Document) -> Callable[[int], StyleAndTextTuples]:
        lines: list[StyleAndTextTuples] = [[]]
        for style, text in highlight(document.text):
            for index, part in enumerate(text.split("\n")):
                if index:
                    lines.append([])
                if part:
                    lines[-1].append((style, part))
        return lambda lineno: lines[lineno] if 0 <= lineno < len(lines) else []


def _completing_loop_binding(source: str, name: str, position: int) -> bool:
    """Inspect a completed draft to offer metadata only on visible loop bindings."""
    location = _position(source, position)
    state = input_state(source)
    try:
        program = parse(
            source + "".join(_CLOSERS[value] for value in reversed(state.stack))
        )
    except (UnexpectedInput, ValueError):
        return False

    def visit(node: Node, bindings: set[str]) -> bool | None:
        if node.kind == "get" and node.value == "index":
            base = node.children[0]
            if (
                base.kind == "ref"
                and base.value == name
                and (base.line, base.column) == location
            ):
                return name in bindings
        if node.kind == "foreach":
            found = visit(node.children[0], bindings)
            return (
                found
                if found is not None
                else visit(node.children[1], bindings | {node.value})
            )
        if node.kind in {"program", "block"}:
            bindings = set(bindings)
            for statement in node.children:
                found = visit(statement, bindings)
                if found is not None:
                    return found
                statement = (
                    statement.children[0] if statement.kind == "observe" else statement
                )
                if statement.kind in {"let", "runnable"}:
                    binding = (
                        statement.value[0]
                        if statement.kind == "runnable"
                        else statement.value
                    )
                    bindings.discard(binding)
            return None
        if node.kind == "runnable":
            bindings = bindings - set(node.value[1])
        for child in node.children:
            if isinstance(child, Node):
                found = visit(child, bindings)
                if found is not None:
                    return found
        return None

    return visit(program, set()) is True


def _matcher_argument_document(
    document: Document, tokens: list[Token], matchers: set[str]
) -> Document | None:
    """Recover the current native argument without parsing earlier script text."""
    stack: list[tuple[str, int | None]] = []
    previous = ""
    for token in tokens:
        if _kind(token) in {"WS", "COMMENT", "NEWLINE", "BATCH_SEPARATOR"}:
            continue
        value = str(token)
        if value in _OPENERS:
            start = int(token.end_pos) if value == "(" and previous in matchers else None
            stack.append((value, start))
        elif value in _CLOSING:
            if not stack or stack.pop()[0] != _CLOSING[value]:
                return None
        elif value == "," and stack and stack[-1][1] is not None:
            stack[-1] = (stack[-1][0], int(token.end_pos))
        previous = value
    start = next((start for _, start in reversed(stack) if start is not None), None)
    if start is None:
        return None
    # Whitespace and comments before the current argument need not consume the
    # parser's completion budget. Existing brackets/expressions remain intact.
    start = next((int(token.start_pos) for token in tokens
                  if int(token.start_pos) >= start
                  and _kind(token) not in {"WS", "COMMENT", "NEWLINE", "BATCH_SEPARATOR"}),
                 document.cursor_position)
    prefix = "match functionDecl("
    return Document(prefix + document.text[start:],
                    cursor_position=len(prefix) + document.cursor_position - start)


class PrototypeCompleter(Completer):
    """Keep legacy suggestions and add the compact prototype keyword set."""

    def __init__(self, base: Completer) -> None:
        self.base = base

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        before = document.text_before_cursor
        # Use token spans from the complete draft: a closed string may extend
        # past the cursor, and an earlier line's comment is no longer active.
        cursor = document.cursor_position
        draft_tokens = lex(document.text)
        if any(
            _kind(token) in {"CPP_SOURCE", "OPEN_CPP_SOURCE"}
            and int(token.start_pos) < cursor
            and (
                cursor < int(token.end_pos)
                or (_kind(token) == "OPEN_CPP_SOURCE" and cursor == int(token.end_pos))
            )
            for token in draft_tokens
        ):
            return
        in_literal = any(
            int(token.start_pos) < cursor < int(token.end_pos)
            and _kind(token)
            in {
                "COMMENT",
                "CPP_SOURCE",
                "OPEN_CPP_SOURCE",
                "OPEN_STRING",
                "STRING",
                "PREDICATE_STRING",
                "FILE_STRING",
                "DIRECTORY_STRING",
                "PATH_STRING",
            }
            for token in draft_tokens
        )
        existing = list(self.base.get_completions(document, complete_event))
        tokens = lex(before)
        native = next(
            (
                token
                for token in reversed(tokens)
                if str(token) in {
                    "match", "parse", "cfg", "callgraph", "traverse",
                    "help", "let", "index",
                }
            ),
            None,
        )
        if not existing and not in_literal and (
            not tokens or _kind(tokens[-1]) not in {"COMMENT", "OPEN_STRING", "OPEN_CPP_SOURCE"}
        ):
            # A runnable header is outside the legacy parser. Recover the
            # native operand's grammar context from its lossless token spans.
            if native is not None and int(native.start_pos) > 0:
                start = int(native.start_pos)
                existing = list(
                    self.base.get_completions(
                        Document(document.text[start:], cursor_position=cursor - start),
                        complete_event,
                    )
                )
            if not existing:
                matchers = set(getattr(self.base, "_nested_matchers", ())) | set(
                    getattr(self.base, "_root_matchers", ()))
                argument = _matcher_argument_document(document, tokens, matchers)
                if argument is not None:
                    existing = list(self.base.get_completions(argument, complete_event))
        if "$" not in before:
            existing = [
                Completion(
                    item.text.removeprefix("$"),
                    item.start_position,
                    display=item.display_text.replace("$", ""),
                    display_meta=item.display_meta,
                )
                if item.text.startswith("$")
                else item
                for item in existing
                if item.text != "$"
            ]
        yield from existing
        if in_literal:
            return
        if tokens and _kind(tokens[-1]) in {"COMMENT", "OPEN_STRING", "OPEN_CPP_SOURCE"}:
            return
        if native is not None and str(native) == "index":
            start = int(native.start_pos)
            context = cursor_context(document.text[start:], cursor - start)
            if (
                context is not None
                and not any(
                    token.type in {"BATCH_SEPARATOR", "SEMICOLON"}
                    for token in context.prefix_tokens
                )
                and accepted_after(context.prefix_tokens)
            ):
                # Index operands are command syntax, not script expressions.
                # Keep unrelated bindings, functions and keywords out of menus.
                return
        help_query = re.search(
            r"(?:^|[;\n])\s*help\s+([A-Za-z_][A-Za-z0-9_]*)?$", before
        )
        if help_query is not None:
            # The shared help catalog includes pipes and callable topics.
            return
        pipeline_partial = _pipeline_stage_partial(before, cursor, tokens)
        pipeline_arguments = _pipeline_call_arguments(before, cursor, tokens)
        pipeline_word_label = (
            None if pipeline_partial is not None or pipeline_arguments is not None
            else _pipeline_word_label(before, cursor, tokens)
        )
        named_arguments = (
            None if pipeline_partial is not None or pipeline_arguments is not None
            or pipeline_word_label is not None
            else _named_call_arguments(before, cursor, tokens)
        )
        match = re.search(r"[A-Za-z_][A-Za-z0-9_]*$|(?<=\.)$", before)
        if (match is None and pipeline_partial is None and pipeline_arguments is None
                and named_arguments is None and pipeline_word_label is None):
            return
        partial = (
            match.group(0) if match is not None
            else pipeline_partial if pipeline_partial is not None
            else pipeline_arguments[1] if pipeline_arguments is not None
            else pipeline_word_label[1] if pipeline_word_label is not None
            else named_arguments[1] if named_arguments is not None
            else ""
        )
        tail = re.match(r"[A-Za-z_0-9]+", document.text_after_cursor)
        word_suffix = tail[0] if tail else ""

        def insertion(name: str, *, call: bool = False) -> str | None:
            if not name.startswith(partial) or not name.endswith(word_suffix):
                return None
            if word_suffix:
                return name[: -len(word_suffix)]
            return name + (
                "("
                if call and not document.text_after_cursor.lstrip().startswith("(")
                else ""
            )

        known = {item.text for item in existing}
        references = getattr(self.base, "_references", None)
        references = references() if callable(references) else references or {}
        functions = getattr(self.base, "_matcher_functions", None)
        functions = functions() if callable(functions) else functions or ()
        descriptions = (
            self.base.function_descriptions()
            if hasattr(self.base, "function_descriptions")
            else {}
        )
        functions = set(functions) | set(descriptions)
        if pipeline_arguments is not None:
            stage_name, argument_partial = pipeline_arguments
            description = descriptions.get(stage_name)
            if description is not None:
                for name in description.pipeline_parameters:
                    if not name.startswith(argument_partial) or name in known:
                        continue
                    yield Completion(
                        name + "=",
                        start_position=-len(argument_partial),
                        display=name + "=",
                        display_meta=f"stage argument · {stage_name} (input supplied by |)",
                    )
            return
        if pipeline_word_label is not None:
            stage_name, argument_partial = pipeline_word_label
            description = descriptions.get(stage_name)
            if description is not None:
                for name in description.pipeline_parameters:
                    if not name.startswith(argument_partial) or name in known:
                        continue
                    yield Completion(
                        name + " ",
                        start_position=-len(argument_partial),
                        display=name,
                        display_meta=f"stage label · {stage_name} (input supplied by |)",
                    )
            return
        if named_arguments is not None:
            function_name, argument_partial, already_supplied = named_arguments
            description = descriptions.get(function_name)
            if description is not None:
                for name in description.parameter_names:
                    if (not name.startswith(argument_partial) or name in already_supplied
                            or name in known):
                        continue
                    yield Completion(
                        name + "=",
                        start_position=-len(argument_partial),
                        display=name + "=",
                        display_meta=f"argument · {function_name}",
                    )
        if pipeline_partial is not None:
            for name in sorted(functions):
                text = insertion(name, call=True)
                if text is None or text in known:
                    continue
                hint = (
                    descriptions[name].pipeline_hint
                    if name in descriptions
                    else f"user defined · {name}(…)"
                )
                yield Completion(
                    text,
                    start_position=-len(pipeline_partial),
                    display=name + ("(" if text.endswith("(") else ""),
                    display_meta=hint,
                )
            return
        if re.search(r"(?:^|[;\n])\s*help\s+[^;\n]*$", before):
            return
        if match is not None and before[: match.start()].endswith("."):
            field = re.search(
                r"([A-Za-z_][A-Za-z0-9_]*(?:\[[0-9]+\]|\.[A-Za-z_][A-Za-z0-9_]*)*)\.[A-Za-z_0-9]*$",
                before,
            )
            if field and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", field.group(1)):
                draft = before[: match.start()] + "index"
                if _completing_loop_binding(draft, field.group(1), field.start(1)):
                    for name in ("index", "value"):
                        text = insertion(name)
                        if text is not None and text not in known:
                            yield Completion(
                                text,
                                start_position=-len(partial),
                                display_meta="loop binding",
                            )
                            known.add(text)
            resolver = getattr(self.base, "_field_resolver", None)
            suggestions = resolver(field.group(1)) if field and resolver else ()
            for item in suggestions:
                name = item.name if hasattr(item, "name") else str(item)
                text = insertion(name, call=getattr(item, "kind", None) == "method")
                if text is not None and text not in known:
                    yield Completion(
                        text,
                        start_position=-len(partial),
                        display_meta=getattr(item, "display_meta", "field"),
                    )
            return
        if "$" not in before:
            for name in sorted(references):
                text = insertion(name)
                if (
                    name not in functions
                    and text is not None
                    and name != partial
                    and text not in known
                ):
                    yield Completion(
                        text, start_position=-len(partial), display_meta="binding"
                    )
            for name in sorted(functions):
                text = insertion(name, call=True)
                if text is not None and text not in known:
                    hint = (
                        descriptions[name].hint
                        if name in descriptions
                        else f"user defined · {name}(…)"
                    )
                    yield Completion(
                        text,
                        start_position=-len(partial),
                        display=name + ("(" if text.endswith("(") else ""),
                        display_meta=hint,
                    )
        for keyword in sorted(_KEYWORDS):
            text = insertion(keyword)
            if text is not None and keyword != partial and text not in known:
                yield Completion(
                    text, start_position=-len(partial), display_meta="script keyword"
                )


def _pipeline_stage_partial(source: str, cursor: int, tokens: list[Token]) -> str | None:
    """Return the editable stage name after a pipeline separator, if present."""
    pipes = [
        token for token in tokens
        if (_kind(token) == "PIPE" or str(token) == "|")
        and int(token.end_pos) <= cursor
    ]
    if not pipes:
        return None
    start = int(pipes[-1].end_pos)
    suffix = source[start:cursor]
    match = re.fullmatch(r"\s*([A-Za-z_][A-Za-z0-9_]*)?", suffix)
    return match[1] or "" if match is not None else None


def _pipeline_call_arguments(
    source: str, cursor: int, tokens: list[Token]
) -> tuple[str, str] | None:
    """Find a simple named-argument prefix in the current pipeline stage call."""
    pipes = [
        token for token in tokens
        if (_kind(token) == "PIPE" or str(token) == "|")
        and int(token.end_pos) <= cursor
    ]
    if not pipes:
        return None
    suffix = source[int(pipes[-1].end_pos):cursor]
    match = re.fullmatch(
        r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)?",
        suffix,
    )
    if match is None:
        return None
    return match[1], match[2] or ""


def _pipeline_word_label(
    source: str, cursor: int, tokens: list[Token]
) -> tuple[str, str] | None:
    """Find a word-label argument being typed in the current pipeline stage."""
    pipes = [
        token for token in tokens
        if (_kind(token) == "PIPE" or str(token) == "|")
        and int(token.end_pos) <= cursor
    ]
    if not pipes:
        return None
    suffix = source[int(pipes[-1].end_pos):cursor]
    match = re.fullmatch(
        r"\s*([A-Za-z_][A-Za-z0-9_]*)\s+([A-Za-z_][A-Za-z0-9_]*)?",
        suffix,
    )
    if match is None:
        return None
    return match[1], match[2] or ""


def _named_call_arguments(
    source: str, cursor: int, tokens: list[Token]
) -> tuple[str, str, set[str]] | None:
    """Find a simple named-call argument being typed at the cursor."""
    depth = 0
    opening = None
    for index in range(len(tokens) - 1, -1, -1):
        token = tokens[index]
        if int(getattr(token, "end_pos", 0)) > cursor:
            continue
        kind = _kind(token)
        if kind in {"RPAR", "RSQB", "RBRACE"}:
            depth += 1
        elif kind in {"LPAR", "LSQB", "LBRACE"}:
            if depth:
                depth -= 1
            elif kind == "LPAR":
                opening = index
                break
    if opening is None or opening == 0:
        return None
    callee = str(tokens[opening - 1])
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", callee):
        return None

    start = int(tokens[opening].end_pos)
    nested = 0
    for token in tokens[opening + 1:]:
        if int(getattr(token, "end_pos", 0)) > cursor:
            break
        kind = _kind(token)
        if kind in {"LPAR", "LSQB", "LBRACE"}:
            nested += 1
        elif kind in {"RPAR", "RSQB", "RBRACE"}:
            if nested:
                nested -= 1
        elif kind == "COMMA" and nested == 0:
            start = int(token.end_pos)
    segment = source[start:cursor]
    match = re.fullmatch(r"\s*([A-Za-z_][A-Za-z0-9_]*)?", segment)
    if match is None:
        return None
    before_call = source[int(tokens[opening].end_pos):cursor]
    supplied = set(re.findall(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*=", before_call))
    return callee, match[1] or "", supplied
