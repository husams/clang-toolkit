"""Recursive Python-AST compiler for the experimental scripting runtime."""

from __future__ import annotations

import ast
from collections.abc import Mapping
from typing import Any, Callable

from .semantics import (
    Context, ExecutionLimitError, Node, PrototypeError, _as_bool, _binary,
    _ensure_dict_capacity, _ensure_insertable, _error, _finite, _int, _kind, _name, _unary, child, children,
    child_values, consumed_value, host_value, index_value, iterable_value, observe_statement,
    loop_condition, complete_loop_iteration, binding_property_value, validate_loop_property_target,
    _static_predicate_name, _predicate, _predicate_binding,
)
from .runnables import create_clause_runnable, create_runnable, define_runnable, invoke_named
from .patterns import define_pattern
from .control import FATAL_ERRORS, LoopBreak, LoopContinue, cleanup, recover, split_handlers


def _tick(context: Context, node: Any) -> None:
    context.tick(node)


def _literal(context: Context, node: Any, value: Any) -> Any:
    if type(value) is int:
        return _int(context, value, node)
    if type(value) is float:
        return _finite(context, value, node)
    return value


def _make_list(context: Context, node: Any, count: int, thunk: Callable[[], list[Any]]) -> list[Any]:
    if count > context.max_items:
        raise _error(context, node, "list exceeds item limit", ExecutionLimitError)
    result = thunk()
    if len(result) > context.max_items:
        raise _error(context, node, "list exceeds item limit", ExecutionLimitError)
    return result


def _make_tuple(context: Context, node: Any, count: int, thunk: Callable[[], list[Any]]) -> tuple[Any, ...]:
    if count > context.max_items:
        raise _error(context, node, "tuple exceeds item limit", ExecutionLimitError)
    return tuple(thunk())


def _make_dict(context: Context, node: Any, count: int, thunk: Callable[[], list[tuple[Any, Any]]]) -> dict[Any, Any]:
    if count > context.max_items:
        raise _error(context, node, "dictionary exceeds item limit", ExecutionLimitError)
    result: dict[Any, Any] = {}
    try:
        for key, value in thunk():
            if type(key) is not str:
                raise _error(context, node, "dictionary keys must be strings")
            result[key] = value
    except TypeError as error:
        raise _error(context, node, "dictionary key is not hashable") from error
    if len(result) > context.max_items:
        raise _error(context, node, "dictionary exceeds item limit", ExecutionLimitError)
    return result


def _get(context: Context, node: Any, base: Any, name: str) -> Any:
    try:
        return binding_property_value(context, child(node, "base", 0), base, name)
    except Exception as error:
        raise _error(context, node, f"property {name!r} is unavailable on {type(base).__name__}: {error}") from error


def _slice(context: Context, node: Any, start: Any, stop: Any, step: Any) -> slice:
    from .selection import make_slice

    try:
        return make_slice(start, stop, step)
    except (TypeError, ValueError) as error:
        raise _error(context, node, str(error)) from error


def _iterable(context: Context, node: Any, value: Any) -> Any:
    return iterable_value(context, node, value)


def _call(context: Context, node: Any, name: str, args: Callable[[], list[Any]]) -> Any:
    try:
        return invoke_named(context, node, name, args)
    except PrototypeError as error:
        if getattr(node, "line", None) is not None and f"line {getattr(node, 'line')}" not in str(error):
            raise _error(context, node, str(error), type(error)) from error
        raise
    except Exception as error:
        raise _error(context, node, f"host function {name!r} failed: {error}") from error


def _invoke(context: Context, node: Node, callee: Callable[[], Any], args: Callable[[], list[Any]]) -> Any:
    from dataclasses import replace
    from .runnables import invoke_value

    try:
        return invoke_value(context, replace(node, children=node.children[1:]), callee(), args)
    except PrototypeError:
        raise
    except Exception as error:
        raise _error(context, node, f"call failed: {error}") from error


def _pipe(context: Context, node: Any, initial: Callable[[], Any], stages: list[Any]) -> Any:
    from .runnables import run_pipe

    return run_pipe(context, node, initial, stages)


def _run_scoped(context: Context, function: Callable[[Context], Any]) -> Any:
    context.push_scope()
    try:
        return function(context)
    finally:
        context.pop_scope()


