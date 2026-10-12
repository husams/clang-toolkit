"""Compiled scripts in the existing CTK prompt and workspace consoles."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import replace
from typing import Any

from lark import Tree
from lark.exceptions import UnexpectedInput

from clang_toolkit.cli.runtime import EvaluationError as LegacyEvaluationError, Runtime
from clang_toolkit.cli.runtime.collections import snapshot_collections
from clang_toolkit.cli.runtime.values import render
from clang_toolkit.cli.syntax_diagnostics import syntax_diagnostic

from .compiler import compile_program
from .semantics import Context, ExecutionLimitError, PrototypeError
from .syntax import Node
from .tree import evaluate


class _ExitRequested(Exception):
    """Stop this submission at an explicit console exit command."""


class _ReplContext(Context):
    def __init__(self, session: ReplSession) -> None:
        self.session = session
        runtime = session.runtime
        super().__init__(
            bindings=runtime.bindings,
            functions={"ctk": self._ctk},
            cancel_hook=runtime._batch_cancel_requested.is_set,
            host_evaluator=session.host,
            statement_observer=session.observe,
        )

    def _ctk(self, command: str) -> Any:
        if not isinstance(command, str):
            raise TypeError("ctk() expects one command string")
        return Runtime.evaluate(self.session.runtime, command)

    def lookup(self, name: str, node: Any = None) -> Any:
        if self.lookup_scope(name) is not None:
            return super().lookup(name, node)
        # Keep the console's config/environment reference namespaces available.
        if name == "env":
            return self.session.runtime.environment
        if name == "config":
            return self.session.runtime.config_vars
        try:
            return self.session.runtime._resolve_name(name)
        except LegacyEvaluationError:
            return super().lookup(name, node)

    def emit(self, value: Any, node: Any = None) -> Any:
        if self.consume_depth:
            return value
        result = super().emit(value, node)
        self.session.record("print", self.output[-1])
        self.session.emitted = True
        return result


class PrototypeRuntime(Runtime):
    """Use the prototype compiler for script flow and Runtime for CTK operations."""

    def __init__(self, client: Any = None, *, script_engine: str = "compiled", **kwargs: Any) -> None:
        super().__init__(client, **kwargs)
        self._prototype_context: Context | None = None
        self._prototype_operands: dict[int, Any] = {}
        self._prototype_session = ReplSession(self, script_engine)

    def _evaluate(self, node: Any) -> Any:
        if not isinstance(node, Node):
            return super()._evaluate(node)
        context = self._prototype_context
        if context is None:
            raise PrototypeError("prototype expression has no active script context")
        if self._prototype_session.engine == "tree":
            return evaluate(node, context)
        key = id(node)
        executable = self._prototype_operands.get(key)
        if executable is None:
            executable = compile_program(node)
            self._prototype_operands[key] = executable
        return executable(context)

    def close(self) -> None:
        self._prototype_session.cache.clear()
        self._prototype_session.parts.clear()
        self._prototype_session.host_displays.clear()
        self._prototype_operands.clear()
        super().close()


class ReplSession:
    """Persistent bindings, bounded compilation cache, and submission-local limits."""

    def __init__(self, runtime: PrototypeRuntime, engine: str = "compiled") -> None:
        if engine not in {"tree", "compiled"}:
            raise ValueError(f"unknown script engine {engine!r}")
        self.runtime = runtime
        self.engine = engine
        self.cache: OrderedDict[str, tuple[Node, Any]] = OrderedDict()
        self.parts: list[Any] = []
        self.source = ""
        self.emitted = False
        self.top_statements: set[int] = set()
        self.last_tail: str | None = None
        self.top_hosts: set[int] = set()
        self.host_displays: dict[int, str | None] = {}

    def program(self, source: str) -> tuple[Node, Any]:
        from .repl_language import parse

        cached = self.cache.get(source)
        if cached is not None:
            self.cache.move_to_end(source)
            return cached
        program = parse(source)
        def prepare(node: Node) -> Node:
            node = replace(node, children=tuple(prepare(child) for child in node.children))
            if node.kind in {"let", "assign"}:
                children = list(node.children)
                rhs = children[-1]
                children[-1] = Node("consume", children=(rhs,), line=rhs.line, column=rhs.column)
                node = replace(node, children=tuple(children))
            if node.kind in {"program", "block"}:
                node = replace(node, children=tuple(
                    Node("observe", children=(statement,), line=statement.line, column=statement.column)
                    for statement in node.children
                ))
            return node
        program = prepare(program)
        executable = compile_program(program) if self.engine == "compiled" else None
        self.cache[source] = (program, executable)
        if len(self.cache) > 64:
            self.cache.popitem(last=False)
        return program, executable

    def requirements(self, source: str) -> Any:
        from clang_toolkit.cli.batch import BatchRequirements

        try:
            program, _ = self.program(source)
        except Exception:
            # Dispatch reports invalid source before any evaluation occurs.
            return BatchRequirements()
        trees: list[Tree] = []
        def visit(node: Any) -> None:
            if isinstance(node, Node):
                if node.kind == "host":
                    visit(node.value[0])
                for child in node.children:
                    visit(child)
            elif isinstance(node, Tree):
                trees.append(node)
                for child in node.children:
                    visit(child)
        visit(program)
        commands = {"session_start", "session_add", "session_match", "session_pause", "session_resume", "session_close"}
        return BatchRequirements(
            query_session=any(str(tree.data) in commands for tree in trees),
            background_query=any(str(tree.data) == "background" for tree in trees),
        )

    def check_output_capacity(self) -> None:
        context = self.runtime._prototype_context
        if context is not None and len(self.parts) >= context.max_items:
            line, column = context.current_location
            raise ExecutionLimitError(f"output exceeds item limit at line {line}, column {column}")

    def record(self, kind: str, value: Any, *, text: str | None = None, routed: bool = False, markdown: str | None = None) -> None:
        from clang_toolkit.cli.app import DispatchResult

        self.check_output_capacity()
        outline = None
        structured = kind in {"print", "display", "match", "bindings_list", "file_list", "session_list", "batch_statement"}
        if self.runtime.capture_display and self.runtime.output.destination == "stdout" and structured:
            outline = (kind, snapshot_collections(value))
            if isinstance(value, (dict, list, tuple)) or kind in {"match", "file_list", "session_list"}:
                text = ""
        if text is None:
            text = render(value)
        if not routed and markdown is None:
            text = self.runtime.output.emit(text)
        self.parts.append(DispatchResult(text, True, markdown=markdown, outline_value=outline))

    def host(self, context: Context, node: Node) -> Any:
        tree, mode = node.value
        if not isinstance(tree, Tree):
            raise PrototypeError("invalid CTK host syntax tree")
        kind = str(tree.data)
        if kind in {"quit", "exit"}:
            from clang_toolkit.cli.app import DispatchResult

            self.parts.append(DispatchResult(None, True))
            raise _ExitRequested()
        if kind in {"help", "help_shortcut"}:
            from clang_toolkit.cli.help import render_help

            return render_help(tree)
        if mode == "expression" and kind not in {"display", "match"}:
            return self.runtime._evaluate(tree)
        visible = mode == "statement" and not context.consume_depth
        if visible:
            self.check_output_capacity()
        value, display = self.runtime._evaluate_statement_once(tree, self.source, value_context=not visible)
        if visible:
            self.host_displays[id(node)] = display
        return value

    def observe(self, context: Context, node: Node, value: Any) -> None:
        tail = self.last_tail if node.kind in {"conditional", "block"} else node.kind
        self.last_tail = tail
        if id(node) not in self.top_statements:
            if node.kind == "host" and id(node) in self.host_displays:
                display = self.host_displays.pop(id(node))
                if display is not None:
                    self.record(str(node.value[0].data), value, text=display, routed=True)
                    self.emitted = True
                    self.last_tail = "host_display"
            return
        emitted, self.emitted = self.emitted, False
        self.last_tail = None
        if node.kind in {"let", "assign", "print"}:
            return
        if node.kind == "host":
            tree, mode = node.value
            kind = str(tree.data)
            if kind in {"help", "help_shortcut"}:
                from clang_toolkit.cli.help import render_help_markdown

                self.record(kind, value, text=value, routed=True, markdown=render_help_markdown(tree))
            elif mode == "statement":
                display = self.host_displays.pop(id(node), None)
                if display is not None:
                    self.record(kind, value, text=display, routed=True)
            elif value is not None and not emitted:
                self.record("display", value)
            return
        if value is not None and tail not in {"print", "host_display"} and not (node.kind == "foreach" and emitted):
            self.record("display", value)

    def dispatch(self, source: str) -> Any:
        from clang_toolkit.cli.app import DispatchResult

        if not source.strip():
            return DispatchResult("", True)
        self.source, self.parts, self.emitted = source, [], False
        self.host_displays.clear()
        old_scopes = self.runtime._scopes
        old_context = self.runtime._prototype_context
        try:
            if self.runtime.history is not None:
                self.runtime.history.append(source, self.runtime.session_id, self.runtime.label)
            program, executable = self.program(source)
            self.top_statements = {id(wrapper.children[0]) for wrapper in program.children}
            self.top_hosts = {id(wrapper.children[0]) for wrapper in program.children if wrapper.children[0].kind == "host"}
            context = _ReplContext(self)
            self.runtime._prototype_context = context
            # Share the exact scope list so pushed loop/branch scopes are visible
            # to CTK leaf operations and are always removed before submission exit.
            self.runtime._scopes = context._scopes
            if executable is not None:
                executable(context)
            else:
                evaluate(program, context)
        except _ExitRequested:
            pass
        except UnexpectedInput as error:
            from lark.exceptions import UnexpectedEOF

            if isinstance(error, UnexpectedEOF):
                line = source.count("\n") + 1
                column = len(source.rsplit("\n", 1)[-1]) + 1
                diagnostic = f"syntax error at line {line}, column {column}: incomplete expression or statement at end of input"
            else:
                diagnostic = syntax_diagnostic(source, error)
            self.parts.append(DispatchResult(diagnostic, False))
        except Exception as error:
            self.parts.append(DispatchResult(f"error: {error}", False))
        finally:
            self.runtime._scopes = old_scopes
            self.runtime._prototype_context = old_context
            self.runtime._prototype_operands.clear()
            self.top_statements.clear()
            self.last_tail = None
            self.top_hosts.clear()
            self.host_displays.clear()
        if not self.parts:
            return DispatchResult("", True)
        if len(self.parts) == 1:
            return self.parts[0]
        return DispatchResult(
            "\n".join(part.output for part in self.parts if part.output),
            all(part.success for part in self.parts),
            parts=tuple(self.parts),
            exit_requested=bool(self.parts and self.parts[-1].output is None),
        )
