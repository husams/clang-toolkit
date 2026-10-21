"""Indexed-project literals and a nonblocking catalog snapshot for the editor."""

from __future__ import annotations

import asyncio
import time
from collections import Counter
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from lark import Token
from prompt_toolkit.application import Application
from prompt_toolkit.application.current import set_app
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.completion import CompleteEvent, Completer, Completion
from prompt_toolkit.document import Document

from clang_toolkit.cli.completion_context import accepted_after
from clang_toolkit.cli.language import lex
from clang_toolkit.cli.path_completion import _no_interpolation, _quoted
from clang_toolkit.cli.runtime.templates import TemplateError, evaluate_string
from clang_toolkit.cursors import CursorError
from clang_toolkit.client import QueryError


@dataclass(frozen=True)
class IndexedProject:
    root: str
    name: str


ProjectEntry = str | IndexedProject


@dataclass(frozen=True)
class ProjectContext:
    start: int
    partial: str
    quote: str
    tail: str
    separator: str


def project_context(document: Document) -> ProjectContext | None:
    """Find the project STRING role of index find using formal grammar tokens."""
    cursor = document.cursor_position
    if "index" not in document.text_before_cursor:
        return None
    tokens = lex(document.text, batch=True)
    native = next(
        (
            token
            for token in reversed(tokens)
            if str(token) == "index" and token.start_pos < cursor
        ),
        None,
    )
    if native is None:
        return None
    offset = int(native.start_pos)
    if offset:
        # A compiled runnable header is outside the legacy grammar. Re-lex the
        # native operand so Lark can supply its contextual terminal types.
        tokens = lex(document.text[offset:], batch=True)
    prefix: list[Token] = []
    for token in tokens:
        if offset + token.start_pos >= cursor:
            break
        if token.type == "COMMENT":
            if cursor <= offset + token.end_pos:
                return None
            continue
        if token.type == "WS":
            continue
        if _project_role(prefix):
            return _project_atom(document, offset + int(token.start_pos), token, offset)
        if token.type == "INDEX":
            prefix = [token]
        elif prefix:
            prefix.append(token)
    if _project_role(prefix):
        return _project_atom(document, cursor, None)
    return None


def _project_role(prefix: list[Token]) -> bool:
    return (
        len(prefix) >= 2
        and prefix[0].type == "INDEX"
        and ((prefix[1].type in {"STATUS", "PAUSE", "RESUME", "CANCEL", "RENAME"}
              and len(prefix) == 2)
             or (prefix[1].type in {"FIND", "LOOKUP"} and prefix[-1].type == "IN"))
        and "STRING" in accepted_after(prefix)
    )


def _project_atom(
    document: Document,
    start: int,
    token: Token | None,
    offset: int = 0,
) -> ProjectContext | None:
    raw = document.text[start : document.cursor_position]
    quote = raw[0] if raw.startswith(('"', "'")) else '"'
    tail = ""
    if raw.startswith(('"', "'")):
        if token is None or token.type not in {"STRING", "OPEN_STRING"}:
            return None
        if token.type == "STRING":
            if document.cursor_position >= offset + token.end_pos:
                return None
            tail = document.text[document.cursor_position : offset + token.end_pos]
        try:
            partial = evaluate_string(raw + quote, _no_interpolation)
        except TemplateError:
            return None
    else:
        if any(char.isspace() or char in "\"'()[]{};,$#" for char in raw):
            return None
        if (
            document.text_after_cursor
            and not document.text_after_cursor[0].isspace()
            and document.text_after_cursor[0] not in ")]},;"
        ):
            return None
        partial = raw
    separator = (
        " "
        if start == document.cursor_position
        and document.text_before_cursor
        and not document.text_before_cursor[-1].isspace()
        else ""
    )
    return ProjectContext(start, partial, quote, tail, separator)


