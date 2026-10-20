"""Compiled scripts in the existing CTK prompt and workspace consoles."""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import replace
from typing import Any

from lark import Token, Tree
from lark.exceptions import UnexpectedInput

from clang_toolkit.cli.runtime import EvaluationError as LegacyEvaluationError, Runtime
from clang_toolkit.cli.runtime.collections import snapshot_collections
from clang_toolkit.cli.runtime.values import render
from clang_toolkit.cli.syntax_diagnostics import syntax_diagnostic

from .compiler import compile_program
from .runnables import RunnableBlock, invoke_named, snapshot_scopes
from .semantics import Context, ExecutionLimitError, PrototypeError
from .syntax import Node
from .tree import evaluate


class _ExitRequested(BaseException):
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
        self.source = session.source

    def _ctk(self, command: str) -> Any:
        if self.session.runtime._active_resource_scope is not None:
            raise PrototypeError("ctk() dynamic commands are unsupported inside foreground batches")
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

    def binding_state(self, name: str, node: Any = None) -> tuple[bool, Any]:
        if self.lookup_scope(name) is not None:
            return super().binding_state(name, node)
        runtime = self.session.runtime
        if name == "env":
            return True, runtime.environment
        if name == "config":
            return True, runtime.config_vars
        # Mirror the existing resolver's membership order; do not catch an
        # arbitrary evaluation failure and misreport it as a missing name.
        for scope in reversed(runtime._scopes):
            if name in scope:
                return True, scope[name]
        for namespace in (runtime.bindings, runtime.environment, runtime.config_vars):
            if name in namespace:
                return True, namespace[name]
        return False, None

    def emit(self, value: Any, node: Any = None) -> Any:
        if self.consume_depth:
            return value
        result = super().emit(value, node)
        self.session.record("print", self.output[-1])
        self.session.emitted = True
        return result


