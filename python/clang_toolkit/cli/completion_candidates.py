"""Turn accepted grammar roles into filtered prompt_toolkit candidates."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from lark.lexer import PatternStr

from clang_toolkit.cli.completion_context import reference_base
from clang_toolkit.cli.completion_cursor import CursorContext
from clang_toolkit.cli.language import parser

_REGEX_LITERALS = {
    "BACKGROUND": "background",
    "PARSE": "parse",
    "YIELD": "yield",
    "CURSOR": "cursor",
    "OPEN": "open",
    "CONTINUE": "continue",
    "RESTART": "restart",
    "ROW": "row",
    "CURSOR_SCOPE": "scope",
    "REVISION": "revision",
    "CLOSE": "close",
    "BIND": ".bind",
    "CALLGRAPH": "callgraph",
    "CFG": "cfg",
    "EXIT": "exit",
    "HELP": "help",
    "LET": "let",
    "MATCH": "match",
    "QUIT": "quit",
    "SCRIPT": "script",
    "TRAVERSE": "traverse",
    "PRINT": "print",
    "FOREACH": "foreach",
    "IN": "in",
    "DO": "do",
    "DONE": "done",
    "GLOB": "glob",
    "TRUE": "true",
    "FALSE": "false",
    "SET": "set",
    "CLEAR": "clear",
    "ADD": "add",
    "EXTRA_ARG": "extra_arg",
    "EXTRA_ARGS": "extra_args",
    "TRAVERSAL": "traversal",
    "CACHE_DIR": "cache_dir",
    "FILES": "files",
    "OUTPUT": "output",
    "STDOUT": "stdout",
    "SAVE": "save",
    "LOAD": "load",
    "TO": "to",
    "AS": "as",
    "INTO": "into",
    "USER": "user",
    "HISTORY": "history",
    "SESSION": "session",
    "START": "start",
    "PAUSE": "pause",
    "RESUME": "resume",
    "LABEL": "label",
    "MODE": "mode",
    "REPLACE": "replace",
}
_NO_VALUE_TERMINALS = {"STRING", "OPEN_STRING", "NUMBER", "DOLLAR", "SEMICOLON"}
_PUNCTUATION = {"(", ")", "]", "}", ",", "."}


@dataclass(frozen=True)
class Candidate:
    text: str
    display: str
    start_position: int


def candidates_for(
    context: CursorContext,
    accepted: set[str],
    root_matchers: Iterable[str],
    nested_matchers: Iterable[str],
    references: Mapping[str, Iterable[str]],
    source_before_cursor: str,
) -> list[Candidate]:
    """Build candidates for accepted terminal roles and the current prefix."""
    names: list[tuple[str, bool, bool]] = []
    matcher_roles = {"ROOT_MATCHER_NAME", "MATCHER_NAME"}
    root_role = "ROOT_MATCHER_NAME" in accepted
    if root_role:
        names.extend((name, True, True) for name in root_matchers)
        if (
            source_before_cursor.lstrip().startswith("let ")
            and "=" in source_before_cursor
        ):
            names.extend((name, True, True) for name in nested_matchers)
    if "MATCHER_NAME" in accepted:
        names.extend((name, False, True) for name in nested_matchers)

    previous = context.prefix_tokens[-1].type if context.prefix_tokens else None
    if "NAME" in accepted and previous == "DOLLAR":
        names.extend((name, False, False) for name in references)
    elif "NAME" in accepted and previous == "DOT":
        fields = references.get(reference_base(context.prefix_tokens), ())
        names.extend((name, False, name == "joinWith") for name in fields)

    candidates: list[Candidate] = []
    for terminal in accepted - _NO_VALUE_TERMINALS - matcher_roles:
        literal = _literal_for(terminal)
        if literal is not None and literal.startswith(context.partial):
            candidates.append(Candidate(literal, literal, -len(context.partial)))

    needs_space = (
        not context.partial
        and bool(source_before_cursor)
        and not source_before_cursor[-1].isspace()
    )
    for name, is_root, is_matcher in names:
        if not name.startswith(context.partial):
            continue
        after = context.after
        suffix = "" if not is_matcher or after.lstrip().startswith("(") else "("
        insertion = name + suffix
        if is_root and needs_space:
            # At the exact end of `match` or `let name =`, append after the
            # existing grammar token instead of replacing it.
            insertion = " " + insertion
            start_position = 0
        else:
            start_position = -len(context.partial)
        candidates.append(Candidate(insertion, name + suffix, start_position))

    seen: set[tuple[str, int]] = set()
    result: list[Candidate] = []
    for item in sorted(candidates, key=lambda candidate: candidate.display):
        if item.text in _PUNCTUATION and context.after.startswith(item.text):
            continue
        if item.display.startswith(".bind") and context.after.startswith(".bind"):
            continue
        key = (item.text, item.start_position)
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _literal_for(terminal: str) -> str | None:
    for candidate in parser().terminals:
        if candidate.name != terminal:
            continue
        if isinstance(candidate.pattern, PatternStr):
            return candidate.pattern.value
        return _REGEX_LITERALS.get(terminal)
    return None