def _conditional(context: Context, node: Any, condition: Callable[[], Any], true_fn: Callable[[Context], Any], false_fn: Callable[[Context], Any]) -> Any:
    return _run_scoped(context, true_fn if _as_bool(context, condition(), node) else false_fn)


def _print(context: Context, value: Callable[[], Any], node: Any) -> Any:
    result = value()
    return context.emit(result, node)


def _assign_ref(context: Context, node: Any, name: str, operator: str, value: Callable[[], Any]) -> Any:
    scope = context.lookup_scope(name)
    if scope is None:
        raise _error(context, node, f"cannot assign undefined binding {name!r}")
    old = scope[name] if operator != "=" else None
    result = value()
    if operator != "=":
        result = _binary(context, operator[:-1], old, result, node)
    scope[name] = result
    return result


def _assign_index(context: Context, node: Any, target_node: Any, operator: str, base: Any, key: Any, value: Callable[[], Any]) -> Any:
    if type(key) is bool:
        raise _error(context, node, "boolean is not a valid index")
    if isinstance(base, list):
        if type(key) is not int or key < 0 or key >= len(base):
            raise _error(context, node, "list assignment index out of range")
        old = base[key] if operator != "=" else None
        result = value()
        if operator != "=":
            result = _binary(context, operator[:-1], old, result, node)
        _ensure_insertable(context, base, result, target_node)
        base[key] = result
        return result
    if isinstance(base, dict):
        if type(key) is not str:
            raise _error(context, node, "dictionary assignment keys must be strings")
        present = key in base
        if operator != "=" and not present:
            raise _error(context, node, f"undefined dictionary key {key!r}")
        old = base[key] if operator != "=" else None
        result = value()
        if operator != "=":
            result = _binary(context, operator[:-1], old, result, node)
        _ensure_dict_capacity(context, base, key, target_node)
        _ensure_insertable(context, base, result, target_node)
        base[key] = result
        return result
    raise _error(context, node, "assignment requires a mutable list or dictionary")


def _assign_get(context: Context, node: Any, target_node: Any, operator: str, base: Any, key: str, value: Callable[[], Any]) -> Any:
    validate_loop_property_target(context, target_node)
    if not isinstance(base, dict):
        raise _error(context, node, "dot assignment requires a mutable dictionary")
    if operator != "=" and key not in base:
        raise _error(context, node, f"undefined dictionary key {key!r}")
    old = base[key] if operator != "=" else None
    result = value()
    if operator != "=":
        result = _binary(context, operator[:-1], old, result, node)
    _ensure_dict_capacity(context, base, key, target_node)
    _ensure_insertable(context, base, result, target_node)
    base[key] = result
    return result


def _bad_target(context: Context, node: Any) -> Any:
    raise _error(context, node, "assignment target must be a binding or mutable index")


def _check_items(context: Context, node: Any, count: int) -> None:
    if count >= context.max_items:
        raise _error(context, node, "foreach result exceeds item limit", ExecutionLimitError)


