"""Typed expression evaluator for the Python interactive shell."""

from __future__ import annotations

import os
import threading
from glob import has_magic, iglob
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import grpc
from lark import Token, Tree
from lark.exceptions import UnexpectedInput

from clang_toolkit.cli.language import parser
from clang_toolkit.cli.help import HAS_NATIVE_ANALYSIS_GRAMMAR, render_help
from clang_toolkit.cli.matcher_catalog import (
    NESTED_MATCHERS,
    ROOT_MATCHERS,
    VALIDATION_NESTED_MATCHERS,
)
from clang_toolkit.client import Client
from clang_toolkit.cursors import CursorError
from clang_toolkit.analysis_error import AnalysisError

from .resource_errors import is_receive_size_rejection
from clang_toolkit.match_values import (
    BindingSelection,
    MatchRow,
    MatchValue,
    MatchValueError,
    NativeBindingCollection,
    NativeMatchCollection,
    ParsedTree,
)
from clang_toolkit.resources import FileBatch, FileHandle, FileSet, InputDescriptor

from .config import ConfigError, ConfigStore
from .filesystem import Directory, File, FileSystemEntry, from_path
from .references import (
    ReferenceError,
    call_method,
    field_names,
    index_value,
    is_semantic_view,
    property_value,
)
from .semantic import MessageView, field_sources
from .templates import TemplateError, evaluate_string
from .history import HistoryStore
from .output import OutputSink
from .persistence import load, read_document, save
from .values import (
    MatchSet,
    MatcherExpr,
    QualifiedName,
    matcher_text,
    render,
    render_inspection,
)
from .cursors import execute_cursor
from .traversal import execute_traversal
from .matcher_functions import MatcherFunction


class EvaluationError(ValueError):
    """A valid sentence that cannot be evaluated in this runtime."""


@dataclass(frozen=True)
class CompletionField:
    """A local completion option with runtime-derived display metadata."""

    name: str
    kind: str
    display_meta: str


# Completion suggestions do not extend local rejection of matcher expressions.
# Concrete node constructors in the registry remain valid top-level matchers.
_KNOWN_NON_ROOT = frozenset(VALIDATION_NESTED_MATCHERS) - frozenset(ROOT_MATCHERS)
_PUNCTUATION = {"LPAR", "RPAR", "LSQB", "RSQB", "COMMA", "DOT", "SCOPE"}
_SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".c++", ".C", ".m", ".mm"}
MAX_CONSOLE_COLLECTION_ITEMS = 10_000
_COLLECTION_VALUE_KINDS = frozenset(
    {"push_command", "delete_command", "set_item_command"}
)
_COMMAND_VALUE_KINDS = frozenset(
    {
        "match", "background", "print", "inspect", "set_command", "clear_command",
        "add_arg", "save_command", "load_command", "history_save", "history_clear",
        "session_label", "session_start", "session_add", "session_match", "session_pause",
        "session_resume", "session_close", "session_list", "session_attach",
        "session_close_retained", "server_status", "cache_status", "cache_prune",
        "bindings_list", "binding_drop", "binding_rename", "cfg", "cfg_file",
        "callgraph", "callgraph_file", "help", "help_shortcut", "traverse", "script",
        "cursor_open", "cursor_continue", "cursor_restart", "cursor_close",
        "import_command", "file_open", "file_list", "file_info", "file_close",
        "file_refresh", "resource_status", "batch_statement",
    }
)


def _simple_reference_name(node: Tree) -> str:
    if node.data != "reference" or len(node.children) != 2:
        raise EvaluationError("target must be a simple variable")
    return str(node.children[1])


def _contains_live_native_value(value: Any, seen: set[int] | None = None) -> bool:
    if seen is None:
        seen = set()
    if isinstance(
        value,
        (
            FileHandle,
            ParsedTree,
            MatchValue,
            MatchRow,
            BindingSelection,
            NativeMatchCollection,
            NativeBindingCollection,
            MatcherFunction,
        ),
    ):
        return True
    if isinstance(value, MatcherExpr):
        identity = id(value)
        if identity in seen:
            return False
        seen.add(identity)
        return any(_contains_live_native_value(item, seen) for item in value.arguments)
    if isinstance(value, MatchSet):
        identity = id(value)
        if identity in seen:
            return False
        seen.add(identity)
        return any(_contains_live_native_value(item, seen) for item in value.rows)
    if isinstance(value, Mapping | list | tuple):
        identity = id(value)
        if identity in seen:
            return False
        seen.add(identity)
        items = value.values() if isinstance(value, Mapping) else value
        return any(_contains_live_native_value(item, seen) for item in items)
    return False


