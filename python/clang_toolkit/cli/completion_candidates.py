"""Turn accepted grammar roles into filtered prompt_toolkit candidates."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass

from lark.lexer import PatternStr
from lark.exceptions import UnexpectedInput

from clang_toolkit.cli.completion_context import reference_base
from clang_toolkit.cli.completion_cursor import CursorContext
from clang_toolkit.cli.language import parser, reference_parser

_REGEX_LITERALS = {
    "BACKGROUND": "background",
    "PARSE": "parse",
    "READ": "read",
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
    "EDGES": "edges",
    "OPTION": "option", "FUNCTIONS": "functions", "BLOCKS": "blocks", "ELEMENTS": "elements",
    "DEPTH": "depth",
    "NODES": "nodes",
    "IMPLICIT": "implicit",
    "INSTANTIATIONS": "instantiations",
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
    "COMPILE_COMMANDS": "compile_commands",
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
    "LIST": "list", "ATTACH": "attach", "SERVER": "server", "STATUS": "status",
    "CACHE": "cache", "PRUNE": "prune", "BINDINGS": "bindings", "BINDING": "binding",
    "DROP": "drop", "RENAME": "rename", "APPEND": "append",
    "START": "start",
    "PAUSE": "pause",
    "RESUME": "resume",
    "LABEL": "label",
    "MODE": "mode",
    "REPLACE": "replace",
}
_NO_VALUE_TERMINALS = {"STRING", "OPEN_STRING", "NUMBER", "DOLLAR", "SEMICOLON"}
_PUNCTUATION = {"(", ")", "]", "}", ",", "."}
_METHOD_NAMES = {"hasField", "fieldState", "fieldOr", "joinWith", "unique", "sort", "filter"}


@dataclass(frozen=True)
class Candidate:
    text: str
    display: str
    start_position: int
    display_meta: str | None = None


def candidates_for(
    context: CursorContext,
    accepted: set[str],
    root_matchers: Iterable[str],
    nested_matchers: Iterable[str],
    references: Mapping[str, Iterable[str]],
    source_before_cursor: str,
    field_resolver: Callable[[str], Iterable[object]] | None = None,
) -> list[Candidate]:
    """Build candidates for accepted terminal roles and the current prefix."""
    names: list[tuple[str, bool, bool, str | None]] = []
    matcher_roles = {"ROOT_MATCHER_NAME", "MATCHER_NAME"}
    root_role = "ROOT_MATCHER_NAME" in accepted
    if root_role:
        names.extend((name, True, True, None) for name in root_matchers)
        if (
            source_before_cursor.lstrip().startswith("let ")
            and "=" in source_before_cursor
        ):
            names.extend((name, True, True, None) for name in nested_matchers)
    if "MATCHER_NAME" in accepted:
        names.extend((name, False, True, None) for name in nested_matchers)

    previous = context.prefix_tokens[-1].type if context.prefix_tokens else None
    if "NAME" in accepted and previous == "DOLLAR":
        names.extend((name, False, False, None) for name in references)
    elif "NAME" in accepted and previous in {"PRUNE", "AS"}:
        options = ("memory", "disk", "all") if previous == "PRUNE" else ("yaml", "json", "csv", "proto")
        names.extend((name, False, False, None) for name in options)
    elif ({"NAME", "JOIN_WITH", "HAS_FIELD"} & accepted) and previous == "DOT":
        reference = _reference_before_terminal_dot(context, source_before_cursor)
        fields: tuple[object, ...] = ()
        if reference is not None and field_resolver is not None:
            try:
                fields = tuple(field_resolver(reference))
            except (KeyError, LookupError, TypeError, ValueError):
                fields = ()
        if not fields and reference is not None:
            # Keep the original root-level mapping API working for callers that
            # have not supplied a resolver. Never apply it to nested paths.
            root = reference_base(context.prefix_tokens)
            if reference == f"${root}":
                fields = references.get(root, ())
        for field in fields:
            if isinstance(field, str):
                # Preserve the original callback and mapping API. Structured
                # runtime results carry their method/property kind explicitly.
                name = field
                is_method = name in _METHOD_NAMES
                display_meta = "method" if is_method else "field"
            else:
                name = str(getattr(field, "name", ""))
                if not name:
                    continue
                is_method = getattr(field, "kind", None) == "method"
                display_meta = getattr(field, "display_meta", None)
            names.append((name, False, is_method, display_meta))

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
    for name, is_root, is_matcher, display_meta in names:
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
        candidates.append(
            Candidate(insertion, name + suffix, start_position, display_meta)
        )

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


def _reference_before_terminal_dot(
    context: CursorContext, source_before_cursor: str
) -> str | None:
    """Return a grammar-validated reference immediately before its final dot."""
    dots = [token for token in context.prefix_tokens if token.type == "DOT"]
    if not dots:
        return None
    dot = dots[-1]
    start = getattr(dot, "start_pos", None)
    if start is None:
        return None
    prefix = source_before_cursor[: int(start)]
    dollar_positions = [
        int(token.start_pos)
        for token in context.prefix_tokens
        if token.type == "DOLLAR"
        and getattr(token, "start_pos", None) is not None
        and int(token.start_pos) < int(start)
    ]
    for reference_start in reversed(dollar_positions):
        candidate = prefix[reference_start:]
        try:
            reference_parser().parse(candidate)
        except UnexpectedInput:
            continue
        return candidate
    return None


def _literal_for(terminal: str) -> str | None:
    for candidate in parser().terminals:
        if candidate.name != terminal:
            continue
        if isinstance(candidate.pattern, PatternStr):
            return candidate.pattern.value
        return _REGEX_LITERALS.get(terminal)
    return None