class _Lowerer:
    def __init__(self, root: Any) -> None:
        self.root = root
        self.nodes: list[Any] = []
        self.values: list[Any] = []
        self.node_ids: dict[int, int] = {}
        self.value_ids: dict[int, int] = {}
        self.functions: list[ast.FunctionDef] = []
        self.counter = 0

    def node_ref(self, node: Any) -> ast.expr:
        key = id(node)
        index = self.node_ids.get(key)
        if index is None:
            index = len(self.nodes)
            self.node_ids[key] = index
            self.nodes.append(node)
        return ast.Subscript(ast.Name("nodes", ast.Load()), ast.Constant(index), ast.Load())

    def value_ref(self, value: Any) -> ast.expr:
        key = id(value)
        index = self.value_ids.get(key)
        if index is None:
            index = len(self.values)
            self.value_ids[key] = index
            self.values.append(value)
        return ast.Subscript(ast.Name("values", ast.Load()), ast.Constant(index), ast.Load())

    @staticmethod
    def call(name: str, *args: ast.expr) -> ast.Call:
        return ast.Call(ast.Name(name, ast.Load()), list(args), [])

    @staticmethod
    def lambda0(expr: ast.expr) -> ast.Lambda:
        return ast.Lambda(ast.arguments([], [], None, [], [], None, []), expr)

    def ticked(self, node: Any, expr: ast.expr) -> ast.expr:
        # Python evaluates tuple elements left to right: charge the step before
        # evaluating the expression, without allocating and calling a closure.
        return ast.Subscript(ast.Tuple([
            self.call("_tick", ast.Name("context", ast.Load()), self.node_ref(node)), expr,
        ], ast.Load()), ast.Constant(1), ast.Load())

    def emit_expr(self, node: Any) -> ast.expr:
        kind = _kind(node)
        nref = self.node_ref(node)
        context = ast.Name("context", ast.Load())
        if kind == "literal":
            expr = self.call("_literal", context, nref, self.value_ref(getattr(node, "value", None)))
        elif kind == "ref":
            expr = ast.Call(ast.Attribute(context, "lookup", ast.Load()), [ast.Constant(_name(node)), nref], [])
        elif kind == "list":
            items = child_values(node)
            expr = self.call("_make_list", context, nref, ast.Constant(len(items)), self.lambda0(ast.List([self.emit_expr(x) for x in items], ast.Load())))
        elif kind == "tuple":
            items = child_values(node)
            expr = self.call("_make_tuple", context, nref, ast.Constant(len(items)), self.lambda0(ast.List([self.emit_expr(x) for x in items], ast.Load())))
        elif kind == "dict":
            raw = children(node)
            entries = tuple(raw.values()) if isinstance(raw, Mapping) else child_values(node)
            if isinstance(raw, Mapping) and not any(k in raw for k in ("entries", "items", "elements", "children", "statements")):
                entries = tuple((k, v) for k, v in raw.items())
            pairs: list[ast.expr] = []
            for entry in entries:
                if isinstance(entry, tuple) and len(entry) == 2 and not hasattr(entry, "kind"):
                    key, value = entry
                else:
                    key, value = getattr(entry, "value", None), child(entry, "expr", 0)
                    if value is None:
                        value = child_values(entry)[0]
                key_expr = self.emit_expr(key) if hasattr(key, "kind") else self.value_ref(key)
                pairs.append(ast.Tuple([key_expr, self.emit_expr(value)], ast.Load()))
            expr = self.call("_make_dict", context, nref, ast.Constant(len(pairs)), self.lambda0(ast.List(pairs, ast.Load())))
        elif kind == "get":
            expr = self.call("_get", context, nref, self.emit_expr(child(node, "base", 0)), ast.Constant(str(getattr(node, "value", None))))
        elif kind == "index":
            expr = self.call("_index", self.emit_expr(child(node, "base", 0)), self.emit_expr(child(node, "key", 1)), context, nref)
        elif kind == "omitted":
            from .selection import OMITTED

            expr = self.value_ref(OMITTED)
        elif kind == "slice":
            expr = self.call("_slice", context, nref, *(self.emit_expr(bound) for bound in child_values(node)))
        elif kind == "consume":
            expr = self.call("_consume", context, self.lambda0(self.emit_expr(child_values(node)[0])))
        elif kind == "host":
            expr = self.call("_host", context, nref)
        elif kind == "inline_runnable":
            expr = self.emit_runnable(node, "_create_runnable")
        elif kind == "clause_runnable":
            executables = ast.Tuple([ast.Name(self.emit_block_function(clause.children[0]), ast.Load())
                                     for clause in node.children], ast.Load())
            expr = self.call("_create_clauses", context, nref, executables)
        elif kind == "call":
            args = [self.emit_expr(child_values(x)[0] if _kind(x) == "keyword_arg" else x) for x in child_values(node)]
            expr = self.call("_call", context, nref, ast.Constant(_name(node)), self.lambda0(ast.List(args, ast.Load())))
        elif kind == "invoke":
            values = child_values(node)
            args = [self.emit_expr(child_values(x)[0] if _kind(x) == "keyword_arg" else x) for x in values[1:]]
            expr = self.call("_invoke", context, nref, self.lambda0(self.emit_expr(values[0])), self.lambda0(ast.List(args, ast.Load())))
        elif kind == "pipe":
            values = child_values(node)
            stages = []
            for stage in values[1:]:
                args = [] if _kind(stage) == "ref" else [
                    self.emit_expr(child_values(item)[0] if _kind(item) == "keyword_arg" else item)
                    for item in child_values(stage)
                ]
                stages.append(ast.Tuple([self.node_ref(stage), ast.Constant(_name(stage)),
                                         self.lambda0(ast.List(args, ast.Load()))], ast.Load()))
            expr = self.call("_pipe", context, nref, self.lambda0(self.emit_expr(values[0])), ast.List(stages, ast.Load()))
        elif kind == "recovery":
            body = ast.Lambda(ast.arguments([], [ast.arg("context")], None, [], [], None, []), self.emit_expr(child_values(node)[0]))
            fallback_fn = ast.Name(self.emit_block_function(child_values(node)[1]), ast.Load())
            fallback = ast.Lambda(ast.arguments([], [ast.arg("context")], None, [], [], None, []),
                                  self.call("_run_scoped", context, fallback_fn))
            expr = self.call("_recover", context, body, fallback)
        elif kind == "foreach":
            return self.call(self.emit_foreach_function(node), context)
        elif kind in {"while", "repeat"}:
            return self.call(self.emit_condition_loop_function(node), context)
        elif kind == "binary":
            op = str(getattr(node, "value", None))
            left, right = child(node, "lhs", 0), child(node, "rhs", 1)
            if op in {"and", "or"}:
                expr = ast.BoolOp(ast.And() if op == "and" else ast.Or(), [
                    self.call("_as_bool", context, self.emit_expr(operand), nref)
                    for operand in (left, right)
                ])
            else:
                expr = self.call("_binary", context, ast.Constant(op), self.emit_expr(left), self.emit_expr(right), nref)
        elif kind == "predicate":
            op = str(getattr(node, "value", None))
            operand = child(node, "operand", 0)
            if operand is None:
                operand = child(node, "lhs", 0)
            if op in {"is_defined", "is_not_defined", "is_set", "is_not_set"}:
                if _kind(operand) != "ref":
                    expr = self.call("_predicate_binding", context, nref, ast.Constant(op), ast.Constant(None))
                else:
                    expr = self.call("_predicate_binding", context, nref, ast.Constant(op), ast.Constant(_name(operand)))
            elif op in {"is_kind", "is_not_kind"}:
                kind_node = child(node, "kind", 1)
                kind_name = _static_predicate_name(kind_node)
                expr = self.call("_predicate", context, nref, ast.Constant(op), self.emit_expr(operand), ast.Constant(kind_name))
            elif op in {"has", "does_not_have"}:
                key_node = child(node, "key", 1)
                key_name = _static_predicate_name(key_node)
                key_expr = ast.Constant(key_name) if key_name is not None else self.emit_expr(key_node)
                expr = self.call("_predicate", context, nref, ast.Constant(op), self.emit_expr(operand), key_expr)
            elif op in {"in", "not_in"}:
                rhs = child(node, "rhs", 1)
                expr = self.call("_predicate", context, nref, ast.Constant(op), self.emit_expr(operand), self.emit_expr(rhs))
            else:
                expr = self.call("_predicate", context, nref, ast.Constant(op), ast.Constant(None), ast.Constant(None))
        elif kind == "unary":
            expr = self.call("_unary", context, ast.Constant(str(getattr(node, "value", None))), self.emit_expr(child(node, "expr", 0)), nref)
        elif kind == "conditional":
            true_fn = self.emit_block_function(child(node, "block", 1))
            false_fn = self.emit_block_function(child(node, "block", 2))
            expr = self.call("_conditional", context, nref, self.lambda0(self.emit_expr(child(node, "condition", 0))), ast.Name(true_fn, ast.Load()), ast.Name(false_fn, ast.Load()))
        elif kind == "block":
            expr = self.call("_run_scoped", context, ast.Name(self.emit_block_function(node), ast.Load()))
        else:
            raise ValueError(f"unknown expression node {kind!r}")
        return self.ticked(node, expr)

    def emit_runnable(self, node: Any, helper: str) -> ast.expr:
        body = self.emit_block_function(child_values(node)[0])
        defaults = ast.Tuple([ast.Name(self.emit_block_function(default), ast.Load())
                              for default in child_values(node)[1:]], ast.Load())
        return self.call(helper, ast.Name("context", ast.Load()), self.node_ref(node),
                         ast.Name(body, ast.Load()), defaults)

    def emit_assignment(self, node: Any) -> ast.expr:
        target, value = child(node, "target", 0), child(node, "expr", 1)
        context, nref = ast.Name("context", ast.Load()), self.node_ref(node)
        operator = str(getattr(node, "value", "="))
        if _kind(target) == "ref":
            return self.call("_assign_ref", context, nref, ast.Constant(_name(target)), ast.Constant(operator), self.lambda0(self.emit_expr(value)))
        if _kind(target) == "index":
            return self.call("_assign_index", context, nref, self.node_ref(target), ast.Constant(operator), self.emit_expr(child(target, "base", 0)), self.emit_expr(child(target, "key", 1)), self.lambda0(self.emit_expr(value)))
        if _kind(target) == "get":
            return self.call("_assign_get", context, nref, self.node_ref(target), ast.Constant(operator), self.emit_expr(child(target, "base", 0)), ast.Constant(str(getattr(target, "value", None))), self.lambda0(self.emit_expr(value)))
        return self.call("_bad_target", context, self.node_ref(target))

    def emit_block_function(self, block: Any, *, value_context: bool = True) -> str:
        name = f"_block_{self.counter}"
        self.counter += 1
        values = child(block, "statements", 0, ()) if isinstance(children(block), Mapping) else child_values(block)
        statements = tuple(values) if isinstance(values, (tuple, list)) else (values,)
        handlers, statements = split_handlers(statements)
        context = ast.Name("context", ast.Load())
        body = [ast.Expr(self.call("_tick", context, self.node_ref(block))), ast.Assign([ast.Name("last", ast.Store())], ast.Constant(None))]
        for index, statement in enumerate(statements):
            body.extend(self.emit_stmt(statement,
                                       value_context=value_context and index == len(statements) - 1))
        if handlers:
            catches = []
            if "error" in handlers:
                fallback = self.emit_block_function(handlers["error"])
                catches = [ast.ExceptHandler(ast.Name("_FatalErrors", ast.Load()), None, [ast.Raise()]),
                           ast.ExceptHandler(ast.Name("_Exception", ast.Load()), None,
                                             [ast.Assign([ast.Name("last", ast.Store())], self.call(fallback, context))])]
            final = []
            if "exit" in handlers:
                action = ast.Name(self.emit_block_function(handlers["exit"]), ast.Load())
                final = [ast.Expr(self.call("_cleanup", context, action))]
            body = [ast.Try(body, catches, [], final)]
        body.append(ast.Return(ast.Name("last", ast.Load())))
        self.functions.append(ast.FunctionDef(name, ast.arguments([], [ast.arg("context")], None, [], [], None, []), body, []))
        return name

    def emit_foreach(self, node: Any) -> list[ast.stmt]:
        iterable, block = child(node, "iterable", 0), child(node, "block", 1)
        index = self.counter
        self.counter += 1
        item, iterable_name, results = f"_item_{index}", f"_iter_{index}", f"_results_{index}"
        body_fn = self.emit_block_function(block)
        context = ast.Name("context", ast.Load())
        ordinal = f"_ordinal_{index}"
        target = ast.Tuple([ast.Name(ordinal, ast.Store()), ast.Name(item, ast.Store())], ast.Store())
        source = self.call("enumerate", ast.Name(iterable_name, ast.Load()))
        body = [
            ast.Expr(self.call("_check_items", context, self.node_ref(node), self.call("len", ast.Name(results, ast.Load())))),
            ast.Expr(self.call("_tick", context, self.node_ref(node))),
            ast.Expr(self.call("_push_loop_scope", context, self.node_ref(node), self.value_ref(getattr(node, "value", None)), ast.Name(item, ast.Load()), ast.Name(ordinal, ast.Load()))),
            ast.Try([ast.Assign([ast.Name("last", ast.Store())], self.call(body_fn, context))],
                    [ast.ExceptHandler(ast.Name("_LoopBreak", ast.Load()), None, [ast.Break()]),
                     ast.ExceptHandler(ast.Name("_LoopContinue", ast.Load()), None, [ast.Continue()])],
                    [], [ast.Expr(ast.Call(ast.Attribute(context, "pop_scope", ast.Load()), [], []))]),
            ast.Expr(ast.Call(ast.Attribute(ast.Name(results, ast.Load()), "append", ast.Load()), [ast.Name("last", ast.Load())], [])),
        ]
        return [
            ast.Expr(self.call("_tick", context, self.node_ref(node))),
            ast.Assign([ast.Name(iterable_name, ast.Store())], self.call("_iterable", context, self.node_ref(node), self.emit_expr(iterable))),
            ast.Assign([ast.Name(results, ast.Store())], ast.List([], ast.Load())),
            ast.For(target, source, body, []),
            ast.Assign([ast.Name("last", ast.Store())], ast.Name(results, ast.Load())),
        ]

    def emit_foreach_function(self, node: Any) -> str:
        name = f"_foreach_{self.counter}"
        self.counter += 1
        body = [*self.emit_foreach(node), ast.Return(ast.Name("last", ast.Load()))]
        self.functions.append(ast.FunctionDef(name, ast.arguments([], [ast.arg("context")], None, [], [], None, []), body, []))
        return name

    def emit_condition_loop(self, node: Any, *, collect: bool) -> list[ast.stmt]:
        index = self.counter
        self.counter += 1
        results, completed = f"_results_{index}", f"_completed_{index}"
        context, nref = ast.Name("context", ast.Load()), self.node_ref(node)
        body_fn = self.emit_block_function(child(node, "block", 1), value_context=collect)
        condition = self.call("_loop_condition", context, nref,
                              self.lambda0(self.emit_expr(child(node, "condition", 0))))
        body = [
            ast.Expr(self.call("_tick", context, nref)),
            ast.Expr(ast.Call(ast.Attribute(context, "push_scope", ast.Load()), [], [])),
            ast.Assign([ast.Name(completed, ast.Store())], ast.Constant(True)),
            ast.Try([ast.Assign([ast.Name("last", ast.Store())], self.call(body_fn, context))],
                    [ast.ExceptHandler(ast.Name("_LoopBreak", ast.Load()), None, [ast.Break()]),
                     ast.ExceptHandler(ast.Name("_LoopContinue", ast.Load()), None,
                                       [ast.Assign([ast.Name(completed, ast.Store())], ast.Constant(False))])],
                    [], [ast.Expr(ast.Call(ast.Attribute(context, "pop_scope", ast.Load()), [], []))]),
            ast.If(ast.Name(completed, ast.Load()),
                   [ast.Expr(self.call("_complete_loop_iteration", context, nref,
                                       ast.Name(results, ast.Load()), ast.Name("last", ast.Load())))], []),
        ]
        repeat = _kind(node) == "repeat"
        if repeat:
            body.append(ast.If(condition, [ast.Break()], []))
        return [
            ast.Expr(self.call("_tick", context, nref)),
            ast.Assign([ast.Name(results, ast.Store())], ast.List([], ast.Load()) if collect else ast.Constant(None)),
            ast.While(ast.Constant(True) if repeat else condition, body, []),
            ast.Assign([ast.Name("last", ast.Store())], ast.Name(results, ast.Load())),
        ]

    def emit_condition_loop_function(self, node: Any) -> str:
        name = f"_loop_{self.counter}"
        self.counter += 1
        body = [*self.emit_condition_loop(node, collect=True), ast.Return(ast.Name("last", ast.Load()))]
        self.functions.append(ast.FunctionDef(name, ast.arguments([], [ast.arg("context")], None, [], [], None, []), body, []))
        return name

    def emit_stmt(self, node: Any, *, value_context: bool = False) -> list[ast.stmt]:
        kind = _kind(node)
        context, nref = ast.Name("context", ast.Load()), self.node_ref(node)
        if kind == "observe":
            statement = child_values(node)[0]
            return [*self.emit_stmt(statement, value_context=value_context), ast.Expr(self.call("_observe", context, self.node_ref(statement), ast.Name("last", ast.Load())))]
        if kind == "flow":
            signal = "_LoopBreak" if node.value == "break" else "_LoopContinue"
            return [ast.Expr(self.call("_tick", context, nref)), ast.Raise(self.call(signal))]
        if kind == "foreach":
            return self.emit_foreach(node)
        if kind in {"while", "repeat"}:
            return self.emit_condition_loop(node, collect=value_context)
        if kind == "block":
            return [ast.Assign([ast.Name("last", ast.Store())], self.call("_run_scoped", context, ast.Name(self.emit_block_function(node), ast.Load())))]
        if kind == "let":
            expr = ast.Call(ast.Attribute(context, "define", ast.Load()), [ast.Constant(_name(node)), self.emit_expr(child(node, "expr", 0))], [])
        elif kind == "destructure":
            expr = self.call("_define_pattern", context, nref, self.emit_expr(child(node, "expr", 0)))
        elif kind == "runnable":
            expr = self.emit_runnable(node, "_define_runnable")
        elif kind == "assign":
            expr = self.emit_assignment(node)
        elif kind == "print":
            expr = self.call("_print", context, self.lambda0(self.emit_expr(child(node, "expr", 0))), nref)
        else:
            expr = self.emit_expr(node)
        prefix = [ast.Expr(self.call("_tick", context, nref))] if kind in {"let", "destructure", "runnable", "assign", "print"} else []
        return [*prefix, ast.Assign([ast.Name("last", ast.Store())], expr)]

    def module(self) -> ast.Module:
        if _kind(self.root) == "program":
            values = child(self.root, "statements", 0, ()) if isinstance(children(self.root), Mapping) else child_values(self.root)
            statements = tuple(values) if isinstance(values, (tuple, list)) else (values,)
        else:
            statements = (self.root,)
        main_body = [ast.Expr(self.call("_tick", ast.Name("context", ast.Load()), self.node_ref(self.root))), ast.Assign([ast.Name("last", ast.Store())], ast.Constant(None))]
        for statement in statements:
            main_body.extend(self.emit_stmt(statement))
        main_body.append(ast.Return(ast.Name("last", ast.Load())))
        main = ast.FunctionDef("_ctk_compiled_program", ast.arguments([], [ast.arg("context")], None, [], [], None, []), main_body, [])
        return ast.Module([*self.functions, main], [])


