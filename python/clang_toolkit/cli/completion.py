"""Grammar-aware completion adapter for prompt_toolkit."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from typing import Any
from pathlib import Path

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document

from clang_toolkit.cli.completion_candidates import candidates_for
from clang_toolkit.cli.completion_context import accepted_after, has_field_argument
from clang_toolkit.cli.completion_cursor import cursor_context
from clang_toolkit.cli.matcher_catalog import NESTED_MATCHERS, ROOT_MATCHERS
from clang_toolkit.cli.path_completion import path_completions
from clang_toolkit.cli.help import COMMAND_HELP


class ReplCompleter(Completer):
    """Suggest accepted grammar roles and offline matcher catalog entries."""

    def __init__(
        self,
        matchers: Iterable[str] | None = None,
        references: Mapping[str, Iterable[str]]
        | Callable[[], Mapping[str, Iterable[str]]]
        | None = None,
        *,
        field_resolver: Callable[[str], Iterable[object]] | None = None,
        presence_resolver: Callable[[str], Iterable[str]] | None = None,
        root_matchers: Iterable[str] | None = None,
        cwd: Path | None = None,
    ) -> None:
        custom = tuple(dict.fromkeys(matchers)) if matchers is not None else None
        nested = custom if custom is not None else NESTED_MATCHERS
        roots = root_matchers if root_matchers is not None else custom
        if roots is None:
            roots = ROOT_MATCHERS
        self._nested_matchers = tuple(dict.fromkeys(nested))
        self._root_matchers = tuple(dict.fromkeys(roots))
        self._references = references
        self._field_resolver = field_resolver
        self._presence_resolver = presence_resolver
        self._cwd = cwd

    def get_completions(
        self, document: Document, complete_event: Any
    ) -> Iterable[Completion]:
        del complete_event
        source = document.text
        cursor = document.cursor_position
        context = cursor_context(source, cursor)
        if context is not None:
            presence = has_field_argument(context.prefix_tokens, source[:cursor])
            if presence is not None:
                reference, quote, partial, start_position, quote_open = presence
                if self._presence_resolver is not None:
                    try:
                        fields = tuple(self._presence_resolver(reference))
                    except (KeyError, LookupError, TypeError, ValueError):
                        fields = ()
                    for field_name in fields:
                        if not isinstance(field_name, str) or not field_name.startswith(
                            partial
                        ):
                            continue
                        escaped = field_name.replace("\\", "\\\\").replace(
                            quote, "\\" + quote
                        )
                        closing_quote_exists = document.text[cursor:].startswith(quote)
                        insertion = (
                            escaped + ("" if closing_quote_exists else quote)
                            if quote_open
                            else quote + escaped + quote
                        )
                        yield Completion(
                            insertion,
                            start_position=start_position,
                            display=field_name,
                            display_meta="field presence",
                        )
                return
        yield from path_completions(document, self._cwd or Path.cwd())
        if context is None:
            return
        accepted = accepted_after(context.prefix_tokens)
        if "HELP_WORD" in accepted:
            prefix = " ".join(str(token) for token in context.prefix_tokens[1:])
            for topic in COMMAND_HELP:
                if prefix:
                    if not topic.startswith(prefix + " "):
                        continue
                    topic = topic[len(prefix) + 1 :]
                if topic.startswith(context.partial):
                    yield Completion(topic, start_position=-len(context.partial))
            return
        current_references = (
            self._references() if callable(self._references) else self._references
        )
        references = {
            name: tuple(dict.fromkeys(fields))
            for name, fields in (current_references or {}).items()
        }
        for item in candidates_for(
            context,
            accepted,
            self._root_matchers,
            self._nested_matchers,
            references,
            source[:cursor],
            self._field_resolver,
        ):
            yield Completion(
                item.text,
                start_position=item.start_position,
                display=item.display,
                display_meta=item.display_meta,
            )
