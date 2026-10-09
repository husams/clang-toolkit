"""Typed expression evaluator for the Python interactive shell."""

from __future__ import annotations

import os
from glob import has_magic, iglob
from collections.abc import Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from lark import Token, Tree
from lark.exceptions import UnexpectedInput

from clang_toolkit.cli.language import parser
from clang_toolkit.cli.help import HAS_NATIVE_ANALYSIS_GRAMMAR, render_help
from clang_toolkit.cli.matcher_catalog import NESTED_MATCHERS, ROOT_MATCHERS
from clang_toolkit.client import Client
from clang_toolkit.match_values import (
    BindingSelection, MatchRow, MatchValue, MatchValueError, NativeBindingCollection,
    NativeMatchCollection, ParsedTree,
)

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
from .persistence import load, save
from .values import MatchSet, MatcherExpr, QualifiedName, matcher_text, render, render_inspection
from .cursors import execute_cursor
from .traversal import execute_traversal


class EvaluationError(ValueError):
    """A valid sentence that cannot be evaluated in this runtime."""


@dataclass(frozen=True)
class CompletionField:
    """A local completion option with runtime-derived display metadata."""

    name: str
    kind: str
    display_meta: str


_KNOWN_NON_ROOT = frozenset(NESTED_MATCHERS) - frozenset(ROOT_MATCHERS)
_PUNCTUATION = {"LPAR", "RPAR", "LSQB", "RSQB", "COMMA", "DOT", "SCOPE"}
_SOURCE_SUFFIXES = {".c", ".cc", ".cpp", ".cxx", ".c++", ".C", ".m", ".mm"}


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
        self._default_targets: list[ParsedTree] = []
        self._block_owners: list[set[Any]] = []

    def _apply_compilation_settings(self) -> None:
        selected = self.config_store.effective["compile_commands"]
        self.client.compilation_database = selected
        bound = getattr(self.client, "_async_client", None)
        if bound is not None:
            bound.compilation_database = selected

    def evaluate(self, source: str) -> Any:
        """Execute a typed SDK expression or assignment without rendering it."""
        statement = parser().parse(source).children[0]
        if not isinstance(statement, Tree):
            raise EvaluationError("expected an expression")
        kind = str(statement.data)
        self._apply_compilation_settings()
        if kind == "assignment":
            self._assignment(statement)
            return self._resolve_name(str(statement.children[1]))
        if kind == "match":
            if self._match_block(statement) is not None:
                from .match_block import execute_match_block
                return execute_match_block(self, statement, source)
            return self._execute_match(statement, source=source)
        if kind in {"traverse", "traverse_expression"}:
            from .traversal import execute_traversal
            return execute_traversal(self, statement)
        if kind in {"callgraph_file", "call_graph_expression"}:
            from .call_graph import execute_call_graph
            return execute_call_graph(self, statement)
        if kind in {"cfg_file", "cfg_file_expression"}:
            from .control_flow import execute_cfg
            return execute_cfg(self, statement, source or "")
        if kind == "display":
            return self._evaluate(statement.children[0])
        raise EvaluationError("SDK execution requires an expression or assignment")

    def execute(self, source: str) -> str | None:
        """Evaluate a parsed command and return output; ``None`` means exit."""
        if self.history is not None:
            self.history.append(source, self.session_id, self.label)
        statement = parser().parse(source).children[0]
        if not isinstance(statement, Tree):
            raise EvaluationError("expected a statement")
        return self._execute_statement(statement, source)

    def _execute_statement(self, statement: Tree, source: str) -> str | None:
        """Dispatch a validated statement, including statements within a block."""
        kind = str(statement.data)
        self._apply_compilation_settings()
        if kind in {"quit", "exit"}:
            return None
        if kind in {"help", "help_shortcut"}:
            return render_help(statement)
        if kind in {"server_status", "cache_status", "cache_prune", "session_list",
                    "session_attach", "session_close_retained", "bindings_list",
                    "binding_drop", "binding_rename"}:
            from .management import execute_management
            return self.output.emit(execute_management(self, statement))
        if kind in {"cursor_open", "cursor_continue", "cursor_restart", "cursor_close"}:
            return self.output.emit(execute_cursor(self, statement))
        if kind == "traverse":
            from .graph_options import render_graph
            return self.output.emit(render_graph(execute_traversal(self, statement)))
        if kind == "session_label":
            self.label = self._string(str(statement.children[2]))
            return ""
        if kind in {"session_start", "session_add", "session_match", "session_pause", "session_resume", "session_close"}:
            if getattr(self.client, "_query_session", None) is None:
                raise EvaluationError("interactive query session is unavailable; restart the console")
            send = getattr(self.client, "send_session_command", None)
            if send is None:
                raise EvaluationError("interactive query session commands are unavailable")
            value = self._string(str(statement.children[2])) if len(statement.children) > 2 else None
            return send(
                kind.removeprefix("session_"), value, working_directory=self.cwd,
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
        if kind == "match":
            if self._match_block(statement) is not None:
                from .match_block import execute_match_block
                return execute_match_block(self, statement, source)
            return self.output.emit(
                render(self._execute_match(statement, source=source))
            )
        if kind == "background":
            matcher_node = statement.children[1]
            matcher = self._evaluate(matcher_node)
            if not isinstance(matcher, MatcherExpr):
                raise EvaluationError("background requires a matcher expression")
            if matcher.name in _KNOWN_NON_ROOT:
                raise EvaluationError(f"{matcher.name} cannot be used as a top-level matcher")
            expression = matcher_text(matcher)
            if source is not None and isinstance(matcher_node, Tree) and not self._has_dynamic_part(matcher_node):
                expression = source[matcher_node.meta.start_pos : matcher_node.meta.end_pos]
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
                        raise EvaluationError("background files cannot include directories or other values")
            if selected_files is None and self.config_store.effective["files"]:
                selected_files = [str((self.cwd / path).resolve()) for path in self.config_store.effective["files"]]
            start = getattr(self.client, "start_background_query", None)
            if start is None:
                raise EvaluationError("background queries are unavailable")
            return start(
                expression, selected_files or (), working_directory=self.cwd,
                compile_arguments=self.config_store.effective["extra_args"],
            )
        if kind == "print":
            text = render(self._evaluate(statement.children[1]))
            if len(statement.children) > 3 and statement.children[3] is not None:
                destination = self._output_path(statement.children[3])
                append = any(isinstance(item, Token) and item.type == "APPEND"
                             for item in statement.children)
                from .output import write_text
                write_text(destination, text, append=append)
                return ""
            return self.output.emit(text)
        if kind == "inspect":
            return self.output.emit(render_inspection(self._evaluate(statement.children[1])))
        if kind == "display":
            return self.output.emit(render(self._evaluate(statement.children[0])))
        if kind == "cfg_file":
            from .control_flow import execute_cfg
            from .graph_options import render_graph
            return self.output.emit(render_graph(execute_cfg(self, statement, source)))
        if kind == "cfg":
            message = ('cfg requires a file: cfg FUNCTION in "file.cc"; see help cfg'
                if HAS_NATIVE_ANALYSIS_GRAMMAR else 'cfg native execution is not implemented in this build; see help cfg')
            raise EvaluationError(message)
        if kind == "script":
            from .scripting import execute_script
            return self.output.emit(execute_script(self, statement))
        if kind == "callgraph_file":
            from .call_graph import execute_call_graph
            from .graph_options import render_graph
            return self.output.emit(render_graph(execute_call_graph(self, statement)))
        if kind == "callgraph":
            message = ('callgraph requires a file: callgraph "file.cc"; see help callgraph'
                if HAS_NATIVE_ANALYSIS_GRAMMAR else 'callgraph native execution is not implemented in this build; see help callgraph')
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
                fields[name] = tuple(sorted(value.binding_names() | {"length", "isEmpty"}))
            elif isinstance(value, MatchRow):
                fields[name] = tuple(value.bindings)
            elif isinstance(value, ParsedTree):
                fields[name] = ("path",)
            elif isinstance(value, list):
                fields[name] = ("length", "isEmpty", "joinWith")
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
                fields[name] = tuple(field for field in
                    getattr(type(value), "__dataclass_fields__", {}) if not field.startswith("_"))
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
            sources = (
                field_sources(value) if isinstance(value, MessageView) else {}
            )
            messages = {}
            results = []
            for name in field_names(value):
                source = sources.get(name)
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
                elif name in {"hasField", "fieldState", "fieldOr"} and is_semantic_view(value):
                    kind = "method"
                    meta = "method · checks field presence or reports availability"
                elif name in {"joinWith", "unique", "sort", "filter"} and isinstance(value, (list, MatchValue, NativeMatchCollection, MatchSet)):
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
            ValueError, TypeError, IndexError, KeyError, MatchValueError,
            UnexpectedInput,
        ):
            return ()

    def close(self) -> None:
        self.bindings.clear()
        self._scopes.clear()
        self._default_targets.clear()
        self._block_owners.clear()
        self.output.close()

    def _assignment(self, statement: Tree) -> None:
        name = str(statement.children[1])
        value = self._evaluate(statement.children[3])
        scope = self._scopes[-1] if self._scopes else self.bindings
        scope[name] = value

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
            if node.type in {"STRING", "FILE_STRING", "DIRECTORY_STRING", "PATH_STRING"}:
                return self._string(str(node))
            if node.type in {"NUMBER", "NEGATIVE_NUMBER"}:
                raw = str(node)
                return float(raw) if any(char in raw for char in ".eE") else int(raw)
            raise EvaluationError(f"unexpected {node.type} token")
        if not isinstance(node, Tree):
            raise EvaluationError("incomplete expression")
        kind = str(node.data)
        if kind == "true":
            return True
        if kind == "false":
            return False
        if kind == "reference":
            return self._reference(node)
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
            return MatcherExpr(name, tuple(args), binding)
        if kind == "nested_qualified_name":
            return QualifiedName("".join(map(str, node.children)))
        if kind == "list_value":
            return [
                self._evaluate(item)
                for item in node.children
                if not self._punctuation(item) and item is not None
            ]
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
        if kind == "match_expression":
            return self._execute_match(node)
        if kind == "parse_expression":
            target = self._evaluate(node.children[1])
            if isinstance(target, File):
                target = target.absolute
            if not isinstance(target, str):
                raise EvaluationError("parse requires a file path")
            return self._track_native_value(self.client.parse(target, working_directory=self.cwd,
                compile_arguments=self.config_store.effective["extra_args"]))
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
        if kind == "foreach_expression":
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
                    value = call_method(value, name, [self._evaluate(arg) for arg in arguments])
            except (ReferenceError, MatchValueError, IndexError, KeyError) as error:
                raise EvaluationError(f"{error} in grouped expression") from error
        return value

    def _method_call_parts(self, call: Tree) -> tuple[str, list[Any]]:
        if call.data == "generic_method_call":
            method_token = call.children[0].children[0]
            arguments_node = call.children[2]
            arguments = [
                item for item in arguments_node.children
                if not self._punctuation(item)
            ]
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
        if isinstance(node.children[1], Tree) and node.children[1].data == "parse_expression":
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
            return set().union(*(Runtime._native_owners(item) for item in value.matches))
        if isinstance(value, NativeBindingCollection):
            return set().union(
                *(Runtime._native_owners(item) for item in value.selections if item is not None),
                *(Runtime._native_owners(item) for item in value.matches),
            )
        if isinstance(value, list | tuple):
            return set().union(*(Runtime._native_owners(item) for item in value))
        if isinstance(value, Mapping):
            return set().union(*(Runtime._native_owners(item) for item in value.values()))
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
                line = expression.meta.line if isinstance(expression, Tree) else expression.line
                column = expression.meta.column if isinstance(expression, Tree) else expression.column
                segment = f"[{expression}]" if isinstance(expression, Token) else "[index]"
                steps.append(("index", key, None, segment, line, column))
                index += 3
                continue
            token = children[index + 1]
            method_call = token if isinstance(token, Tree) else None
            if method_call is not None and method_call.data in {
                "has_field_call", "field_state_call", "field_or_call",
                "generic_method_call",
            }:
                if method_call.data == "generic_method_call":
                    method_token = method_call.children[0].children[0]
                    arguments_node = method_call.children[2]
                    arguments = [
                        item for item in arguments_node.children
                        if not self._punctuation(item)
                    ]
                else:
                    method_token = method_call.children[0]
                    if method_call.data == "field_or_call":
                        arguments = [method_call.children[2], method_call.children[4]]
                    else:
                        arguments = [method_call.children[2]]
                method = str(method_token)
                steps.append(("method", method, arguments,
                              f".{method}(...)", method_token.line, method_token.column))
                index += 2
            else:
                steps.append(("property", str(token), None, f".{token}", token.line, token.column))
                index += 2

        local_name = any(name in scope for scope in self._scopes)
        if name in {"env", "config"} and not local_name and steps and steps[0][0] == "property":
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
                    value = call_method(value, field, [self._evaluate(argument) for argument in argument])
                elif operation == "index":
                    value = index_value(value, field)
                else:
                    value = property_value(value, field)
                if operation == "index" and isinstance(previous, MatchValue) and type(field) is int:
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
        self, node: Tree, *, source: str | None = None,
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
        files = None
        target: Any = self._default_targets[-1] if self._default_targets else None
        if len(node.children) > 3 and node.children[3] is not None:
            selected = self._evaluate(node.children[3])
            if isinstance(selected, str | Directory):
                path = selected.absolute if isinstance(selected, Directory) else selected
                files = self._match_paths(path)
                target = None if files is not None else path
            elif isinstance(selected, File | ParsedTree | MatchValue | BindingSelection
                           | NativeMatchCollection | NativeBindingCollection):
                target = selected.absolute if isinstance(selected, File) else selected
            elif isinstance(selected, list):
                target = None
                files = []
                for entry in selected:
                    if isinstance(entry, File):
                        files.append(entry.absolute)
                    elif isinstance(entry, str):
                        files.append(str((self.cwd / entry).resolve()))
                    else:
                        raise EvaluationError(
                            "match files cannot include directories or other values"
                        )
            else:
                raise EvaluationError("match target must be a file list, path, directory, glob, tree or binding selection")
        try:
            text = matcher_text(matcher)
        except TypeError as exc:
            raise EvaluationError(str(exc)) from exc
        if source is not None and isinstance(matcher_node, Tree):
            original = source[matcher_node.meta.start_pos : matcher_node.meta.end_pos]
            if not self._has_dynamic_part(matcher_node):
                text = original
        if target is not None:
            traversal = self.config_store.effective["traversal"]
            from clang_toolkit._generated.match.v1 import match_service_pb2 as pb
            traversal_mode = (
                pb.MATCH_TRAVERSAL_MODE_IGNORE_UNLESS_SPELLED_IN_SOURCE
                if traversal in {"ignore_unless_spelled_in_source", "IgnoreUnlessSpelledInSource"}
                else pb.MATCH_TRAVERSAL_MODE_AS_IS
            )
            options = {
                "working_directory": self.cwd,
                "compile_arguments": self.config_store.effective["extra_args"],
                "traversal_mode": traversal_mode,
            }
            if isinstance(target, NativeMatchCollection | NativeBindingCollection):
                if isinstance(target, NativeMatchCollection):
                    sources = target.matches
                    files_for_sources = target.files
                else:
                    source_pairs = [
                        (selection, path)
                        for selection, path in zip(target.selections, target.files, strict=True)
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
                    NativeMatchCollection(tuple(matches), tuple(files_for_sources))
                )
            return self._track_native_value(
                self._match_target(text, target, options, on_row)
            )
        if files is None and self.config_store.effective["files"]:
            files = [
                str((self.cwd / path).resolve())
                for path in self.config_store.effective["files"]
            ]
        if files is None:
            if on_row is not None:
                raise EvaluationError("match do requires a target, configured files, or an enclosing parsed tree")
            rows = self.client.match(
                text, files=None, working_directory=self.cwd,
                compile_arguments=self.config_store.effective["extra_args"],
            )
            return MatchSet(tuple(rows))
        max_files = self._match_setting("max_files", 100)
        if len(files) > max_files:
            raise EvaluationError(f"match file list exceeds configured limit of {max_files}")
        from clang_toolkit._generated.match.v1 import match_service_pb2 as pb
        traversal_mode = (
            pb.MATCH_TRAVERSAL_MODE_IGNORE_UNLESS_SPELLED_IN_SOURCE
            if self.config_store.effective["traversal"] in {
                "ignore_unless_spelled_in_source", "IgnoreUnlessSpelledInSource"
            }
            else pb.MATCH_TRAVERSAL_MODE_AS_IS
        )
        matches = self._match_files(
            text, files, on_row=on_row, working_directory=self.cwd,
            compile_arguments=self.config_store.effective["extra_args"],
            traversal_mode=traversal_mode,
        )
        return self._track_native_value(NativeMatchCollection(tuple(matches), tuple(files)))

    def _match_files(self, text: str, targets: list[Any] | tuple[Any, ...],
                     on_row: Callable[[Any, Any], None] | None = None,
                     **options: Any) -> list[MatchValue]:
        if len(targets) < 2:
            return [self._match_target(text, target, options, on_row) for target in targets]
        workers = self._match_setting("pool_size", 4) or 4
        futures = []
        try:
            with ThreadPoolExecutor(max_workers=min(workers, len(targets))) as pool:
                try:
                    for target in targets:
                        futures.append(pool.submit(self._match_target, text, target, options, on_row))
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

    def _match_target(self, text: str, target: Any, options: dict[str, Any],
                      on_row: Callable[[Any, Any], None] | None) -> MatchValue:
        if on_row is None:
            return self.client.match_in(text, target, **options)
        return self.client.match_in(text, target, **options,
                                    on_row=lambda row: on_row(row, target))

    @staticmethod
    def _match_block(node: Tree) -> Tree | None:
        return next((child for child in node.children
                     if isinstance(child, Tree) and child.data == "statement_block"), None)

    def _match_paths(self, target: str) -> list[str] | None:
        """Expand local directories/globs; leave literal file paths unchanged."""
        path = self.cwd / target
        if path.is_file():
            return None
        if path.is_dir():
            candidates = (
                item for item in path.rglob("*")
                if item.suffix in _SOURCE_SUFFIXES
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
                    raise EvaluationError(f"match file list exceeds configured limit of {max_files}")
        return sorted(files)

    def _match_setting(self, name: str, default: int) -> int:
        owner = getattr(self.client, "client", self.client)
        configure = getattr(owner, "_configuration", None)
        config = configure() if configure else getattr(owner, "config", None)
        value = getattr(config, name, default)
        return value if type(value) is int and value >= 0 else default

    @staticmethod
    def _has_dynamic_part(node: Tree) -> bool:
        if node.data == "reference":
            return True
        return any(
            (
                isinstance(child, Tree)
                and (child.data == "reference" or Runtime._has_dynamic_part(child))
            )
            or (
                isinstance(child, Token)
                and child.type == "STRING"
                and str(child).startswith('"')
                and "$" in str(child)
            )
            for child in node.children
        )

    def _foreach(self, node: Tree) -> list[Any]:
        iterator = node.children[1]
        if not isinstance(iterator, Tree) or iterator.data != "reference":
            raise EvaluationError("foreach iterator must be a variable")
        names = [
            str(item)
            for item in iterator.children
            if isinstance(item, Token) and item.type == "NAME"
        ]
        if len(names) != 1 or len(iterator.children) != 2:
            raise EvaluationError("foreach iterator cannot use a field")
        items = self._evaluate(node.children[3])
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
            raise EvaluationError("foreach requires match results, a repeated field, or a list")
        if known_length > 10_000:
            raise EvaluationError("foreach exceeds 10000 elements")
        results: list[Any] = []
        output_size = 0
        for index, item in enumerate(iterable):
            if index >= 10_000:
                raise EvaluationError("foreach exceeds 10000 elements")
            self._scopes.append({names[0]: item})
            try:
                result = self._evaluate(node.children[5])
                output_size += self._output_size_hint(result)
                if output_size > 1_000_000:
                    raise EvaluationError("foreach output exceeds 1000000 bytes")
                results.append(result)
            except EvaluationError as exc:
                if "foreach output exceeds" in str(exc):
                    raise
                raise EvaluationError(f"foreach element {index}: {exc}") from exc
            finally:
                self._scopes.pop()
        return results