def compile_program(program: Node, *, cache_key: str | None = None,
                    cache_namespace: str = "libraries") -> Callable[[Context], Any]:
    from .library_cache import load_python, store_python

    artifact = (
        load_python(cache_key, program, namespace=cache_namespace)
        if cache_key is not None else None
    )
    if artifact is None:
        lowerer = _Lowerer(program)
        module = lowerer.module()
        ast.fix_missing_locations(module)
        source = ast.unparse(module)
        code = compile(module, "<ctk-prototype-compiled>", "exec")
        nodes, values = lowerer.nodes, lowerer.values
        if cache_key is not None:
            store_python(cache_key, program, source, code, nodes, values, namespace=cache_namespace)
    else:
        source, code, module, nodes, values = artifact
    namespace: dict[str, Any] = {
        "__builtins__": {}, "nodes": nodes, "values": values,
        "_tick": _tick, "_literal": _literal,
        "_host": host_value, "_observe": observe_statement, "_consume": consumed_value,
        "_make_list": _make_list,
        "_define_pattern": define_pattern,
        "_define_runnable": define_runnable, "_create_runnable": create_runnable,
        "_create_clauses": create_clause_runnable,
        "_recover": recover, "_cleanup": cleanup, "_FatalErrors": FATAL_ERRORS,
        "_Exception": Exception, "_LoopBreak": LoopBreak, "_LoopContinue": LoopContinue,
        "_make_dict": _make_dict, "_make_tuple": _make_tuple, "_get": _get, "_index": index_value, "_slice": _slice, "_iterable": _iterable,
        "_as_bool": _as_bool, "_binary": _binary, "_unary": _unary,
        "_predicate": _predicate, "_predicate_binding": _predicate_binding,
        "_call": _call, "_invoke": _invoke, "_pipe": _pipe, "_conditional": _conditional, "_run_scoped": _run_scoped,
        "_print": _print, "_assign_ref": _assign_ref, "_assign_index": _assign_index, "_assign_get": _assign_get,
        "_loop_condition": loop_condition, "_complete_loop_iteration": complete_loop_iteration,
        "_bad_target": _bad_target, "_check_items": _check_items, "len": len, "enumerate": enumerate,
        "_push_loop_scope": lambda context, node, pattern, item, ordinal: context.push_pattern_loop_scope(pattern, item, ordinal, node),
    }
    exec(code, namespace)
    function = namespace["_ctk_compiled_program"]
    function.__ctk_source__ = source
    function.__ctk_ast__ = module
    return function


__all__ = ["compile_program"]
