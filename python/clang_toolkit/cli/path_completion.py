"""Filesystem candidates restricted to path roles in the shared Lark grammar."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from lark import Token

from prompt_toolkit.completion import Completion
from prompt_toolkit.document import Document

from clang_toolkit.cli.completion_context import accepted_after
from clang_toolkit.cli.language import lex
from clang_toolkit.cli.runtime.templates import TemplateError, evaluate_string

PATH_ROLES = frozenset({"FILE_STRING", "DIRECTORY_STRING", "PATH_STRING"})


@dataclass(frozen=True)
class PathContext:
    start: int
    spelling: str
    quote: str
    directories_only: bool
    relative_only: bool
    has_closing_quote: bool


def _no_interpolation(_tree: object) -> str:
    raise TemplateError("path completion requires a literal path")


def path_context(document: Document) -> PathContext | None:
    """Locate a path atom using accepted terminal roles, including unfinished input.

    Command structure comes exclusively from Lark. Only the editable path atom
    is decoded here; invalid matcher/string prefixes never reach the filesystem.
    """
    source = document.text_before_cursor
    tokens = lex(source)
    prefix: list[Token] = []
    for token in tokens:
        if token.type == "WS":
            continue
        roles = accepted_after(prefix) & PATH_ROLES
        if roles:
            raw = source[token.start_pos :]
            # References and expressions retain their existing providers.
            if token.type in {"DOLLAR", "LSQB", "GLOB", "PARSE", "MATCH", "IN"}:
                prefix.append(token)
                continue
            context = _atom(document, token.start_pos, raw, roles)
            if context is not None:
                return context
        prefix.append(token)
    roles = accepted_after(prefix) & PATH_ROLES
    if roles and (not source or source[-1].isspace()):
        return _atom(document, len(source), "", roles)
    # An exact path-taking keyword also accepts a path at its end. The atom
    # provider inserts a separator, just as matcher completion does for match.
    if roles:
        return _atom(document, len(source), "", roles)
    return None


def _atom(
    document: Document, start: int, raw: str, roles: set[str]
) -> PathContext | None:
    quote = raw[0] if raw.startswith(("'", '"')) else "'"
    suffix = document.text_after_cursor
    closing_quote = bool(raw) and suffix.startswith(quote)
    if (
        suffix
        and not closing_quote
        and not suffix[0].isspace()
        and suffix[0] not in ")]},;"
    ):
        return None
    if raw.startswith(("'", '"')):
        atom_tokens = lex(raw)
        first = atom_tokens[0]
        if first.type not in {
            "STRING",
            "FILE_STRING",
            "DIRECTORY_STRING",
            "PATH_STRING",
            "OPEN_STRING",
        }:
            return None
        try:
            if first.type == "OPEN_STRING":
                spelling = evaluate_string(raw + quote, _no_interpolation)
            else:
                trailing = raw[first.end_pos :]
                if any(char.isspace() for char in trailing) or any(
                    char in trailing for char in "\"'()[]{},;$"
                ):
                    return None
                # Allow typing a new basename after a completed quoted directory
                # and then pressing Tab: 'directory/'fi -> 'directory/file.cc'.
                spelling = evaluate_string(str(first), _no_interpolation) + trailing
        except TemplateError:
            return None
    else:
        if any(char.isspace() for char in raw) or any(
            char in raw for char in "\"'()[]{},;$"
        ):
            return None
        spelling = raw
    return PathContext(
        start,
        spelling,
        quote,
        "DIRECTORY_STRING" in roles,
        "PATH_STRING" in roles,
        closing_quote,
    )


def _quoted(path: str, quote: str, *, close: bool) -> str:
    body = path.replace("\\", "\\\\").replace(quote, "\\" + quote)
    body = body.replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")
    if quote == '"':
        body = body.replace("$", "\\$")
    return quote + body + (quote if close else "")


def path_completions(document: Document, cwd: Path) -> list[Completion]:
    """List safe, quoted file/directory insertions; inaccessible paths are empty."""
    context = path_context(document)
    if context is None:
        return []
    try:
        spelling = os.path.expanduser(context.spelling)
        if context.relative_only and Path(spelling).is_absolute():
            return []
        parent_text, basename = os.path.split(spelling)
        parent = Path(parent_text or ".")
        if not parent.is_absolute():
            parent = cwd / parent
        entries = sorted(parent.iterdir(), key=lambda entry: entry.name)
        choices = []
        for entry in entries:
            if not entry.name.startswith(basename):
                continue
            try:
                directory = entry.is_dir()
                if not directory and (context.directories_only or not entry.is_file()):
                    continue
            except OSError:
                continue
            path = os.path.join(parent_text, entry.name)
            if directory:
                path += "/"
            insertion = _quoted(
                path, context.quote, close=not context.has_closing_quote
            )
            if (
                context.start == document.cursor_position
                and document.text_before_cursor
                and not document.text_before_cursor[-1].isspace()
            ):
                insertion = " " + insertion
            choices.append(
                Completion(
                    insertion,
                    start_position=context.start - document.cursor_position,
                    display=entry.name + ("/" if directory else ""),
                    display_meta="directory" if directory else "file",
                )
            )
        return choices
    except (OSError, ValueError, RuntimeError):
        # Missing directories, denied traversal, invalid NULs and unknown home
        # users are normal while editing, rather than console errors.
        return []