class Runtime:
    """One REPL session's lexical values, settings view, and request identity."""

    def __init__(
        self,
        client: Client,
        *,
        cwd: Path | None = None,
        environment: Mapping[str, str] | None = None,
        config_vars: Mapping[str, Any] | None = None,
        config_store: ConfigStore | None = None,
        history: HistoryStore | None = None,
        session_id: UUID | None = None,
    ) -> None:
        self.client = client
        self.cwd = (cwd or Path.cwd()).resolve()
        self.environment = environment if environment is not None else os.environ
        self.config_store = config_store or ConfigStore(self.cwd)
        if self.config_store.effective["compile_commands"] is None:
            selected = getattr(client, "compilation_database", None)
            if selected is not None:
                self.config_store.effective["compile_commands"] = str(selected)
        self.config_vars = {
            **self.config_store.effective["vars"],
            **(config_vars or {}),
        }
        self.output = OutputSink(self.cwd, self.config_store.effective["output"])
        self.session_id = session_id or uuid4()
        self.label: str | None = None
        self.history = history
        self.bindings: dict[str, Any] = {}
        self._scopes: list[dict[str, Any]] = []
        self._matcher_call_depth = 0
        self._default_targets: list[ParsedTree] = []
        self._block_owners: list[set[Any]] = []
        self._active_resource_scope: Any = None
        self._active_batch_inputs: tuple[InputDescriptor, ...] | None = None
        self._batch_file_outcomes: dict[tuple[str, str], str] = {}
        self._batch_unknown_file_outcomes: set[str] = set()
        self._batch_outcome_lock = threading.Lock()
        self._batch_cancel_requested = threading.Event()
        self._last_batch_file_outcomes: dict[tuple[str, str], str] = {}
        self._last_batch_unknown_file_count = 0
        self._last_batch_unattempted_file_count = 0
        self._batch_jobs: int | None = None
        self._successful_exports = 0
        self._value_context_depth = 0
        self._source_stack: list[str] = []
        self._exit_requested = False

    def request_batch_cancel(self) -> None:
        """Ask a foreground batch runner to stop after cancelling its scope."""
        self._batch_cancel_requested.set()

    def clear_batch_cancel(self) -> None:
        self._batch_cancel_requested.clear()

    def _apply_compilation_settings(self) -> None:
        selected = self.config_store.effective["compile_commands"]
        self.client.compilation_database = selected
        bound = getattr(self.client, "_async_client", None)
        if bound is not None:
            bound.compilation_database = selected

    def evaluate(self, source: str) -> Any:
        """Evaluate any command or expression and return its raw value."""
        statement = parser().parse(source).children[0]
        if not isinstance(statement, Tree):
            raise EvaluationError("expected an expression")
        self._apply_compilation_settings()
        if statement.data in {"quit", "exit"}:
            raise EvaluationError(
                "expected an expression or assignment; quit and exit are control-flow commands"
            )
        return self._evaluate_statement_once(statement, source, value_context=True)[0]

    def execute(self, source: str) -> str | None:
        """Evaluate a parsed command and return output; ``None`` means exit."""
        if self.history is not None:
            self.history.append(source, self.session_id, self.label)
        statement = parser().parse(source).children[0]
        if not isinstance(statement, Tree):
            raise EvaluationError("expected a statement")
        return self._execute_statement(statement, source)

    def _execute_statement(self, statement: Tree, source: str) -> str | None:
        """Execute one command and return its standalone display text."""
        _, display = self._evaluate_statement_once(
            statement, source, value_context=False
        )
        if str(statement.data) in {"quit", "exit"} or self._exit_requested:
            self._exit_requested = False
            return None
        return display or ""

    def _evaluate_statement_once(
        self, statement: Tree, source: str, *, value_context: bool
    ) -> tuple[Any, str | None]:
        """Run one statement exactly once, separating value from display."""
        kind = str(statement.data)
        if kind in {"quit", "exit"}:
            return None, None
        self._apply_compilation_settings()
        self._source_stack.append(source)
        if value_context:
            self._value_context_depth += 1
        try:
            if kind == "assignment":
                return self._assignment(statement), None
            if kind == "matcher_definition":
                return self._define_matcher(statement), None
            if kind == "display":
                expression = statement.children[0]
                if (
                    isinstance(expression, Tree)
                    and expression.data in {
                        "foreach_expression", "foreach_statement_expression"
                    }
                    and self._is_foreach_statement_block(expression)
                ):
                    value = self._foreach(
                        expression, source=source, value_context=value_context
                    )
                    if self._is_foreach_statement_block(expression):
                        display = None if value_context else (value or "")
                    else:
                        display = None if value_context else self._emit_output(render(value))
                    return value, display
                value = self._evaluate(expression)
                display = None if value_context else self._emit_output(render(value))
                return value, display
            if kind in _COMMAND_VALUE_KINDS | _COLLECTION_VALUE_KINDS:
                value, display = self._evaluate_command_statement(
                    statement, source, value_context=value_context
                )
                return value, display
            # These statements are effect-only or retain an existing textual
            # result. Their dispatcher is already single-execution; output is
            # suppressed while evaluating into a value.
            display = self._execute_statement_legacy(statement, source)
            return None, display
        finally:
            if value_context:
                self._value_context_depth -= 1
            self._source_stack.pop()

    def _evaluate_command_statement(
        self, statement: Tree, source: str, *, value_context: bool
    ) -> tuple[Any, str | None]:
        """Evaluate a command node once, returning its value and optional display."""
        kind = str(statement.data)
        if kind == "batch_statement":
            from .batch_execution import execute_batch, render_batch_report

            report = execute_batch(self, statement, source, value_context=value_context)
            if value_context:
                return report, None
            if report.get("status") == "failed":
                error = EvaluationError(f"batch failed: {render_batch_report(report)}")
                error.report = report
                raise error
            display = self._emit_output(render_batch_report(report))
            return report, display
        if kind in {"file_open", "file_list", "file_info", "file_close", "file_refresh", "resource_status"}:
            from .file_commands import execute_file_command, render_file_command

            value = execute_file_command(self, statement)
            display = None if value_context else self._emit_output(render_file_command(kind, value))
            return value, display
        if kind == "match":
            if self._match_block(statement) is not None:
                from .match_block import execute_match_block

                output = execute_match_block(self, statement, source)
                return output or "", None if value_context else output
            value = self._execute_match(statement, source=source)
            display = None if value_context else self._emit_output(render(value))
            return value, display
        if kind == "traverse":
            from .graph_options import render_graph
            from .traversal import execute_traversal

            value = execute_traversal(self, statement)
            display = None if value_context else self._emit_output(render_graph(value))
            return value, display
        if kind == "cfg_file":
            from .control_flow import execute_cfg
            from .graph_options import render_graph

            value = execute_cfg(self, statement, source)
            display = None if value_context else self._emit_output(render_graph(value))
            return value, display
        if kind == "callgraph_file":
            from .call_graph import execute_call_graph
            from .graph_options import render_graph

            value = execute_call_graph(self, statement)
            display = None if value_context else self._emit_output(render_graph(value))
            return value, display
        if kind == "script":
            from .scripting import execute_script, render_script_response
            from .semantic import view

            response = execute_script(self, statement)
            value = view(response)
            display = None if value_context else self._emit_output(render_script_response(response))
            return value, display
        if kind in {"help", "help_shortcut"}:
            value = render_help(statement)
            return value, None if value_context else value
        if kind == "inspect":
            inspected = self._evaluate(statement.children[1])
            value = render_inspection(inspected)
            return value, None if value_context else self._emit_output(value)
        if kind == "bindings_list":
            value = dict(self.bindings)
            display = self._execute_statement_legacy(statement, source)
            return value, None if value_context else display
        if kind in {"cursor_open", "cursor_continue", "cursor_restart", "cursor_close"}:
            from .cursors import execute_cursor, render_cursor
            from .semantic import view

            response = execute_cursor(self, statement)
            value = view(response) if response is not None else None
            return value, None if value_context else self._emit_output(render_cursor(response))
        if kind == "print":
            value = self._evaluate(statement.children[1])
            if len(statement.children) > 3 and statement.children[3] is not None:
                text = render(value)
                destination = self._output_path(statement.children[3])
                append = any(
                    isinstance(item, Token) and item.type == "APPEND"
                    for item in statement.children
                )
                self.output.check_output(text)
                from .output import write_text

                write_text(destination, text, append=append)
                return value, None
            display = None if value_context else self._emit_output(render(value))
            return value, display
        if kind == "save_command":
            value = self._evaluate(statement.children[1])
            path = self._output_path(statement.children[3])
            format_name = (
                str(statement.children[-1])
                if len(statement.children) > 5 and statement.children[-1] is not None
                else None
            )
            save(value, path, format_name=format_name)
            self._successful_exports += 1
            return value, None
        if kind == "load_command":
            path = self._output_path(statement.children[1])
            value = load(path)
            into = next(
                (index for index, child in enumerate(statement.children)
                 if isinstance(child, Token) and child.type == "INTO"),
                None,
            )
            target = statement.children[into + 1] if into is not None else None
            if target is not None:
                if not isinstance(target, Tree) or target.data != "reference":
                    raise EvaluationError("load target must be a simple variable")
                name = _simple_reference_name(target)
                scope = self._scopes[-1] if self._scopes else self.bindings
                scope[name] = value
            return value, None
        if kind in {"server_status", "cache_status", "session_list", "cache_prune"}:
            from .management import execute_management_value

            value, text = execute_management_value(self, statement)
            return value, None if value_context else self._emit_output(text)
        if kind in _COLLECTION_VALUE_KINDS:
            self._collection_command(statement)
            if kind == "set_item_command":
                value = self._resolve_name(self._collection_parts(statement.children[1])[0])
            elif kind == "delete_command":
                value = self._resolve_name(self._collection_parts(statement.children[1])[0])
            else:
                value = self._resolve_collection_ref(statement.children[1])
            return value, None
        # Effect-only legacy commands already route all display through the sink.
        display = self._execute_statement_legacy(statement, source)
        return (display or None), None if value_context else display

    def _execute_statement_legacy(self, statement: Tree, source: str) -> str | None:
        """Dispatch a validated statement, including statements within a block."""
        kind = str(statement.data)
        self._apply_compilation_settings()
        if kind in {"quit", "exit"}:
            return None
        if kind in {"help", "help_shortcut"}:
            return render_help(statement)
        if kind in {
            "server_status",
            "cache_status",
            "cache_prune",
            "session_list",
            "session_attach",
            "session_close_retained",
            "bindings_list",
            "binding_drop",
            "binding_rename",
        }:
            from .management import execute_management

            return self._emit_output(execute_management(self, statement))
        if kind in {
            "file_open",
            "file_list",
            "file_info",
            "file_close",
            "file_refresh",
            "resource_status",
        }:
            from .file_commands import execute_file_command

            return self._emit_output(execute_file_command(self, statement))
        if kind == "batch_statement":
            from .batch_execution import execute_batch

            return execute_batch(self, statement, source)
        if kind in {"cursor_open", "cursor_continue", "cursor_restart", "cursor_close"}:
            from .cursors import render_cursor

            return self._emit_output(render_cursor(execute_cursor(self, statement)))
        if kind == "traverse":
            from .graph_options import render_graph

            return self._emit_output(render_graph(execute_traversal(self, statement)))
        if kind == "session_label":
            self.label = self._string(str(statement.children[2]))
            return ""
        if kind in {
            "session_start",
            "session_add",
            "session_match",
            "session_pause",
            "session_resume",
            "session_close",
        }:
            if getattr(self.client, "_query_session", None) is None:
                raise EvaluationError(
                    "interactive query session is unavailable; restart the console"
                )
            send = getattr(self.client, "send_session_command", None)
            if send is None:
                raise EvaluationError(
                    "interactive query session commands are unavailable"
                )
            value = (
                self._string(str(statement.children[2]))
                if len(statement.children) > 2
                else None
            )
            return send(
                kind.removeprefix("session_"),
                value,
                working_directory=self.cwd,
                compile_arguments=self.config_store.effective["extra_args"],
            )
        if kind == "history_save":
            if self.history is None:
                raise EvaluationError("history is not enabled")
            self.history.save(self.cwd / self._string(str(statement.children[2])))
            return ""
        if kind == "history_clear":
            if self.history is None:
                raise EvaluationError("history is not enabled")
            self.history.clear()
            return ""
        if kind == "set_command":
            self._set(statement)
            return ""
        if kind == "import_command":
            from .imports import execute_import

            return execute_import(self, statement)
        if kind in {"push_command", "delete_command", "set_item_command"}:
            self._collection_command(statement)
            return ""
        if kind == "split_command":
            value = self._split_values(
                self._evaluate(statement.children[1]),
                self._evaluate(statement.children[3]),
            )
            return self._emit_output(render(value))
        if kind == "clear_command":
            self._clear(statement)
            return ""
        if kind == "add_arg":
            args = list(self.config_store.effective["extra_args"])
            args.append(self._string(str(statement.children[2])))
            self.config_store.set("extra_args", args)
            return ""
        if kind == "save_command":
            value = self._evaluate(statement.children[1])
            path = self._output_path(statement.children[3])
            format_name = (
                str(statement.children[-1])
                if len(statement.children) > 5 and statement.children[-1] is not None
                else None
            )
            save(value, path, format_name=format_name)
            self._successful_exports += 1
            return ""
        if kind == "load_command":
            path = self._output_path(statement.children[1])
            target = statement.children[3]
            names = [
                str(item)
                for item in target.children
                if isinstance(item, Token) and item.type == "NAME"
            ]
            if len(names) != 1 or len(target.children) != 2:
                raise EvaluationError("load target must be a simple variable")
            value = load(path)
            scope = self._scopes[-1] if self._scopes else self.bindings
            scope[names[0]] = value
            return ""
        if kind == "assignment":
            self._assignment(statement)
            return ""
        if kind == "matcher_definition":
            self._define_matcher(statement)
            return ""
        if kind == "match":
            if self._match_block(statement) is not None:
                from .match_block import execute_match_block

                return execute_match_block(self, statement, source)
            return self._emit_output(
                render(self._execute_match(statement, source=source))
            )
        if kind == "background":
            matcher_node = statement.children[1]
            matcher = self._evaluate(matcher_node)
            if not isinstance(matcher, MatcherExpr):
                raise EvaluationError("background requires a matcher expression")
            if matcher.name in _KNOWN_NON_ROOT:
                raise EvaluationError(
                    f"{matcher.name} cannot be used as a top-level matcher"
                )
            expression = matcher_text(matcher)
            if (
                source is not None
                and isinstance(matcher_node, Tree)
                and not self._has_dynamic_part(matcher_node)
            ):
                expression = source[
                    matcher_node.meta.start_pos : matcher_node.meta.end_pos
                ]
            selected_files = None
            if len(statement.children) > 3 and statement.children[3] is not None:
                selected = self._evaluate(statement.children[3])
                if not isinstance(selected, list):
                    raise EvaluationError("background files must be a list of files")
                selected_files = []
                for entry in selected:
                    if isinstance(entry, File):
                        selected_files.append(entry.absolute)
                    elif isinstance(entry, str):
                        selected_files.append(str((self.cwd / entry).resolve()))
                    else:
                        raise EvaluationError(
                            "background files cannot include directories or other values"
                        )
            if selected_files is None and self.config_store.effective["files"]:
                selected_files = [
                    str((self.cwd / path).resolve())
                    for path in self.config_store.effective["files"]
                ]
            start = getattr(self.client, "start_background_query", None)
            if start is None:
                raise EvaluationError("background queries are unavailable")
            return start(
                expression,
                selected_files or (),
                working_directory=self.cwd,
                compile_arguments=self.config_store.effective["extra_args"],
            )
        if kind == "print":
            text = render(self._evaluate(statement.children[1]))
            if len(statement.children) > 3 and statement.children[3] is not None:
                destination = self._output_path(statement.children[3])
                append = any(
                    isinstance(item, Token) and item.type == "APPEND"
                    for item in statement.children
                )
                self.output.check_output(text)
                from .output import write_text

                write_text(destination, text, append=append)
                return ""
            return self._emit_output(text)
        if kind == "inspect":
            return self._emit_output(
                render_inspection(self._evaluate(statement.children[1]))
            )
        if kind == "display":
            expression = statement.children[0]
            if (
                isinstance(expression, Tree)
                and expression.data
                in {"foreach_expression", "foreach_statement_expression"}
                and self._is_foreach_statement_block(expression)
            ):
                return self._foreach(expression, source=source)
            return self._emit_output(render(self._evaluate(expression)))
        if kind == "cfg_file":
            from .control_flow import execute_cfg
            from .graph_options import render_graph

            return self._emit_output(render_graph(execute_cfg(self, statement, source)))
        if kind == "cfg":
            message = (
                'cfg requires a file: cfg FUNCTION in "file.cc"; see help cfg'
                if HAS_NATIVE_ANALYSIS_GRAMMAR
                else "cfg native execution is not implemented in this build; see help cfg"
            )
            raise EvaluationError(message)
        if kind == "script":
            from .scripting import execute_script

            return self._emit_output(execute_script(self, statement))
        if kind == "callgraph_file":
            from .call_graph import execute_call_graph
            from .graph_options import render_graph

            return self._emit_output(render_graph(execute_call_graph(self, statement)))
        if kind == "callgraph":
            message = (
                'callgraph requires a file: callgraph "file.cc"; see help callgraph'
                if HAS_NATIVE_ANALYSIS_GRAMMAR
                else "callgraph native execution is not implemented in this build; see help callgraph"
            )
            raise EvaluationError(message)
        raise EvaluationError(f"{kind} execution is not implemented yet")

    def completion_references(self) -> dict[str, tuple[str, ...]]:
        """Expose current variable names and typed fields to prompt_toolkit."""
        sources: dict[str, Any] = {
            "config": self.config_vars,
            "env": self.environment,
            **self.bindings,
        }
        fields: dict[str, tuple[str, ...]] = {}
        for name, value in sources.items():
            if isinstance(value, MatchValue):
                fields[name] = tuple(
                    sorted(value.binding_names() | {"length", "isEmpty"})
                )
            elif isinstance(value, MatchRow):
                fields[name] = tuple(value.bindings)
            elif isinstance(value, ParsedTree):
                fields[name] = ("path",)
            elif isinstance(value, list):
                fields[name] = field_names(value)
            elif type(value) is dict:
                fields[name] = field_names(value)
            elif isinstance(value, FileSystemEntry):
                fields[name] = (
                    "size",
                    "modified",
                    "basename",
                    "dirname",
                    "absolute",
                    "parts",
                )
            elif isinstance(value, Mapping):
                fields[name] = tuple(value)
            else:
                fields[name] = tuple(
                    field
                    for field in getattr(type(value), "__dataclass_fields__", {})
                    if not field.startswith("_")
                )
        return fields

    def completion_fields(self, reference: str) -> tuple[str, ...]:
        """Return local schema fields after resolving a complete reference."""
        return tuple(
            suggestion.name for suggestion in self.completion_suggestions(reference)
        )

    def completion_suggestions(self, reference: str) -> tuple[CompletionField, ...]:
        """Return local field names with runtime/schema-derived annotations."""
        try:
            from clang_toolkit.cli.language import reference_parser

            parsed = reference_parser().parse(reference).children[0]
            if not isinstance(parsed, Tree) or parsed.data != "reference":
                return ()
            value = self._reference(parsed)
            semantic_value = value
            if isinstance(value, BindingSelection):
                try:
                    semantic_value = property_value(value, "value")
                except (MatchValueError, ReferenceError):
                    semantic_value = None
            sources = (
                field_sources(semantic_value)
                if isinstance(semantic_value, MessageView)
                else {}
            )
            messages = {}
            results = []
            seen_dictionary_keys: set[str] = set()
            for name in field_names(value):
                source = (
                    None
                    if isinstance(value, BindingSelection)
                    and name
                    in {
                        "name",
                        "value",
                        "scope",
                        "source_file",
                        "decl_name",
                        "decl_type",
                        "parameter_name",
                        "record_name",
                        "type_name",
                        "location",
                        "range",
                        "symbol_identity",
                        "documentation",
                        "call_site",
                    }
                    else sources.get(name)
                )
                if source is not None:
                    owner, field = source
                    kind = "field"
                    oneof = field.containing_oneof
                    if id(owner) not in messages:
                        messages[id(owner)] = owner._message()
                    message = messages[id(owner)]
                    if (
                        oneof is not None
                        and len(oneof.fields) > 1
                        and message.WhichOneof(oneof.name) == name
                    ):
                        if field.message_type is not None:
                            meta = (
                                f"active payload · {field.message_type.name} · "
                                "continue with ."
                            )
                        else:
                            meta = "active field"
                            if field.enum_type is not None:
                                meta += f" · {field.enum_type.name}"
                    else:
                        value_type = field.message_type or field.enum_type
                        meta = (
                            f"field · {value_type.name}"
                            if value_type is not None
                            else "field"
                        )
                elif name in {"hasField", "fieldState", "fieldOr"} and (
                    is_semantic_view(value) or isinstance(value, BindingSelection)
                ):
                    kind = "method"
                    meta = "method · checks field presence or reports availability"
                elif isinstance(value, list) and name in {
                    "push",
                    "pop",
                    "insert",
                    "remove",
                    "clear",
                    "joinWith",
                    "unique",
                    "sort",
                    "filter",
                }:
                    kind = "method"
                    meta = f"method · {name} list values"
                elif (
                    type(value) is dict
                    and name in value
                    and name not in seen_dictionary_keys
                ):
                    kind = "property"
                    meta = "dictionary key"
                    seen_dictionary_keys.add(name)
                elif type(value) is dict and name in {
                    "get",
                    "set",
                    "delete",
                    "hasKey",
                    "clear",
                }:
                    kind = "method"
                    meta = f"method · {name} dictionary entries"
                elif name in {"joinWith", "unique", "sort", "filter"} and isinstance(
                    value, (list, MatchValue, NativeMatchCollection, MatchSet)
                ):
                    kind = "method"
                    meta = f"method · {name} values by a field selector"
                else:
                    kind = "property"
                    meta = "property"
                results.append(CompletionField(name, kind, meta))
            return tuple(results)
        except (
            ValueError,
            TypeError,
            IndexError,
            KeyError,
            MatchValueError,
            UnexpectedInput,
        ):
            return ()

    def completion_presence_fields(self, reference: str) -> tuple[str, ...]:
        """Offer local fields accepted by hasField, including inactive payloads."""
        try:
            from clang_toolkit.cli.language import reference_parser

            parsed = reference_parser().parse(reference).children[0]
            if not isinstance(parsed, Tree) or parsed.data != "reference":
                return ()
            value = self._reference(parsed)
            if not isinstance(value, MessageView):
                return ()
            return tuple(
                name
                for name, (_, field) in field_sources(
                    value, include_inactive=True
                ).items()
                if field.has_presence
            )
        except (
            ValueError,
            TypeError,
            IndexError,
            KeyError,
            MatchValueError,
            UnexpectedInput,
        ):
            return ()

    def close(self) -> None:
        self.bindings.clear()
        self._scopes.clear()
        self._default_targets.clear()
        self._block_owners.clear()
        self.output.close()

    def _emit_output(self, text: str) -> str:
        """Route display effects unless a command is being evaluated as a value."""
        if self._value_context_depth:
            # Keep the text available to enclosing command results, but do not
            # publish it through stdout or the configured output sink.
            return text
        return self.output.emit(text)

    def _assignment(self, statement: Tree) -> Any:
        name = str(statement.children[1])
        self._value_context_depth += 1
        try:
            value = self._evaluate(statement.children[3])
        finally:
            self._value_context_depth -= 1
        scope = self._scopes[-1] if self._scopes else self.bindings
        scope[name] = value
        return value

    def _bare_parts(self, node: Tree) -> tuple[str, list[tuple[str, Any]]]:
        if (
            node.data not in {"bare_value", "bare_access", "mutation_target"}
            or not node.children
        ):
            raise EvaluationError("expected a variable or collection reference")
        name = str(node.children[0])
        suffixes: list[tuple[str, Any]] = []
        index = 1
        while index < len(node.children):
            token = node.children[index]
            if isinstance(token, Token) and token.type == "DOT":
                suffixes.append(("property", str(node.children[index + 1])))
                index += 2
            elif isinstance(token, Token) and token.type == "LSQB":
                suffixes.append(("index", self._evaluate(node.children[index + 1])))
                index += 3
            else:
                raise EvaluationError("invalid variable reference")
        return name, suffixes

    def _collection_parts(self, node: Tree) -> tuple[str, list[tuple[str, Any]]]:
        if node.data != "reference":
            return self._bare_parts(node)
        if len(node.children) < 2:
            raise EvaluationError("expected a variable or collection reference")
        name = str(node.children[1])
        suffixes: list[tuple[str, Any]] = []
        index = 2
        while index < len(node.children):
            token = node.children[index]
            if isinstance(token, Token) and token.type == "LSQB":
                suffixes.append(("index", self._evaluate(node.children[index + 1])))
                index += 3
            elif isinstance(token, Token) and token.type == "DOT":
                member = node.children[index + 1]
                if isinstance(member, Tree):
                    raise EvaluationError(
                        "collection operations cannot target a method result"
                    )
                suffixes.append(("property", str(member)))
                index += 2
            else:
                raise EvaluationError("invalid collection reference")
        return name, suffixes

    def _resolve_bare(self, node: Tree) -> Any:
        name, suffixes = self._bare_parts(node)
        value = self._resolve_name(name)
        for operation, key in suffixes:
            try:
                value = (
                    index_value(value, key)
                    if operation == "index"
                    else property_value(value, key)
                )
            except (ReferenceError, MatchValueError, IndexError, KeyError) as error:
                raise EvaluationError(str(error)) from error
        return value

    def _resolve_collection_ref(self, node: Tree) -> Any:
        return (
            self._reference(node)
            if node.data == "reference"
            else self._resolve_bare(node)
        )

    def _bare_mutation_target(self, node: Tree) -> tuple[Any, Any]:
        name, suffixes = self._collection_parts(node)
        if not suffixes or suffixes[-1][0] != "index":
            raise EvaluationError(
                "collection item operation requires a final [key] or [index]"
            )
        value = self._resolve_name(name)
        for operation, key in suffixes[:-1]:
            try:
                value = (
                    index_value(value, key)
                    if operation == "index"
                    else property_value(value, key)
                )
            except (ReferenceError, MatchValueError, IndexError, KeyError) as error:
                raise EvaluationError(str(error)) from error
        return value, suffixes[-1][1]

    def _collection_command(self, statement: Tree) -> None:
        kind = str(statement.data)
        if kind == "push_command":
            target = self._resolve_collection_ref(statement.children[1])
            value = self._evaluate(statement.children[-1])
            self._reject_live_batch_collection_value(value)
            try:
                call_method(target, "push", [value])
            except ReferenceError as error:
                raise EvaluationError(str(error)) from error
            return
        if kind == "set_item_command":
            target, key = self._bare_mutation_target(statement.children[1])
            value = self._evaluate(statement.children[-1])
            self._reject_live_batch_collection_value(value)
            from .collections import ensure_insertable, mutable_index_target

            try:
                mutable_index_target(target, key)
                ensure_insertable(target, value)
                if type(target) is list and key >= len(target):
                    raise ReferenceError("list assignment index is out of range")
                target[key] = value
            except ReferenceError as error:
                raise EvaluationError(str(error)) from error
            return
        if kind == "delete_command":
            target, key = self._bare_mutation_target(statement.children[1])
            from .collections import mutable_index_target

            try:
                mutable_index_target(target, key)
                if type(target) is list:
                    if key >= len(target):
                        raise ReferenceError("list index is out of range")
                    del target[key]
                else:
                    if key not in target:
                        raise ReferenceError(f"dictionary key not found: {key}")
                    del target[key]
            except ReferenceError as error:
                raise EvaluationError(str(error)) from error

    def _split_values(self, value: Any, separator: Any) -> list[str]:
        if not isinstance(value, str) or not isinstance(separator, str):
            raise EvaluationError("split requires a string and a string separator")
        if not separator:
            raise EvaluationError("split separator cannot be empty")
        return value.split(separator)

    @staticmethod
    def _flatten_members(value: Any) -> Any | None:
        """Return a one-level collection iterator, excluding record/scalar values."""
        if type(value) in (list, tuple):
            return iter(value)
        if isinstance(value, MatchSet):
            return iter(value.rows)
        if isinstance(value, MatchValue):
            return value.iter_rows()
        if isinstance(value, NativeMatchCollection | NativeBindingCollection):
            return iter(value)
        from .semantic import RepeatedView

        if isinstance(value, RepeatedView):
            return iter(value)
        return None

    def _flatten_collection(self, value: Any) -> list[Any]:
        outer = self._flatten_members(value)
        if outer is None:
            raise EvaluationError(
                "flatten requires a list or query-result collection; "
                f"got {type(value).__name__}"
            )

        result: list[Any] = []
        for index, child in enumerate(outer):
            members = self._flatten_members(child)
            if members is None:
                if isinstance(child, str):
                    reason = "strings are scalar values, not collections"
                elif isinstance(child, Mapping):
                    reason = "dictionaries are records, not collections"
                else:
                    reason = f"{type(child).__name__} is not a supported collection"
                raise EvaluationError(
                    f"flatten child at index {index} is invalid: {reason}; "
                    "expected a list or query-result collection"
                )
            for member in members:
                if len(result) >= MAX_CONSOLE_COLLECTION_ITEMS:
                    raise EvaluationError(
                        f"flatten result exceeds {MAX_CONSOLE_COLLECTION_ITEMS} items"
                    )
                result.append(member)
        return result

    def _define_matcher(self, statement: Tree) -> MatcherFunction:
        name = str(statement.children[1])
        if name in set(ROOT_MATCHERS) | set(NESTED_MATCHERS):
            raise EvaluationError(f"{name} is a built-in matcher name")
        parameter_node = next(
            (
                child
                for child in statement.children
                if isinstance(child, Tree) and child.data == "parameters"
            ),
            None,
        )
        parameters = (
            tuple(
                str(child)
                for child in parameter_node.children
                if isinstance(child, Token) and child.type == "NAME"
            )
            if parameter_node
            else ()
        )
        if len(set(parameters)) != len(parameters):
            raise EvaluationError(f"{name} has duplicate parameter names")
        scope = self._scopes[-1] if self._scopes else self.bindings
        value = MatcherFunction(name, parameters, statement.children[-1])
        scope[name] = value
        return value

    def _matcher_function(self, name: str) -> MatcherFunction | None:
        for scope in reversed(self._scopes):
            if name in scope:
                value = scope[name]
                return value if isinstance(value, MatcherFunction) else None
        value = self.bindings.get(name)
        return value if isinstance(value, MatcherFunction) else None

    def matcher_function_names(self) -> tuple[str, ...]:
        values = dict(self.bindings)
        for scope in self._scopes:
            values.update(scope)
        return tuple(
            name for name, value in values.items() if isinstance(value, MatcherFunction)
        )

    def _set(self, statement: Tree) -> None:
        scope = (
            "user"
            if any(
                isinstance(item, Token) and item.type == "USER"
                for item in statement.children
            )
            else "project"
        )
        setting = next(item for item in statement.children if isinstance(item, Tree))
        kind = str(setting.data)
        if kind == "traversal_setting":
            key, value = "traversal", str(setting.children[1])
        elif kind == "compilation_database_setting":
            key, value = "compile_commands", self._string(str(setting.children[1]))
        elif kind == "args_setting":
            key, value = "extra_args", self._evaluate(setting.children[1])
        elif kind == "cache_setting":
            key, value = "cache_dir", self._string(str(setting.children[2]))
        elif kind == "files_setting":
            key, selected = "files", self._evaluate(setting.children[2])
            if not isinstance(selected, list):
                raise EvaluationError("files setting requires a list of files")
            value = []
            for entry in selected:
                if isinstance(entry, Directory):
                    raise EvaluationError("files setting cannot include directories")
                if isinstance(entry, File):
                    value.append(entry.path)
                elif isinstance(entry, str):
                    value.append(entry)
                else:
                    raise EvaluationError("files setting requires file paths")
        elif kind == "output_setting":
            key = "output"
            target = setting.children[2]
            value = (
                "stdout"
                if isinstance(target, Token) and target.type == "STDOUT"
                else str(self._output_path(target))
            )
            old = self.output.destination
            replace = any(
                isinstance(item, Token) and item.type == "REPLACE"
                for item in setting.children
            )
            if replace and value == "stdout":
                raise EvaluationError("replace mode requires a file destination")
            self.output.configure(value, replace=replace)
            try:
                self.config_store.set(key, value, scope=scope)
            except ConfigError:
                self.output.configure(old)
                raise
            return
        else:
            raise EvaluationError(f"unsupported setting: {kind}")
        self.config_store.set(key, value, scope=scope)

    def _clear(self, statement: Tree) -> None:
        scope = (
            "user"
            if any(
                isinstance(item, Token) and item.type == "USER"
                for item in statement.children
            )
            else "project"
        )
        key = str(statement.children[-1])
        self.config_store.clear(key, scope=scope)
        if key == "output":
            self.output.configure(self.config_store.effective["output"])

    def _evaluate(self, node: Any) -> Any:
        if isinstance(node, Token):
            if node.type in {
                "STRING",
                "FILE_STRING",
                "DIRECTORY_STRING",
                "PATH_STRING",
            }:
                return self._string(str(node))
            if node.type in {"NUMBER", "NEGATIVE_NUMBER"}:
                raw = str(node)
                return float(raw) if any(char in raw for char in ".eE") else int(raw)
            raise EvaluationError(f"unexpected {node.type} token")
        if not isinstance(node, Tree):
            raise EvaluationError("incomplete expression")
        kind = str(node.data)
        if kind in _COMMAND_VALUE_KINDS | _COLLECTION_VALUE_KINDS:
            source = self._source_stack[-1] if self._source_stack else ""
            return self._evaluate_command_statement(
                node, source, value_context=True
            )[0]
        if kind == "true":
            return True
        if kind == "false":
            return False
        if kind == "reference":
            return self._reference(node)
        if kind == "bare_value":
            return self._resolve_bare(node)
        if kind == "bare_access":
            return self._resolve_bare(node)
        if kind == "named_value":
            return self._resolve_name(str(node.children[0]))
        if kind == "matcher":
            name = str(node.children[0])
            args: list[Any] = []
            binding: str | None = None
            for child in node.children[1:]:
                if isinstance(child, Tree) and child.data == "bind":
                    binding = self._string(str(child.children[2]))
                elif isinstance(child, Tree) and child.data == "arguments":
                    args.extend(
                        self._evaluate(item)
                        for item in child.children
                        if not self._punctuation(item)
                    )
                elif not self._punctuation(child) and child is not None:
                    args.append(self._evaluate(child))
            function = self._matcher_function(name)
            if function is not None:
                value = function.call(self, args)
                return replace(value, binding=binding) if binding is not None else value
            return MatcherExpr(name, tuple(args), binding)
        if kind == "nested_qualified_name":
            return QualifiedName("".join(map(str, node.children)))
        if kind == "list_value":
            return [
                self._evaluate(item)
                for item in node.children
                if not self._punctuation(item) and item is not None
            ]
        if kind == "dict_value":
            result: dict[str, Any] = {}
            for entry in node.children:
                if not isinstance(entry, Tree) or entry.data != "dict_entry":
                    continue
                key_token = entry.children[0]
                key = (
                    self._string(str(key_token))
                    if isinstance(key_token, Token) and key_token.type == "STRING"
                    else str(key_token)
                )
                if key in result:
                    raise EvaluationError(f"duplicate dictionary key: {key}")
                result[key] = self._evaluate(entry.children[2])
            return result
        if kind == "pop_expression":
            target = self._resolve_collection_ref(node.children[1])
            try:
                return call_method(target, "pop", [])
            except ReferenceError as error:
                raise EvaluationError(str(error)) from error
        if kind == "split_expression":
            return self._split_values(
                self._evaluate(node.children[1]), self._evaluate(node.children[3])
            )
        if kind == "join_expression":
            values = self._resolve_collection_ref(node.children[1])
            separator = self._evaluate(node.children[3])
            if not isinstance(values, list) or not isinstance(separator, str):
                raise EvaluationError("join requires a list and a string separator")
            return separator.join(render(item) for item in values)
        if kind == "flatten_expression":
            return self._flatten_collection(self._evaluate(node.children[2]))
        if kind == "grouped_expression":
            return self._grouped_expression(node)
        if kind == "glob_call":
            pattern = self._string(str(node.children[2]))
            if Path(pattern).is_absolute():
                raise EvaluationError(
                    "glob patterns must be relative to the session directory"
                )
            paths = sorted(self.cwd.glob(pattern))
            if len(paths) > 10_000:
                raise EvaluationError("glob result exceeds 10000 entries")
            return [
                entry
                for path in paths
                if (entry := from_path(path, self.cwd)) is not None
            ]
        if kind == "files_expression":
            from .file_commands import discover_files

            return discover_files(self, node)
        if kind == "match_expression":
            return self._execute_match(node)
        if kind == "parse_expression":
            target = self._evaluate(node.children[1])
            if isinstance(target, File):
                target = target.absolute
            if not isinstance(target, str):
                raise EvaluationError("parse requires a file path")
            return self._track_native_value(
                self._scoped_file_call(
                    target,
                    lambda: self.client.parse(
                        target,
                        working_directory=self.cwd,
                        compile_arguments=self.config_store.effective["extra_args"],
                        **(
                            {"scope": self._active_resource_scope}
                            if self._active_resource_scope is not None
                            else {}
                        ),
                    ),
                )
            )
        if kind == "read_expression":
            return read_document(self._output_path(node.children[1]))
        if kind == "analysis_block":
            return self._analysis_block(node)
        if kind == "traverse_expression":
            from .traversal import execute_traversal

            return execute_traversal(self, node)
        if kind == "call_graph_expression":
            from .call_graph import execute_call_graph

            return execute_call_graph(self, node)
        if kind == "cfg_file_expression":
            from .control_flow import execute_cfg

            return execute_cfg(self, node, "")
        if kind in {"foreach_expression", "foreach_statement_expression"}:
            return self._foreach(node)
        raise EvaluationError(f"unsupported expression: {kind}")

    def _grouped_expression(self, node: Tree) -> Any:
        value = self._evaluate(node.children[1])
        for suffix in node.children[3:]:
            if not isinstance(suffix, Tree):
                continue
            try:
                if suffix.data == "grouped_property":
                    value = property_value(value, str(suffix.children[1]))
                elif suffix.data == "grouped_index":
                    key = self._evaluate(suffix.children[1])
                    value = index_value(value, key)
                elif suffix.data == "grouped_method":
                    call = suffix.children[1]
                    name, arguments = self._method_call_parts(call)
                    if name in {"push", "insert", "set"}:
                        for argument in arguments:
                            self._reject_live_batch_collection_value(
                                self._evaluate(argument)
                            )
                    value = call_method(
                        value, name, [self._evaluate(arg) for arg in arguments]
                    )
            except (ReferenceError, MatchValueError, IndexError, KeyError) as error:
                raise EvaluationError(f"{error} in grouped expression") from error
        return value

    def _reject_live_batch_collection_value(self, value: Any) -> None:
        if self._active_resource_scope is None:
            return
        if _contains_live_native_value(value):
            raise EvaluationError(
                "batch-owned live resources cannot be stored in collections; "
                "save or summarize them instead"
            )

    def _method_call_parts(self, call: Tree) -> tuple[str, list[Any]]:
        if call.data == "generic_method_call":
            method_token = call.children[0].children[0]
            arguments_node = call.children[2]
            arguments = (
                [
                    item
                    for item in arguments_node.children
                    if not self._punctuation(item)
                ]
                if isinstance(arguments_node, Tree)
                else []
            )
        else:
            method_token = call.children[0]
            if call.data == "field_or_call":
                arguments = [call.children[2], call.children[4]]
            else:
                arguments = [call.children[2]]
        return str(method_token), arguments

    def _analysis_block(self, node: Tree) -> Any:
        target = self._evaluate(node.children[1])
        if not isinstance(target, ParsedTree):
            raise EvaluationError("analysis block requires a parsed tree")
        scope: dict[str, Any] = {}
        owners: set[Any] = set()
        if (
            isinstance(node.children[1], Tree)
            and node.children[1].data == "parse_expression"
        ):
            owners.add(target._owner)
        self._scopes.append(scope)
        self._default_targets.append(target)
        self._block_owners.append(owners)
        surviving: set[Any] = set()
        try:
            for child in node.children[3:]:
                if isinstance(child, Tree) and child.data == "assignment":
                    self._assignment(child)
                elif isinstance(child, Token) and child.type == "YIELD":
                    index = node.children.index(child)
                    value = self._evaluate(node.children[index + 1])
                    surviving = self._native_owners(value)
                    return value
            raise EvaluationError("analysis block requires a terminal yield")
        finally:
            self._default_targets.pop()
            self._scopes.pop()
            self._block_owners.pop()
            scope.clear()
            for owner in owners - surviving:
                owner.close()

    def _track_native_value(self, value: Any) -> Any:
        if isinstance(value, NativeMatchCollection):
            for match in value.matches:
                for owners in self._block_owners:
                    owners.add(match._owner)
        elif isinstance(value, NativeBindingCollection):
            for selection in value.selections:
                if selection is None:
                    continue
                for owners in self._block_owners:
                    owners.add(selection._owner)
            for match in value.matches:
                for owners in self._block_owners:
                    owners.add(match._owner)
        elif isinstance(value, ParsedTree | MatchValue | MatchRow | BindingSelection):
            for owners in self._block_owners:
                owners.add(value._owner)
        return value

    @staticmethod
    def _native_owners(value: Any) -> set[Any]:
        if isinstance(value, ParsedTree | MatchValue | MatchRow | BindingSelection):
            return {value._owner}
        if isinstance(value, NativeMatchCollection):
            return set().union(
                *(Runtime._native_owners(item) for item in value.matches)
            )
        if isinstance(value, NativeBindingCollection):
            return set().union(
                *(
                    Runtime._native_owners(item)
                    for item in value.selections
                    if item is not None
                ),
                *(Runtime._native_owners(item) for item in value.matches),
            )
        if isinstance(value, list | tuple):
            return set().union(*(Runtime._native_owners(item) for item in value))
        if isinstance(value, Mapping):
            return set().union(
                *(Runtime._native_owners(item) for item in value.values())
            )
        return set()

    @staticmethod
    def _punctuation(node: Any) -> bool:
        return isinstance(node, Token) and node.type in _PUNCTUATION

    @staticmethod
    def _output_size_hint(value: Any, limit: int = 1_000_001) -> int:
        """Estimate retained output without formatting or consuming a view."""
        if limit <= 0:
            return limit
        if isinstance(value, str):
            return min(len(value.encode("utf-8")), limit)
        if isinstance(value, bytes):
            return min(len(value), limit)
        if isinstance(value, list | tuple):
            size = 0
            for item in value:
                size += Runtime._output_size_hint(item, limit - size)
                if size >= limit:
                    break
            return size
        if isinstance(value, Mapping):
            size = 0
            for key, item in value.items():
                size += len(str(key).encode("utf-8"))
                size += Runtime._output_size_hint(item, limit - size)
                if size >= limit:
                    break
            return size
        data = getattr(value, "_data", None)
        if isinstance(data, bytes):
            return min(len(data), limit)
        return min(len(render(value).encode("utf-8")), limit)

    def _reference(self, node: Tree) -> Any:
        children = node.children
        name = str(children[1])
        steps: list[tuple[str, Any, Any | None, str, int, int]] = []
        index = 2
        while index < len(children):
            if isinstance(children[index], Token) and children[index].type == "LSQB":
                expression = children[index + 1]
                key = self._evaluate(expression)
                line = (
                    expression.meta.line
                    if isinstance(expression, Tree)
                    else expression.line
                )
                column = (
                    expression.meta.column
                    if isinstance(expression, Tree)
                    else expression.column
                )
                segment = (
                    f"[{expression}]" if isinstance(expression, Token) else "[index]"
                )
                steps.append(("index", key, None, segment, line, column))
                index += 3
                continue
            token = children[index + 1]
            method_call = token if isinstance(token, Tree) else None
            if method_call is not None and method_call.data in {
                "has_field_call",
                "field_state_call",
                "field_or_call",
                "generic_method_call",
            }:
                if method_call.data == "generic_method_call":
                    method_token = method_call.children[0].children[0]
                    arguments_node = method_call.children[2]
                    arguments = (
                        [
                            item
                            for item in arguments_node.children
                            if not self._punctuation(item)
                        ]
                        if isinstance(arguments_node, Tree)
                        else []
                    )
                else:
                    method_token = method_call.children[0]
                    if method_call.data == "field_or_call":
                        arguments = [method_call.children[2], method_call.children[4]]
                    else:
                        arguments = [method_call.children[2]]
                method = str(method_token)
                steps.append(
                    (
                        "method",
                        method,
                        arguments,
                        f".{method}(...)",
                        method_token.line,
                        method_token.column,
                    )
                )
                index += 2
            else:
                steps.append(
                    (
                        "property",
                        str(token),
                        None,
                        f".{token}",
                        token.line,
                        token.column,
                    )
                )
                index += 2

        local_name = any(name in scope for scope in self._scopes)
        if (
            name in {"env", "config"}
            and not local_name
            and steps
            and steps[0][0] == "property"
        ):
            key = steps.pop(0)[1]
            source = self.environment if name == "env" else self.config_vars
            if key not in source:
                raise EvaluationError(f"unknown {name} variable: {key}")
            value: Any = source[key]
        else:
            value = self._resolve_name(name)
        row_context: int | None = None
        for operation, field, argument, segment, line, column in steps:
            previous = value
            try:
                if operation == "method":
                    value = call_method(
                        value,
                        field,
                        [self._evaluate(argument) for argument in argument],
                    )
                elif operation == "index":
                    value = index_value(value, field)
                else:
                    value = property_value(value, field)
                if (
                    operation == "index"
                    and isinstance(previous, MatchValue)
                    and type(field) is int
                ):
                    row_context = field
            except (ReferenceError, MatchValueError, IndexError, KeyError) as exc:
                row = f" in row {row_context}" if row_context is not None else ""
                raise EvaluationError(
                    f"{exc}{row} at {segment} (line {line}, column {column})"
                ) from exc
        return value

    def _resolve_name(self, name: str) -> Any:
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        if name in self.bindings:
            return self.bindings[name]
        if name in self.environment:
            return self.environment[name]
        if name in self.config_vars:
            return self.config_vars[name]
        raise EvaluationError(f"unknown variable: {name}")

    def _output_path(self, node: Any) -> Path:
        value = self._evaluate(node)
        if isinstance(value, FileSystemEntry):
            value = value.absolute
        if not isinstance(value, str) or not value:
            raise EvaluationError("file destination must be a nonempty path string")
        if value == "~" or value.startswith("~/"):
            home = self.environment.get("HOME")
            if not home:
                raise EvaluationError("HOME is required to expand ~ in a file path")
            value = home + value[1:]
        return self.cwd / value

    def _string(self, raw: str) -> str:
        try:
            return evaluate_string(raw, self._evaluate)
        except TemplateError as exc:
            raise EvaluationError(str(exc)) from exc

    def _execute_match(
        self,
        node: Tree,
        *,
        source: str | None = None,
        on_row: Callable[[Any, Any], None] | None = None,
    ) -> MatchSet | MatchValue | NativeMatchCollection:
        matcher_node = node.children[1]
        matcher = self._evaluate(matcher_node)
        if not isinstance(matcher, MatcherExpr):
            raise EvaluationError("match requires a matcher expression")
        if matcher.name in _KNOWN_NON_ROOT:
            raise EvaluationError(
                f"{matcher.name} cannot be used as a top-level matcher"
            )
        files: list[Any] | None = None
        target: Any = self._default_targets[-1] if self._default_targets else None
        if len(node.children) > 3 and node.children[3] is not None:
            selected = self._evaluate(node.children[3])
            if isinstance(selected, str | Directory):
                path = (
                    selected.absolute if isinstance(selected, Directory) else selected
                )
                files = self._match_paths(path)
                target = None if files is not None else path
            elif isinstance(
                selected,
                File
                | ParsedTree
                | MatchValue
                | BindingSelection
                | NativeMatchCollection
                | NativeBindingCollection,
            ):
                target = selected.absolute if isinstance(selected, File) else selected
            elif isinstance(selected, InputDescriptor | FileHandle):
                target = selected
            elif isinstance(selected, FileBatch):
                target = None
                files = list(selected.inputs)
            elif isinstance(selected, FileSet):
                target = None
                files = list(selected.inputs)
            elif isinstance(selected, list):
                target = None
                files = []
                for entry in selected:
                    if isinstance(entry, File):
                        files.append(entry.absolute)
                    elif isinstance(entry, str):
                        files.append(str((self.cwd / entry).resolve()))
                    elif isinstance(entry, InputDescriptor | FileHandle):
                        files.append(entry)
                    else:
                        raise EvaluationError(
                            "match files cannot include directories or other values"
                        )
            elif isinstance(selected, tuple) and all(
                isinstance(entry, InputDescriptor | FileHandle) for entry in selected
            ):
                target = None
                files = list(selected)
            else:
                raise EvaluationError(
                    "match target must be a file list, path, directory, glob, tree or binding selection"
                )
        try:
            text = matcher_text(matcher)
        except TypeError as exc:
            raise EvaluationError(str(exc)) from exc
        if source is not None and isinstance(matcher_node, Tree):
            original = source[matcher_node.meta.start_pos : matcher_node.meta.end_pos]
            if original and not self._has_dynamic_part(matcher_node):
                text = original
        if target is not None:
            traversal = self.config_store.effective["traversal"]
            from clang_toolkit._generated.match.v1 import match_service_pb2 as pb

            traversal_mode = (
                pb.MATCH_TRAVERSAL_MODE_IGNORE_UNLESS_SPELLED_IN_SOURCE
                if traversal
                in {"ignore_unless_spelled_in_source", "IgnoreUnlessSpelledInSource"}
                else pb.MATCH_TRAVERSAL_MODE_AS_IS
            )
            options = {
                "working_directory": self.cwd,
                "compile_arguments": self.config_store.effective["extra_args"],
                "traversal_mode": traversal_mode,
            }
            if self._active_resource_scope is not None:
                options["scope"] = self._active_resource_scope
            if isinstance(target, NativeMatchCollection | NativeBindingCollection):
                if isinstance(target, NativeMatchCollection):
                    sources = target.matches
                    files_for_sources = target.files
                else:
                    source_pairs = [
                        (selection, path)
                        for selection, path in zip(
                            target.selections, target.files, strict=True
                        )
                        if selection is not None
                    ]
                    sources = tuple(selection for selection, _ in source_pairs)
                    files_for_sources = tuple(path for _, path in source_pairs)
                max_files = self._match_setting("max_files", 100)
                if len(sources) > max_files:
                    raise EvaluationError(
                        f"match aggregate exceeds configured file limit of {max_files}"
                    )
                matches = self._match_files(text, sources, on_row=on_row, **options)
                return self._track_native_value(
                    NativeMatchCollection(
                        tuple(matches),
                        tuple(_source_file_path(path) for path in files_for_sources),
                    )
                )
            return self._track_native_value(
                self._match_target(text, target, options, on_row)
            )
        if files is None and target is None and self._active_resource_scope is not None:
            files = list(self._active_batch_inputs or ())
        if files is None and self.config_store.effective["files"]:
            files = [
                str((self.cwd / path).resolve())
                for path in self.config_store.effective["files"]
            ]
        if files is None:
            if on_row is not None:
                raise EvaluationError(
                    "match do requires a target, configured files, or an enclosing parsed tree"
                )
            rows = self.client.match(
                text,
                files=None,
                working_directory=self.cwd,
                compile_arguments=self.config_store.effective["extra_args"],
            )
            return MatchSet(tuple(rows))
        max_files = self._match_setting("max_files", 100)
        if len(files) > max_files:
            raise EvaluationError(
                f"match file list exceeds configured limit of {max_files}"
            )
        from clang_toolkit._generated.match.v1 import match_service_pb2 as pb

        traversal_mode = (
            pb.MATCH_TRAVERSAL_MODE_IGNORE_UNLESS_SPELLED_IN_SOURCE
            if self.config_store.effective["traversal"]
            in {"ignore_unless_spelled_in_source", "IgnoreUnlessSpelledInSource"}
            else pb.MATCH_TRAVERSAL_MODE_AS_IS
        )
        if self._active_resource_scope is not None:
            traversal_scope = self._active_resource_scope
        else:
            traversal_scope = None
        matches = self._match_files(
            text,
            files,
            on_row=on_row,
            working_directory=self.cwd,
            compile_arguments=self.config_store.effective["extra_args"],
            traversal_mode=traversal_mode,
            **({"scope": traversal_scope} if traversal_scope is not None else {}),
        )
        return self._track_native_value(
            NativeMatchCollection(
                tuple(matches), tuple(_source_file_path(path) for path in files)
            )
        )

    def _scoped_file_call(self, target: Any, operation: Callable[[], Any]) -> Any:
        """Run one file operation and record its per-input terminal outcome."""
        if self._active_resource_scope is None:
            return operation()
        key = self._batch_input_key(target)
        unknown_key = None if key is not None else str(getattr(target, "path", target))
        with self._batch_outcome_lock:
            if key is not None:
                self._batch_file_outcomes[key] = "attempting"
            elif unknown_key is not None:
                self._batch_unknown_file_outcomes.add(unknown_key)
        try:
            result = operation()
        except KeyboardInterrupt:
            self._finish_batch_file_outcome(key, "cancelled")
            raise
        except (CursorError, AnalysisError) as error:
            if error.code == grpc.StatusCode.CANCELLED:
                outcome = "cancelled"
            elif error.code in {
                grpc.StatusCode.UNAVAILABLE,
                grpc.StatusCode.DEADLINE_EXCEEDED,
                grpc.StatusCode.UNKNOWN,
            } or is_receive_size_rejection(error):
                outcome = "unknown"
            else:
                outcome = "failed"
            self._finish_batch_file_outcome(key, outcome)
            raise
        except BaseException:
            self._finish_batch_file_outcome(key, "failed")
            raise
        self._finish_batch_file_outcome(key, "completed")
        return result

    def _batch_input_key(self, target: Any) -> tuple[str, str] | None:
        if isinstance(target, FileHandle):
            target = target.input
        elif isinstance(target, ParsedTree):
            target = target.path
        elif isinstance(target, File):
            target = target.absolute
        target_path = (
            target.path if isinstance(target, InputDescriptor) else str(target)
        )
        profile_id = target.profile_id if isinstance(target, InputDescriptor) else ""
        if self._active_batch_inputs is None:
            return None
        normalized_target = os.path.normpath(target_path)
        for descriptor in self._active_batch_inputs:
            key = (descriptor.path, descriptor.profile_id)
            if (
                key == (target_path, profile_id)
                or os.path.normpath(descriptor.path) == normalized_target
            ):
                return key
            if not os.path.isabs(target_path) and descriptor.working_directory:
                joined = os.path.normpath(
                    os.path.join(descriptor.working_directory, target_path)
                )
                if os.path.normpath(descriptor.path) == joined:
                    return key
        return None

    def _finish_batch_file_outcome(
        self, key: tuple[str, str] | None, outcome: str
    ) -> None:
        if key is None:
            return
        with self._batch_outcome_lock:
            self._batch_file_outcomes[key] = outcome

    def _match_files(
        self,
        text: str,
        targets: list[Any] | tuple[Any, ...],
        on_row: Callable[[Any, Any], None] | None = None,
        **options: Any,
    ) -> list[MatchValue]:
        if len(targets) < 2:
            return [
                self._match_target(text, target, options, on_row) for target in targets
            ]
        workers = self._batch_jobs or self._match_setting("pool_size", 4) or 4
        futures = []
        try:
            with ThreadPoolExecutor(max_workers=min(workers, len(targets))) as pool:
                try:
                    for target in targets:
                        futures.append(
                            pool.submit(
                                self._match_target, text, target, options, on_row
                            )
                        )
                    return [future.result() for future in futures]
                except BaseException:
                    for future in futures:
                        future.cancel()
                    raise
        except BaseException:
            # The pool has joined: also release successful results completed
            # after an earlier file failed, without publishing a partial value.
            for future in futures:
                if not future.cancelled():
                    try:
                        future.result()._owner.close()
                    except BaseException:
                        pass
            raise

    def _match_target(
        self,
        text: str,
        target: Any,
        options: dict[str, Any],
        on_row: Callable[[Any, Any], None] | None,
    ) -> MatchValue:
        if on_row is None:
            return self._scoped_file_call(
                target, lambda: self.client.match_in(text, target, **options)
            )
        return self._scoped_file_call(
            target,
            lambda: self.client.match_in(
                text, target, **options, on_row=lambda row: on_row(row, target)
            ),
        )

    @staticmethod
    def _match_block(node: Tree) -> Tree | None:
        return next(
            (
                child
                for child in node.children
                if isinstance(child, Tree) and child.data == "statement_block"
            ),
            None,
        )

    @staticmethod
    def _is_foreach_statement_block(node: Tree) -> bool:
        body = node.children[5]
        if isinstance(body, Tree) and body.data in {
            "foreach_statement_block",
            "foreach_empty_block",
        }:
            return True
        if (
            node.data != "foreach_statement_expression"
            or not isinstance(body, Tree)
            or body.data != "dict_value"
        ):
            return False
        has_entries = any(
            isinstance(child, Tree) and child.data == "dict_entry"
            for child in body.children
        )
        has_done = any(
            isinstance(child, Token) and child.type in {"DONE", "DONE_AFTER_NEWLINE"}
            for child in node.children
        )
        return not has_entries and not has_done

    def _match_paths(self, target: str) -> list[str] | None:
        """Expand local directories/globs; leave literal file paths unchanged."""
        path = self.cwd / target
        if path.is_file():
            return None
        if path.is_dir():
            candidates = (
                item for item in path.rglob("*") if item.suffix in _SOURCE_SUFFIXES
            )
        elif has_magic(target):
            candidates = (Path(item) for item in iglob(str(path), recursive=True))
        else:
            return None
        max_files = self._match_setting("max_files", 100)
        files: set[str] = set()
        for item in candidates:
            if item.is_file():
                files.add(str(item.resolve()))
                if len(files) > max_files:
                    raise EvaluationError(
                        f"match file list exceeds configured limit of {max_files}"
                    )
        return sorted(files)

    def _match_setting(self, name: str, default: int) -> int:
        owner = getattr(self.client, "client", self.client)
        configure = getattr(owner, "_configuration", None)
        config = configure() if configure else getattr(owner, "config", None)
        value = getattr(config, name, default)
        return value if type(value) is int and value >= 0 else default

    def _has_dynamic_part(self, node: Tree) -> bool:
        if node.data == "reference":
            return True
        if (
            node.data == "matcher"
            and self._matcher_function(str(node.children[0])) is not None
        ):
            return True
        return any(
            (
                isinstance(child, Tree)
                and (child.data == "reference" or self._has_dynamic_part(child))
            )
            or (
                isinstance(child, Token)
                and child.type == "STRING"
                and str(child).startswith('"')
                and "$" in str(child)
            )
            for child in node.children
        )

    def _foreach(
        self,
        node: Tree,
        *,
        source: str | None = None,
        value_context: bool | None = None,
    ) -> list[Any] | str | None:
        if source is None:
            source = self._source_stack[-1] if self._source_stack else ""
        if value_context is None:
            value_context = self._value_context_depth > 0
        declaration_form = node.data == "foreach_statement_expression"
        iterator = node.children[1]
        if declaration_form:
            if not isinstance(iterator, Token) or iterator.type != "NAME":
                raise EvaluationError("foreach iterator must be a variable name")
            name = str(iterator)
            items_node = node.children[3]
            body = node.children[5]
        else:
            if not isinstance(iterator, Tree) or iterator.data != "reference":
                raise EvaluationError("foreach iterator must be a variable")
            names = [
                str(item)
                for item in iterator.children
                if isinstance(item, Token) and item.type == "NAME"
            ]
            if len(names) != 1 or len(iterator.children) != 2:
                raise EvaluationError("foreach iterator cannot use a field")
            name = names[0]
            items_node = node.children[3]
            body = node.children[5]
        items = self._evaluate(items_node)
        from .semantic import RepeatedView

        if isinstance(items, MatchValue):
            iterable = items.iter_rows()
            known_length = len(items)
        elif isinstance(items, NativeMatchCollection):
            iterable = iter(items)
            known_length = len(items)
        elif isinstance(items, NativeBindingCollection):
            iterable = iter(items)
            known_length = len(items)
        elif isinstance(items, MatchSet):
            iterable = iter(items.rows)
            known_length = len(items.rows)
        elif isinstance(items, RepeatedView | list):
            iterable = iter(items)
            known_length = len(items)
        else:
            raise EvaluationError(
                "foreach requires match results, a repeated field, or a list"
            )
        if known_length > 10_000:
            raise EvaluationError("foreach exceeds 10000 elements")
        statement_block = self._is_foreach_statement_block(node)
        statements = (
            [child for child in body.children if isinstance(child, Tree)]
            if statement_block
            and isinstance(body, Tree)
            and body.data == "foreach_statement_block"
            else []
        )
        results: list[Any] = []
        block_output: list[str] = []
        output_size = 0
        for index, item in enumerate(iterable):
            if index >= 10_000:
                raise EvaluationError("foreach exceeds 10000 elements")
            self._scopes.append({name: item})
            should_exit = False
            try:
                if statement_block:
                    last_value: Any = None
                    for statement in statements:
                        if str(statement.data) in {"quit", "exit"}:
                            should_exit = True
                            if not value_context:
                                self._exit_requested = True
                            break
                        last_value, output = self._evaluate_statement_once(
                            statement, source, value_context=value_context
                        )
                        if not value_context and output:
                            output_size += len(output.encode("utf-8"))
                            if output_size > 1_000_000:
                                raise EvaluationError(
                                    "foreach output exceeds 1000000 bytes"
                                )
                            block_output.append(output)
                    if value_context and not should_exit:
                        output_size += self._output_size_hint(last_value)
                        results.append(last_value)
                else:
                    result = self._evaluate(body)
                    output_size += self._output_size_hint(result)
                    results.append(result)
                if output_size > 1_000_000:
                    raise EvaluationError("foreach output exceeds 1000000 bytes")
            except EvaluationError as exc:
                if "foreach output exceeds" in str(exc):
                    raise
                raise EvaluationError(f"foreach element {index}: {exc}") from exc
            finally:
                self._scopes.pop()
            if should_exit:
                return None
        if statement_block and not value_context:
            return "\n".join(block_output)
        return results


def _source_file_path(value: Any) -> str:
    """Keep collection provenance detached from resource descriptor objects."""
    if isinstance(value, FileHandle):
        return value.path
    if isinstance(value, InputDescriptor):
        return value.path
    return str(value)
