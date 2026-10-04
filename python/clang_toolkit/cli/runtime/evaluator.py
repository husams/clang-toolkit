"""Typed expression evaluator for the Python interactive shell."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from lark import Token, Tree

from clang_toolkit.cli.language import parser
from clang_toolkit.cli.matcher_catalog import NESTED_MATCHERS, ROOT_MATCHERS
from clang_toolkit.client import Client

from .config import ConfigError, ConfigStore
from .filesystem import Directory, File, FileSystemEntry, from_path
from .references import ReferenceError, call_method, property_value
from .templates import TemplateError, evaluate_string
from .history import HistoryStore
from .output import OutputSink
from .persistence import load, save
from .values import MatchSet, MatcherExpr, QualifiedName, matcher_text, render


class EvaluationError(ValueError):
    """A valid sentence that cannot be evaluated in this runtime."""


_KNOWN_NON_ROOT = frozenset(NESTED_MATCHERS) - frozenset(ROOT_MATCHERS)
_PUNCTUATION = {"LPAR", "RPAR", "LSQB", "RSQB", "COMMA", "DOT", "SCOPE"}


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

    def execute(self, source: str) -> str | None:
        """Evaluate a parsed command and return output; ``None`` means exit."""
        if self.history is not None:
            self.history.append(source, self.session_id, self.label)
        statement = parser().parse(source).children[0]
        if not isinstance(statement, Tree):
            raise EvaluationError("expected a statement")
        kind = str(statement.data)
        if kind in {"quit", "exit"}:
            return None
        if kind == "help":
            return "commands: match, let, print, foreach, set, clear, save, load, cfg, callgraph, help, quit"
        if kind == "session_label":
            self.label = self._string(str(statement.children[2]))
            return ""
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
            path = self.cwd / self._string(str(statement.children[3]))
            format_name = (
                str(statement.children[-1])
                if len(statement.children) > 5 and statement.children[-1] is not None
                else None
            )
            save(value, path, format_name=format_name)
            return ""
        if kind == "load_command":
            path = self.cwd / self._string(str(statement.children[1]))
            target = statement.children[3]
            names = [
                str(item)
                for item in target.children
                if isinstance(item, Token) and item.type == "NAME"
            ]
            if len(names) != 1 or len(target.children) != 2:
                raise EvaluationError("load target must be a simple variable")
            value = load(path)
            self.bindings[names[0]] = value
            return ""
        if kind == "assignment":
            name = str(statement.children[1])
            value = self._evaluate(statement.children[3])
            self.bindings[name] = value
            return ""
        if kind == "match":
            return self.output.emit(
                render(self._execute_match(statement, source=source))
            )
        if kind == "print":
            return self.output.emit(render(self._evaluate(statement.children[1])))
        if kind == "display":
            return self.output.emit(render(self._evaluate(statement.children[0])))
        if kind == "cfg":
            argument = source[statement.children[0].end_pos :].strip()
            return self.output.emit(self.client.cfg(argument))
        if kind == "callgraph":
            if len(statement.children) > 1 and statement.children[1] is not None:
                raise EvaluationError("callgraph selection is not implemented yet")
            return self.output.emit(self.client.callgraph())
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
            if isinstance(value, list):
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
                fields[name] = tuple(getattr(type(value), "__dataclass_fields__", {}))
        return fields

    def close(self) -> None:
        self.output.close()

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
                else self._string(str(target))
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
            if node.type == "STRING":
                return self._string(str(node))
            if node.type == "NUMBER":
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
        if kind == "foreach_expression":
            return self._foreach(node)
        raise EvaluationError(f"unsupported expression: {kind}")

    @staticmethod
    def _punctuation(node: Any) -> bool:
        return isinstance(node, Token) and node.type in _PUNCTUATION

    def _reference(self, node: Tree) -> Any:
        children = node.children
        name = str(children[1])
        steps: list[tuple[str, str, Any | None]] = []
        index = 2
        while index < len(children):
            token = children[index + 1]
            if isinstance(token, Token) and token.type == "JOIN_WITH":
                steps.append(("method", str(token), children[index + 3]))
                index += 5
            else:
                steps.append(("property", str(token), None))
                index += 2

        if name in {"env", "config"} and steps and steps[0][0] == "property":
            key = steps.pop(0)[1]
            source = self.environment if name == "env" else self.config_vars
            if key not in source:
                raise EvaluationError(f"unknown {name} variable: {key}")
            value: Any = source[key]
        else:
            value = self._resolve_name(name)
        for operation, field, argument in steps:
            try:
                if operation == "method":
                    value = call_method(value, field, [self._evaluate(argument)])
                else:
                    value = property_value(value, field)
            except ReferenceError as exc:
                raise EvaluationError(str(exc)) from exc
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

    def _string(self, raw: str) -> str:
        try:
            return evaluate_string(raw, self._evaluate)
        except TemplateError as exc:
            raise EvaluationError(str(exc)) from exc

    def _execute_match(self, node: Tree, *, source: str | None = None) -> MatchSet:
        matcher_node = node.children[1]
        matcher = self._evaluate(matcher_node)
        if not isinstance(matcher, MatcherExpr):
            raise EvaluationError("match requires a matcher expression")
        if matcher.name in _KNOWN_NON_ROOT:
            raise EvaluationError(
                f"{matcher.name} cannot be used as a top-level matcher"
            )
        files = None
        if len(node.children) > 3 and node.children[3] is not None:
            selected = self._evaluate(node.children[3])
            if not isinstance(selected, list):
                raise EvaluationError("match files must be a list of files")
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
        try:
            text = matcher_text(matcher)
        except TypeError as exc:
            raise EvaluationError(str(exc)) from exc
        if source is not None and isinstance(matcher_node, Tree):
            original = source[matcher_node.meta.start_pos : matcher_node.meta.end_pos]
            if not self._has_dynamic_part(matcher_node):
                text = original
        if files is None and self.config_store.effective["files"]:
            files = [
                str((self.cwd / path).resolve())
                for path in self.config_store.effective["files"]
            ]
        if files is None:
            rows = self.client.match(text)
        else:
            rows = self.client.match(text, files=files)
        return MatchSet(tuple(rows))

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
        if not isinstance(items, list):
            raise EvaluationError("foreach requires a list")
        if len(items) > 10_000:
            raise EvaluationError("foreach list exceeds 10000 elements")
        results: list[Any] = []
        for index, item in enumerate(items):
            self._scopes.append({names[0]: item})
            try:
                results.append(self._evaluate(node.children[5]))
            except EvaluationError as exc:
                raise EvaluationError(f"foreach element {index}: {exc}") from exc
            finally:
                self._scopes.pop()
        return results