def project_completions(
    document: Document, context: ProjectContext, roots: Iterable[ProjectEntry]
) -> list[Completion]:
    projects = sorted({(entry, Path(entry).name or entry) if isinstance(entry, str)
                       else (entry.root, entry.name or Path(entry.root).name)
                       for entry in roots if entry})
    counts = Counter(name for root, name in projects)
    matches = []
    for root, name in projects:
        use_path = "/" in context.partial or counts[name] > 1
        value = root if use_path else name
        if not (
            name.casefold().startswith(context.partial.casefold())
            or root.casefold().startswith(context.partial.casefold())
        ):
            continue
        literal = _quoted(value, context.quote, close=True)
        if context.tail:
            if not literal.endswith(context.tail):
                continue
            literal = literal[: -len(context.tail)]
        matches.append(
            Completion(
                context.separator + literal,
                start_position=context.start - document.cursor_position,
                display=name,
                display_meta=f"indexed project · {root}",
            )
        )
    return matches


def refresh_project_menu(buffer: Buffer, app: Application) -> None:
    """Show an asynchronously loaded catalog only if the cursor still needs it."""
    if app.is_running and project_context(buffer.document) is not None:
        with set_app(app):
            buffer.cancel_completion()
            buffer.start_completion(select_first=False)
        app.invalidate()


class ProjectCompleter(Completer):
    """Compose project suggestions with any of the existing console engines."""

    def __init__(self, base: Completer, projects: Callable[[], Iterable[ProjectEntry]]) -> None:
        self.base = base
        self._projects = projects

    def get_completions(
        self,
        document: Document,
        complete_event: CompleteEvent,
    ) -> Iterable[Completion]:
        context = project_context(document)
        if context is not None:
            yield from project_completions(document, context, self._projects())
        else:
            yield from self.base.get_completions(document, complete_event)


class ProjectCompletionCache:
    """Keep typing local; coalesce catalog refreshes with a bounded RPC deadline."""

    def __init__(self, *, ttl: float = 5.0, timeout: float = 2.0) -> None:
        self._ttl = ttl
        self._timeout = timeout
        self._roots: tuple[ProjectEntry, ...] = ()
        self._next_refresh = 0.0
        self._loader: Callable[[], Awaitable[Iterable[ProjectEntry]]] | None = None
        self._on_update: Callable[[], None] | None = None
        self._task: asyncio.Task[None] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def bind(
        self,
        loader: Callable[[], Awaitable[Iterable[ProjectEntry]]],
        on_update: Callable[[], None],
    ) -> None:
        self._loop = asyncio.get_running_loop()
        self._loader = loader
        self._on_update = on_update

    def get(self) -> tuple[ProjectEntry, ...]:
        loop = self._loop
        if self._loader is not None and loop is not None and time.monotonic() >= self._next_refresh:
            try:
                current = asyncio.get_running_loop()
            except RuntimeError:
                current = None
            if current is loop:
                self._start_refresh()
            elif not loop.is_closed():
                # Completion runs in a worker, but RPCs and menu updates belong
                # to the UI loop. Return the immutable snapshot immediately.
                loop.call_soon_threadsafe(self._start_refresh)
        return self._roots

    def _start_refresh(self) -> None:
        # Recheck after crossing threads: close or another refresh may win.
        if self._loader is not None and time.monotonic() >= self._next_refresh:
            if self._task is None or self._task.done():
                self._task = asyncio.get_running_loop().create_task(self._refresh())

    async def _refresh(self) -> None:
        loader = self._loader
        if loader is None:
            return
        try:
            roots = tuple(sorted(set(await asyncio.wait_for(loader(), self._timeout)),
                                 key=lambda entry: entry if isinstance(entry, str) else entry.root))
            if roots != self._roots:
                self._roots = roots
                if self._on_update is not None:
                    self._on_update()
        except (CursorError, QueryError, TimeoutError, OSError):
            # Completion remains usable offline and retains the last good list.
            pass
        finally:
            self._next_refresh = time.monotonic() + self._ttl

    async def aclose(self) -> None:
        self._loader = None
        if self._task is not None and not self._task.done():
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