class PrototypeRuntime(Runtime):
    """Use the prototype compiler for script flow and Runtime for CTK operations."""

    def _resolve_collection_ref(self, node: Any) -> Any:
        if isinstance(node, Node):
            return self._evaluate(node)
        return super()._resolve_collection_ref(node)

    def _bare_mutation_target(self, node: Any) -> tuple[Any, Any]:
        if isinstance(node, Node):
            if node.kind != "index":
                raise LegacyEvaluationError("collection item operation requires a final [key] or [index]")
            return self._evaluate(node.children[0]), self._evaluate(node.children[1])
        return super()._bare_mutation_target(node)

    def _index_value(self, value: Any, key: Any) -> Any:
        from .semantics import index_value

        context = self._prototype_context
        if context is None:
            return super()._index_value(value, key)
        return index_value(value, key, context, None)

    def __init__(self, client: Any = None, *, script_engine: str = "compiled", **kwargs: Any) -> None:
        super().__init__(client, **kwargs)
        self._prototype_context: Context | None = None
        self._prototype_operands: dict[int, Any] = {}
        self._prototype_session = ReplSession(self, script_engine)

    def _evaluate(self, node: Any) -> Any:
        context = self._prototype_context
        templates = getattr(getattr(node, "meta", None), "ctk_templates", None)
        if context is not None and templates is not None:
            previous = context.string_templates
            context.string_templates = templates
            try:
                return self._evaluate_operand(node)
            finally:
                context.string_templates = previous
        return self._evaluate_operand(node)

    def _evaluate_operand(self, node: Any) -> Any:
        context = self._prototype_context
        if isinstance(node, Tree) and node.data == "matcher" and context is not None:
            from clang_toolkit.cli.runtime.matcher_functions import MatcherFunction
            from clang_toolkit.cli.runtime.values import MatcherExpr

            name = str(node.children[0])
            present, value = context.binding_state(name)
            if present and isinstance(value, (RunnableBlock, MatcherFunction)):
                arguments = []
                binding = None
                for child in node.children[1:]:
                    if isinstance(child, Tree) and child.data == "arguments":
                        arguments.extend(item for item in child.children if not self._punctuation(item))
                    elif isinstance(child, Tree) and child.data == "bind":
                        binding = child.children[2]
                    elif child is not None and not self._punctuation(child):
                        arguments.append(child)
                call = Node("call", name, tuple(arguments), node.meta.line, node.meta.column)
                result = invoke_named(context, call, name,
                                      lambda: [self._evaluate(item) for item in arguments])
                if binding is not None and not isinstance(result, MatcherExpr):
                    raise LegacyEvaluationError(f"{name} must return a matcher expression to use bind")
                return replace(result, binding=self._string(str(binding))) if binding is not None else result
        if not isinstance(node, Node):
            return super()._evaluate(node)
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

    def _reference_property(self, name: str, value: Any, field: str, *, root: bool) -> Any:
        context = self._prototype_context
        if root and context is not None:
            ordinal = context.loop_index(name)
            if ordinal is not None:
                if field == "index":
                    return ordinal
                if field == "value":
                    return value
        return super()._reference_property(name, value, field, root=root)

    def _has_dynamic_part(self, node: Tree) -> bool:
        if any(isinstance(child, Node) for child in node.children):
            return True
        if node.data == "matcher" and self._prototype_context is not None:
            present, value = self._prototype_context.binding_state(str(node.children[0]))
            if present and isinstance(value, RunnableBlock):
                return True
        if any(isinstance(child, Token) and child.type == "STRING"
               and str(child).startswith('"') and "{" in str(child)
               for child in node.children):
            return True
        return super()._has_dynamic_part(node)

    def _string(self, raw: str) -> str:
        context = self._prototype_context
        if context is not None and raw in context.string_templates:
            return context.string_templates[raw].render(context)
        return super()._string(raw)

    def _execute_foreground_body(self, body: Tree, source: str, *, value_context: bool) -> Any:
        context = self._prototype_context
        if context is None:
            raise PrototypeError("foreground body has no active script context")
        program = body.children[0]
        previous_depth = context.consume_depth
        previous_scopes = list(context._scopes)
        context._scopes[:] = snapshot_scopes(context._scopes)
        if value_context:
            context.consume_depth += 1
        try:
            executable = getattr(body.meta, "ctk_executable", None)
            return executable(context) if executable is not None else evaluate(program, context)
        finally:
            context.consume_depth = previous_depth
            context._scopes[:] = previous_scopes

    def _foreground_body_trees(self, body: Tree) -> Any:
        from .dependencies import execution_trees

        bindings = dict(self.bindings)
        for scope in self._scopes:
            bindings.update(scope)
        return execution_trees(body, bindings)

    def matcher_function_names(self) -> tuple[str, ...]:
        values = dict(self.bindings)
        for scope in self._scopes:
            values.update(scope)
        return tuple(dict.fromkeys((*super().matcher_function_names(),
                                    *(name for name, value in values.items() if isinstance(value, RunnableBlock)))))

    def completion_suggestions(self, reference: str) -> Any:
        return super().completion_suggestions(reference if reference.startswith("$") else "$" + reference)

    def callable_help(self) -> dict[str, Any]:
        from clang_toolkit.cli.callable_help import (
            builtin_callable_help,
            describe_callable,
        )
        from clang_toolkit.cli.runtime.matcher_functions import MatcherFunction

        values = dict(self.bindings)
        for scope in self._scopes:
            values.update(scope)
        context = self._prototype_context or _ReplContext(self._prototype_session)
        descriptions = builtin_callable_help(context.functions)
        descriptions.update(
            {
                name: describe_callable(name, value)
                for name, value in values.items()
                if isinstance(value, (RunnableBlock, MatcherFunction))
                or callable(value)
            }
        )
        return descriptions

    def completion_presence_fields(self, reference: str) -> tuple[str, ...]:
        return super().completion_presence_fields(reference if reference.startswith("$") else "$" + reference)

    def _execute_library_source(self, source: str, path: Any) -> None:
        try:
            program, executable = self._prototype_session.program(source, library=True)
        except UnexpectedInput as error:
            raise LegacyEvaluationError(f"{path}: {syntax_diagnostic(source, error)}") from error
        except ValueError as error:
            raise LegacyEvaluationError(f"{path}: {error}") from error
        for wrapper in program.children:
            node = wrapper.children[0]
            allowed = node.kind in {"let", "destructure", "runnable"} or (
                node.kind == "host" and node.value[0].data in {"matcher_definition", "import_command"})
            if not allowed:
                raise LegacyEvaluationError(
                    f"{path}:{node.line}: libraries accept let definitions and import statements")
        previous_context = self._prototype_context
        context = previous_context or _ReplContext(self._prototype_session)
        previous_scopes = list(context._scopes)
        previous_runtime_scopes = self._scopes
        previous_source = context.source
        previous_source_name = context.source_name
        previous_templates = context.string_templates
        self._prototype_context = context
        context.source = source
        context.source_name = str(path)
        context.string_templates = program.value or {}
        if self._active_resource_scope is None:
            context._scopes[:] = [self.bindings]
        self._scopes = context._scopes
        try:
            if executable is not None:
                executable(context)
            else:
                evaluate(program, context)
        except Exception as error:
            line, _column = context.current_location
            raise LegacyEvaluationError(f"{path}:{line or 1}: {error}") from error
        finally:
            context._scopes[:] = previous_scopes
            context.source = previous_source
            context.source_name = previous_source_name
            context.string_templates = previous_templates
            self._prototype_context = previous_context
            self._scopes = previous_runtime_scopes

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

    def program(self, source: str, *, library: bool = False) -> tuple[Node, Any]:
        from .repl_language import parse

        cached = self.cache.get(source)
        if cached is not None:
            self.cache.move_to_end(source)
            return cached
        if library:
            from .library_cache import parse_library

            program = parse_library(source)
        else:
            program = parse(source)
        def prepare_host(tree: Tree) -> Tree:
            tree = Tree(tree.data, [prepare(child) if isinstance(child, Node)
                                   else prepare_host(child) if isinstance(child, Tree)
                                   else child for child in tree.children], meta=tree.meta)
            if tree.data == "statement_block" and tree.children and isinstance(tree.children[0], Node):
                node = tree.children[0]
                key = f"{node.line}:{node.column}:{source}" if library else None
                tree.meta.ctk_executable = (
                    compile_program(node, cache_key=key, cache_namespace="blocks")
                    if self.engine == "compiled" else None
                )
            return tree
        def prepare(node: Node) -> Node:
            if node.kind == "host":
                node = replace(node, value=(prepare_host(node.value[0]), node.value[1]))
            node = replace(node, children=tuple(prepare(child) for child in node.children))
            if node.kind in {"let", "destructure", "assign"}:
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
        from .templates import compile_template

        templates = {}
        host_trees = []
        def collect(node: Any) -> None:
            if isinstance(node, Node):
                if node.kind == "host":
                    collect(node.value[0])
                for child in node.children:
                    collect(child)
            elif isinstance(node, Tree):
                host_trees.append(node)
                for child in node.children:
                    collect(child)
            elif isinstance(node, Token) and node.type in {"STRING", "FILE_STRING", "DIRECTORY_STRING", "PATH_STRING"}:
                raw = str(node)
                if raw not in templates:
                    template = compile_template(raw, library=library)
                    if template is not None:
                        templates[raw] = template
        collect(program)
        for tree in host_trees:
            tree.meta.ctk_templates = templates
        program = replace(program, value=templates)
        executable = compile_program(program, cache_key=source if library else None) if self.engine == "compiled" else None
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
        from .dependencies import execution_trees

        trees = list(execution_trees(program, self.runtime.bindings))
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

    def record(self, kind: str, value: Any, *, text: str | None = None, routed: bool = False, markdown: str | None = None, result_key: str | None = None) -> None:
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
        self.parts.append(DispatchResult(
            text, True, markdown=markdown, outline_value=outline,
            result_key=result_key,
        ))

    def host(self, context: Context, node: Node) -> Any:
        tree, mode = node.value
        if not isinstance(tree, Tree):
            raise PrototypeError("invalid CTK host syntax tree")
        kind = str(tree.data)
        if self.runtime._active_resource_scope is not None:
            from clang_toolkit.cli.runtime.batch_execution import _validate_body

            _validate_body(tree, self.runtime)
        if kind in {"quit", "exit"}:
            from clang_toolkit.cli.app import DispatchResult

            self.parts.append(DispatchResult(None, True))
            raise _ExitRequested()
        if kind in {"help", "help_shortcut"}:
            from .help import render_help

            return render_help(tree, self.runtime.callable_help())
        if mode == "expression" and kind not in {"display", "match"}:
            expression = Tree("display", [tree], meta=tree.meta)
            return self.runtime._evaluate_statement_once(
                expression, context.source, value_context=True)[0]
        visible = mode == "statement" and not context.consume_depth
        if visible:
            self.check_output_capacity()
        value, display = self.runtime._evaluate_statement_once(tree, context.source, value_context=not visible)
        if visible:
            self.host_displays[id(node)] = display
        return value

    def observe(self, context: Context, node: Node, value: Any) -> None:
        from clang_toolkit.cli.app import _match_result_key

        if node.kind == "loop_iteration":
            if not context.consume_depth and value is not None and self.last_tail not in {"let", "destructure", "runnable", "assign", "print", "host_display"}:
                self.record("display", value)
                self.emitted = True
            return
        tail = self.last_tail if node.kind in {"conditional", "block", "call", "invoke", "recovery"} else node.kind
        self.last_tail = tail
        if id(node) not in self.top_statements:
            if node.kind == "host" and id(node) in self.host_displays:
                display = self.host_displays.pop(id(node))
                if display is not None:
                    self.record(str(node.value[0].data), value, text=display, routed=True,
                                result_key=_match_result_key(node.value[0], context.source))
                    self.emitted = True
                    self.last_tail = "host_display"
            return
        emitted, self.emitted = self.emitted, False
        self.last_tail = None
        if node.kind in {"let", "destructure", "runnable", "assign", "print"}:
            return
        if node.kind == "host":
            tree, mode = node.value
            kind = str(tree.data)
            if kind in {"help", "help_shortcut"}:
                from .help import render_help_markdown

                self.record(kind, value, text=value, routed=True,
                            markdown=render_help_markdown(tree, self.runtime.callable_help()))
            elif mode == "statement":
                display = self.host_displays.pop(id(node), None)
                if display is not None:
                    self.record(kind, value, text=display, routed=True,
                                result_key=_match_result_key(tree, context.source))
            elif value is not None and not emitted:
                self.record("display", value)
            return
        if value is not None and tail not in {"print", "host_display"} and not (node.kind == "foreach" and emitted):
            self.record("display", value)

    # Native scalar loops must not bypass a replaced observation method.
    _plain_observer = observe

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
            context.string_templates = program.value or {}
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
