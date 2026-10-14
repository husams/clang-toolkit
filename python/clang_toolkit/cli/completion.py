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
from clang_toolkit.cli.matcher_catalog import NESTED_MATCHERS, ROOT_MATCHERS, matcher_hint
from clang_toolkit.cli.path_completion import path_completions
from clang_toolkit.cli.help import COMMAND_HELP, MATCHER_HELP
from clang_toolkit.cli.callable_help import CallableHelp


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
        matcher_functions: Iterable[str] | Callable[[], Iterable[str]] | None = None,
        function_help: Mapping[str, CallableHelp]
        | Callable[[], Mapping[str, CallableHelp]]
        | None = None,
        cwd: Path | None = None,
    ) -> None:
        custom = tuple(dict.fromkeys(matchers)) if matchers is not None else None
        nested = custom if custom is not None else NESTED_MATCHERS
        roots = root_matchers if root_matchers is not None else custom
        if roots is None:
            roots = ROOT_MATCHERS
        self._nested_matchers = tuple(dict.fromkeys(nested))
        self._root_matchers = tuple(dict.fromkeys(roots))
        self._matcher_names = frozenset((*self._nested_matchers, *self._root_matchers))
        self._matcher_functions = matcher_functions
        self._function_help = function_help
        self._references = references
        self._field_resolver = field_resolver
        self._presence_resolver = presence_resolver
        self._cwd = cwd

    def get_completions(
        self, document: Document, complete_event: Any
    ) -> Iterable[Completion]:
        source = document.text
        cursor = document.cursor_position
        # Completion parses the whole editable command to recover its Lark
        # context. On very long partial strings this is unnecessary work and
        # can stall typing; the command is still parsed normally on submission.
        if cursor > 8192 or (
            cursor > 512
            and (complete_event is None or not complete_event.completion_requested)
        ):
            return
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
        if context is None or context.in_string:
            return
        accepted = accepted_after(context.prefix_tokens)
        # Completed commands should remain editable history drafts. An implicit
        # optional keyword menu makes Up/Down insert a continuation instead.
        # Explicit Tab and typing whitespace still offer those continuations.
        if (
            complete_event is not None
            and not complete_event.completion_requested
            and "$END" in accepted
            and source[:cursor]
            and not source[cursor - 1].isspace()
        ):
            return
        functions_help = self.function_descriptions()
        if "HELP_WORD" in accepted:
            prefix = " ".join(str(token) for token in context.prefix_tokens[1:])
            topics = {**COMMAND_HELP, **MATCHER_HELP}
            if prefix == "matchers":
                topics.update(
                    {f"matchers {name}": entry for name, entry in MATCHER_HELP.items()}
                )
            for topic, entry in topics.items():
                if prefix:
                    if not topic.startswith(prefix + " "):
                        continue
                    topic = topic[len(prefix) + 1 :]
                if topic.startswith(context.partial) and topic.endswith(
                    context.word_suffix
                ):
                    insertion = (
                        topic[:-len(context.word_suffix)]
                        if context.word_suffix else topic
                    )
                    yield Completion(
                        insertion,
                        start_position=-len(context.partial),
                        display=topic,
                        display_meta=matcher_hint(entry.topic) or entry.purpose,
                    )
            if not prefix:
                for name, entry in functions_help.items():
                    if name.startswith(context.partial) and name.endswith(
                        context.word_suffix
                    ):
                        insertion = (
                            name[:-len(context.word_suffix)]
                            if context.word_suffix else name
                        )
                        yield Completion(
                            insertion, start_position=-len(context.partial),
                            display=name, display_meta=entry.hint,
                        )
            return
        current_references = (
            self._references() if callable(self._references) else self._references
        )
        references = {
            name: tuple(dict.fromkeys(fields))
            for name, fields in (current_references or {}).items()
        }
        functions = tuple(self._matcher_functions() if callable(self._matcher_functions)
                          else self._matcher_functions or ())
        functions = tuple(dict.fromkeys((*functions, *functions_help)))
        for item in candidates_for(
            context,
            accepted,
            (*self._root_matchers, *functions),
            (*self._nested_matchers, *functions),
            references,
            source[:cursor],
            self._field_resolver,
        ):
            metadata = item.display_meta
            if metadata is None:
                name = item.display.removesuffix("(")
                if name in functions:
                    metadata = (
                        functions_help[name].hint if name in functions_help
                        else f"user defined · {name}(…)"
                    )
                elif (
                    {"ROOT_MATCHER_NAME", "MATCHER_NAME"} & accepted
                    and name in self._matcher_names
                ):
                    metadata = matcher_hint(name) or "AST matcher"
                elif item.display in COMMAND_HELP:
                    metadata = COMMAND_HELP[item.display].purpose
                else:
                    metadata = "language keyword"
            yield Completion(
                item.text,
                start_position=item.start_position,
                display=item.display,
                display_meta=metadata,
            )

    def function_descriptions(self) -> Mapping[str, CallableHelp]:
        return (
            self._function_help() if callable(self._function_help)
            else self._function_help or {}
        )
