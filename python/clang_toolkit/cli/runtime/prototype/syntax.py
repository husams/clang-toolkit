"""Parser and immutable syntax tree for the experimental script runtime.

The prototype intentionally has no evaluator.  Keeping the syntax tree small
and regular makes it possible for the runtime and later tooling to share the
same parser without coupling this experiment to the released console.
"""

from __future__ import annotations

import ast as python_ast
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from lark import Lark, Token, Transformer, v_args
from lark.exceptions import VisitError
from .patterns import ConsPattern, ListPattern, pattern_names


@dataclass(frozen=True)
class Node:
    """A source-located, immutable prototype syntax node."""

    kind: str
    value: Any = None
    children: tuple[Node, ...] = ()
    line: int = 1
    column: int = 1
    source_span: tuple[int, int] | None = None


@dataclass(frozen=True)
class _Part:
    kind: str
    value: Any = None
    children: tuple[Node, ...] = ()
    line: int = 1
    column: int = 1


@dataclass(frozen=True)
class _Else:
    block: Node


_INT64_MAX = (1 << 63) - 1
_INT64_MIN_MAGNITUDE = 1 << 63


def _nodes(items: list[Any] | tuple[Any, ...]) -> tuple[Node, ...]:
    return tuple(item for item in items if isinstance(item, Node))


def _pattern_names(pattern: Any) -> tuple[str, ...]:
    return pattern_names(pattern)


@v_args(meta=True)
class _Builder(Transformer[Any, Any]):
    @staticmethod
    def _location(meta: Any, items: list[Any] | tuple[Any, ...]) -> tuple[int, int]:
        line = getattr(meta, "line", None)
        column = getattr(meta, "column", None)
        if line is not None and column is not None:
            return int(line), int(column)
        for item in items:
            if isinstance(item, Node):
                return item.line, item.column
        return 1, 1

    def start(self, meta: Any, items: list[Any]) -> Node:
        nodes = _nodes(items)
        return nodes[0] if nodes else Node("program")

    def empty_program(self, meta: Any, items: list[Any]) -> Node:
        line, column = self._location(meta, items)
        return Node("program", children=(), line=line, column=column)

    def program(self, meta: Any, items: list[Any]) -> Node:
        line, column = self._location(meta, items)
        return Node("program", children=_nodes(items), line=line, column=column)

    def separators(self, meta: Any, items: list[Any]) -> None:
        return None

    def soft_newlines(self, meta: Any, items: list[Any]) -> None:
        return None

    def let_stmt(self, meta: Any, items: list[Any]) -> Node:
        pattern, expression = items
        names = pattern_names(pattern.value)
        if len(set(names)) != len(names):
            raise ValueError("destructuring pattern has duplicate names")
        line, column = self._location(meta, items)
        if expression.kind == "clause_runnable" and isinstance(pattern.value, str):
            from dataclasses import replace
            expression = replace(expression, value=pattern.value)
        return Node("let" if isinstance(pattern.value, str) and pattern.value != "_" else "destructure",
                    value=pattern.value, children=(expression,), line=line, column=column)

    def print_stmt(self, meta: Any, items: list[Any]) -> Node:
        line, column = self._location(meta, items)
        return Node("print", children=(items[0],), line=line, column=column)

    def parameter(self, meta: Any, items: list[Any]) -> Node:
        line, column = self._location(meta, items)
        nodes = _nodes(items)
        pattern = nodes[0]
        return Node("parameter", pattern.value, nodes[1:], line, column,
                    (meta.start_pos, meta.end_pos))

    def name_pattern(self, meta: Any, items: list[Any]) -> Node:
        line, column = self._location(meta, items)
        return Node("pattern_name", str(items[0]), line=line, column=column)

    def discard_pattern(self, meta: Any, items: list[Any]) -> Node:
        line, column = self._location(meta, items)
        return Node("pattern_discard", "_", line=line, column=column)

    def empty_pattern(self, meta: Any, items: list[Any]) -> Node:
        line, column = self._location(meta, items)
        return Node("pattern_tuple", (), line=line, column=column)

    def tuple_single_pattern(self, meta: Any, items: list[Any]) -> Node:
        line, column = self._location(meta, items)
        return Node("pattern_tuple", tuple(item.value for item in _nodes(items)), line=line, column=column)

    def tuple_pattern(self, meta: Any, items: list[Any]) -> Node:
        line, column = self._location(meta, items)
        return Node("pattern_tuple", tuple(item.value for item in _nodes(items)), line=line, column=column)

    def grouped_pattern(self, meta: Any, items: list[Any]) -> Node:
        return _nodes(items)[0]

    def empty_list_pattern(self, meta: Any, items: list[Any]) -> Node:
        line, column = self._location(meta, items)
        return Node("pattern_list", ListPattern(()), line=line, column=column)

    def list_pattern(self, meta: Any, items: list[Any]) -> Node:
        line, column = self._location(meta, items)
        return Node("pattern_list", ListPattern(tuple(item.value for item in _nodes(items))), line=line, column=column)

    def cons_pattern(self, meta: Any, items: list[Any]) -> Node:
        head, tail = _nodes(items)
        return Node("pattern_cons", ConsPattern(head.value, tail.value), line=head.line, column=head.column)

    def clause_runnable(self, meta: Any, items: list[Any]) -> Node:
        clauses = _nodes(items)
        arities = {len(clause.value[1]) for clause in clauses}
        if len(arities) != 1:
            raise ValueError("function clauses must have the same arity")
        if any(len(clause.children) > 1 for clause in clauses):
            raise ValueError("function clauses cannot have defaults")
        line, column = self._location(meta, items)
        return Node("clause_runnable", "<inline>", clauses, line, column, (meta.start_pos, meta.end_pos))

    def parameters(self, meta: Any, items: list[Any]) -> tuple[Node, ...]:
        return _nodes(items)

    def runnable_definition(self, meta: Any, items: list[Any]) -> Node:
        return self._runnable(meta, items[1:], str(items[0]), "runnable")

    def inline_runnable(self, meta: Any, items: list[Any]) -> Node:
        return self._runnable(meta, items, "<inline>", "inline_runnable")

    def _runnable(self, meta: Any, items: list[Any], name: str, kind: str) -> Node:
        specs = next((item for item in items if isinstance(item, tuple)), ())
        parameters = tuple(item.value for item in specs)
        names = [parameter for pattern in parameters for parameter in _pattern_names(pattern)]
        if len(set(names)) != len(names):
            raise ValueError(f"{name} has duplicate parameter names")
        default_seen = False
        for item in specs:
            if item.children:
                if not isinstance(item.value, str):
                    raise ValueError(f"{name}: pattern parameters cannot have defaults")
                default_seen = True
            elif default_seen:
                raise ValueError(f"{name}: required parameters must precede defaults")
        body = self._action_block(next(item for item in items if isinstance(item, Node)))
        defaults = tuple(item for item in specs if item.children)
        line, column = self._location(meta, items)
        return Node(kind, (name, parameters), (body, *defaults), line, column,
                    (meta.start_pos, meta.end_pos))

    def error_handler(self, meta: Any, items: list[Any]) -> Node:
        line, column = self._location(meta, items)
        return Node("handler", "error", (self._action_block(items[0]),), line, column)

    def exit_handler(self, meta: Any, items: list[Any]) -> Node:
        line, column = self._location(meta, items)
        return Node("handler", "exit", (self._action_block(items[0]),), line, column)

    def handler_block(self, meta: Any, items: list[Any]) -> Node:
        return items[0]

    def break_stmt(self, meta: Any, items: list[Any]) -> Node:
        line, column = self._location(meta, items)
        return Node("flow", "break", (), line, column)

    def continue_stmt(self, meta: Any, items: list[Any]) -> Node:
        line, column = self._location(meta, items)
        return Node("flow", "continue", (), line, column)

    @staticmethod
    def _action_block(node: Node) -> Node:
        return node if node.kind == "block" else Node("block", children=(node,), line=node.line, column=node.column)

    def recovery_tail(self, meta: Any, items: list[Any]) -> Node:
        return Node("recovery_tail", children=(self._action_block(items[0]),))

    def recovery_expr(self, meta: Any, items: list[Any]) -> Node:
        nodes = _nodes(items)
        if len(nodes) == 2 and nodes[1].kind == "recovery_tail":
            return Node("recovery", children=(nodes[0], nodes[1].children[0]),
                        line=nodes[0].line, column=nodes[0].column)
        if len(nodes) == 1:
            return nodes[0]
        line, column = self._location(meta, items)
        return Node("recovery", children=nodes, line=line, column=column)

    def foreach_expr(self, meta: Any, items: list[Any]) -> Node:
        nodes = _nodes(items)
        pattern = nodes[0]
        names = _pattern_names(pattern.value)
        if len(set(names)) != len(names):
            raise ValueError("foreach tuple pattern has duplicate names")
        iterable, block = nodes[1:]
        line, column = self._location(meta, items)
        return Node("foreach", value=pattern.value, children=(iterable, block), line=line, column=column)

    def while_expr(self, meta: Any, items: list[Any]) -> Node:
        line, column = self._location(meta, items)
        return Node("while", children=_nodes(items), line=line, column=column)

    def repeat_expr(self, meta: Any, items: list[Any]) -> Node:
        body, condition = _nodes(items)
        line, column = self._location(meta, items)
        return Node("repeat", children=(condition, body), line=line, column=column)

    def assign_stmt(self, meta: Any, items: list[Any]) -> Node:
        target, operator, expression = items
        line, column = self._location(meta, items)
        return Node("assign", value=str(operator), children=(target, expression), line=line, column=column)

    def if_expr(self, meta: Any, items: list[Any]) -> Node:
        condition, block, *rest = items
        else_block = rest[0].block if rest else self._empty_block(meta)
        line, column = self._location(meta, items)
        return Node("conditional", children=(condition, block, else_block), line=line, column=column)

    def unless_expr(self, meta: Any, items: list[Any]) -> Node:
        condition, block, *rest = items
        negated = Node("unary", value="not", children=(condition,), line=condition.line, column=condition.column)
        else_block = rest[0].block if rest else self._empty_block(meta)
        line, column = self._location(meta, items)
        return Node("conditional", children=(negated, block, else_block), line=line, column=column)

    def conditional_single_body(self, meta: Any, items: list[Any]) -> Node:
        statement = next(item for item in items if isinstance(item, Node))
        line, column = self._location(meta, items)
        return Node("block", children=(statement,), line=line, column=column)

    def conditional_block_body(self, meta: Any, items: list[Any]) -> Node:
        return next(item for item in items if isinstance(item, Node))

    def if_else(self, meta: Any, items: list[Any]) -> _Else:
        blocks = [item for item in items if isinstance(item, Node)]
        if len(blocks) != 1:
            raise ValueError("conditional else requires exactly one body")
        return _Else(blocks[0])

    def single_else_body(self, meta: Any, items: list[Any]) -> Node:
        statement = next(item for item in items if isinstance(item, Node))
        line, column = self._location(meta, items)
        return Node("block", children=(statement,), line=line, column=column)

    def block_else_body(self, meta: Any, items: list[Any]) -> Node:
        return next(item for item in items if isinstance(item, Node))

    def statement_else_body(self, meta: Any, items: list[Any]) -> Node:
        statement = next(item for item in items if isinstance(item, Node))
        line, column = self._location(meta, items)
        return Node("block", children=(statement,), line=line, column=column)

    def single_body(self, meta: Any, items: list[Any]) -> Node:
        statement = next(item for item in items if isinstance(item, Node))
        line, column = self._location(meta, items)
        return Node("block", children=(statement,), line=line, column=column)

    def block_body(self, meta: Any, items: list[Any]) -> Node:
        return next(item for item in items if isinstance(item, Node))

    def block(self, meta: Any, items: list[Any]) -> Node:
        values = next((item for item in items if isinstance(item, tuple)), ())
        nodes = tuple(item for item in values if isinstance(item, Node))
        line, column = self._location(meta, items)
        return Node("block", children=nodes, line=line, column=column)

    def block_contents(self, meta: Any, items: list[Any]) -> tuple[Node, ...]:
        return _nodes(items)

    def conditional(self, meta: Any, items: list[Any]) -> Node:
        if len(items) == 1:
            return items[0]
        expressions = [item for item in items if isinstance(item, Node)]
        condition, true_expression, false_expression = expressions
        line, column = self._location(meta, items)
        true_block = self._expression_block(true_expression, line, column)
        false_block = self._expression_block(false_expression, line, column)
        return Node("conditional", children=(condition, true_block, false_block), line=line, column=column)

    def or_expr(self, meta: Any, items: list[Any]) -> Node:
        return self._fold_binary("or", items, meta)

    def and_expr(self, meta: Any, items: list[Any]) -> Node:
        return self._fold_binary("and", items, meta)

    def not_expr(self, meta: Any, items: list[Any]) -> Node:
        expression = next(item for item in items if isinstance(item, Node))
        line, column = self._location(meta, items)
        return Node("unary", value="not", children=(expression,), line=line, column=column)

    def comparison(self, meta: Any, items: list[Any]) -> Node:
        nodes = [item for item in items if isinstance(item, Node)]
        tails = [item for item in items if isinstance(item, _Part)]
        if not tails:
            return nodes[0]
        left = nodes[0]
        tail = tails[0]
        line, column = self._location(meta, items)
        if tail.kind == "comparison":
            return Node("binary", value=tail.value, children=(left, tail.children[0]), line=line, column=column)
        kind = str(tail.value)
        if kind in {"is_defined", "is_not_defined", "is_set", "is_not_set"} and left.kind != "ref":
            raise ValueError(f"{kind.replace('_', ' ')} requires a root variable reference at line {line}, column {column}")
        return Node("predicate", value=kind, children=(left, *tail.children), line=line, column=column)

    def comparison_tail(self, meta: Any, items: list[Any]) -> _Part:
        operator = next(item for item in items if isinstance(item, Token) and item.type == "COMPARE_OP")
        right = next(item for item in items if isinstance(item, Node))
        line, column = self._location(meta, items)
        return _Part("comparison", value=str(operator), children=(right,), line=line, column=column)

    def has_tail(self, meta: Any, items: list[Any]) -> _Part:
        key = next(item for item in items if isinstance(item, Node))
        return self._predicate_tail(meta, "has", (key,))

    def does_not_have_tail(self, meta: Any, items: list[Any]) -> _Part:
        key = next(item for item in items if isinstance(item, Node))
        return self._predicate_tail(meta, "does_not_have", (key,))

    def in_tail(self, meta: Any, items: list[Any]) -> _Part:
        right = next(item for item in items if isinstance(item, Node))
        return self._predicate_tail(meta, "in", (right,))

    def not_in_tail(self, meta: Any, items: list[Any]) -> _Part:
        right = next(item for item in items if isinstance(item, Node))
        return self._predicate_tail(meta, "not_in", (right,))

    def is_defined_tail(self, meta: Any, items: list[Any]) -> _Part:
        return self._predicate_tail(meta, "is_defined")

    def is_not_defined_tail(self, meta: Any, items: list[Any]) -> _Part:
        return self._predicate_tail(meta, "is_not_defined")

    def is_set_tail(self, meta: Any, items: list[Any]) -> _Part:
        return self._predicate_tail(meta, "is_set")

    def is_not_set_tail(self, meta: Any, items: list[Any]) -> _Part:
        return self._predicate_tail(meta, "is_not_set")

    def is_kind_tail(self, meta: Any, items: list[Any]) -> _Part:
        name = next(item for item in items if isinstance(item, Token) and item.type == "CNAME")
        line, column = self._location(meta, items)
        return self._predicate_tail(meta, "is_kind", (Node("literal", value=str(name), line=line, column=column),))

    def is_not_kind_tail(self, meta: Any, items: list[Any]) -> _Part:
        name = next(item for item in items if isinstance(item, Token) and item.type == "CNAME")
        line, column = self._location(meta, items)
        return self._predicate_tail(meta, "is_not_kind", (Node("literal", value=str(name), line=line, column=column),))

    def bare_key(self, meta: Any, items: list[Any]) -> Node:
        line, column = self._location(meta, items)
        return Node("literal", value=str(items[0]), line=line, column=column)

    @staticmethod
    def _predicate_tail(meta: Any, kind: str, children: tuple[Node, ...] = ()) -> _Part:
        line, column = _Builder._location(meta, children)
        return _Part("predicate", value=kind, children=children, line=line, column=column)

    def additive(self, meta: Any, items: list[Any]) -> Node:
        return self._fold_operator("binary", items, meta)

    def multiplicative(self, meta: Any, items: list[Any]) -> Node:
        return self._fold_operator("binary", items, meta)

    def unary_expr(self, meta: Any, items: list[Any]) -> Node:
        operator, expression = items
        magnitude = expression.value if expression.kind == "literal" and isinstance(expression.value, int) else None
        if str(operator) == "-" and magnitude == _INT64_MIN_MAGNITUDE:
            line, column = self._location(meta, items)
            return Node("literal", value=-_INT64_MIN_MAGNITUDE, line=line, column=column)
        if magnitude is not None:
            if str(operator) == "-" and magnitude > _INT64_MIN_MAGNITUDE:
                self._range_error(meta, "integer literal is outside signed 64-bit range")
            if str(operator) == "+" and magnitude > _INT64_MAX:
                self._range_error(meta, "integer literal is outside signed 64-bit range")
        line, column = self._location(meta, items)
        return Node("unary", value=str(operator), children=(expression,), line=line, column=column)

    def postfix(self, meta: Any, items: list[Any]) -> Node:
        result = items[0]
        for part in items[1:]:
            if not isinstance(part, _Part):
                continue
            if part.kind == "member":
                result = Node("get", value=part.value, children=(result,), line=part.line, column=part.column)
            elif part.kind == "index":
                result = Node("index", children=(result, part.children[0]), line=part.line, column=part.column)
            elif part.kind == "call":
                result = Node("invoke", children=(result, *part.children), line=part.line, column=part.column)
        return result

    def call_suffix(self, meta: Any, items: list[Any]) -> _Part:
        line, column = self._location(meta, items)
        arguments = next((item for item in items if isinstance(item, tuple)), ())
        return _Part("call", children=arguments, line=line, column=column)

    def member_part(self, meta: Any, items: list[Any]) -> _Part:
        line, column = self._location(meta, items)
        name = next(item for item in items if isinstance(item, Token) and item.type == "CNAME")
        return _Part("member", value=str(name), line=line, column=column)

    def index_part(self, meta: Any, items: list[Any]) -> _Part:
        expression = next(item for item in items if isinstance(item, Node))
        line, column = self._location(meta, items)
        return _Part("index", children=(expression,), line=line, column=column)

    def target(self, meta: Any, items: list[Any]) -> Node:
        result = items[0]
        for part in items[1:]:
            if not isinstance(part, _Part):
                continue
            if part.kind == "member":
                result = Node("get", value=part.value, children=(result,), line=part.line, column=part.column)
            else:
                result = Node("index", children=(result, part.children[0]), line=part.line, column=part.column)
        return result

    def target_member_part(self, meta: Any, items: list[Any]) -> _Part:
        return self.member_part(meta, items)

    def reference(self, meta: Any, items: list[Any]) -> Node:
        line, column = self._location(meta, items)
        return Node("ref", value=str(items[0]), line=line, column=column)

    def named_call(self, meta: Any, items: list[Any]) -> Node:
        name = str(items[0])
        arguments = next((item for item in items[1:] if isinstance(item, tuple)), ())
        line, column = self._location(meta, items)
        return Node("call", value=name, children=arguments, line=line, column=column)

    def keyword_argument(self, meta: Any, items: list[Any]) -> Node:
        name = next(str(item) for item in items if isinstance(item, Token) and item.type == "CNAME")
        expression = next(item for item in items if isinstance(item, Node))
        line, column = self._location(meta, items)
        return Node("keyword_arg", name, (expression,), line, column)

    def pipe_expr(self, meta: Any, items: list[Any]) -> Node:
        nodes = _nodes(items)
        recovery = nodes[-1] if nodes and nodes[-1].kind == "recovery_tail" else None
        if recovery is not None:
            nodes = nodes[:-1]
        if len(nodes) == 1:
            expression = nodes[0]
        else:
            line, column = self._location(meta, items)
            expression = Node("pipe", children=nodes, line=line, column=column)
        if recovery is not None:
            return Node("recovery", children=(expression, recovery.children[0]),
                        line=expression.line, column=expression.column)
        return expression

    def arguments(self, meta: Any, items: list[Any]) -> tuple[Node, ...]:
        return _nodes(items)

    def index_expression(self, meta: Any, items: list[Any]) -> _Part:
        expression = next(item for item in items if isinstance(item, Node))
        line, column = self._location(meta, items)
        return _Part("index", children=(expression,), line=line, column=column)

    def slice_bound(self, meta: Any, items: list[Any]) -> Node:
        line, column = self._location(meta, items)
        return next((item for item in items if isinstance(item, Node)),
                    Node("omitted", line=line, column=column))

    def slice_expression(self, meta: Any, items: list[Any]) -> _Part:
        line, column = self._location(meta, items)
        bounds = _nodes(items)
        if len(bounds) == 2:
            bounds += (Node("omitted", line=line, column=column),)
        return _Part("index", children=(Node("slice", children=bounds,
                                            line=line, column=column),),
                     line=line, column=column)

    def grouped_expression(self, meta: Any, items: list[Any]) -> Node:
        return next(item for item in items if isinstance(item, Node))

    def empty_tuple(self, meta: Any, items: list[Any]) -> Node:
        line, column = self._location(meta, items)
        return Node("tuple", children=(), line=line, column=column)

    def tuple_items(self, meta: Any, items: list[Any]) -> Node:
        line, column = self._location(meta, items)
        return Node("tuple", children=_nodes(items), line=line, column=column)

    def tuple_singleton(self, meta: Any, items: list[Any]) -> Node:
        line, column = self._location(meta, items)
        return Node("tuple", children=_nodes(items), line=line, column=column)

    def inner_expression(self, meta: Any, items: list[Any]) -> Node:
        return next(item for item in items if isinstance(item, Node))

    def list_literal(self, meta: Any, items: list[Any]) -> Node:
        values = next((item for item in items if isinstance(item, tuple)), ())
        line, column = self._location(meta, items)
        return Node("list", children=values, line=line, column=column)

    def list_items(self, meta: Any, items: list[Any]) -> tuple[Node, ...]:
        return _nodes(items)

    def dict_literal(self, meta: Any, items: list[Any]) -> Node:
        entries = next((item for item in items if isinstance(item, tuple)), ())
        line, column = self._location(meta, items)
        return Node("dict", children=entries, line=line, column=column)

    def dict_items(self, meta: Any, items: list[Any]) -> tuple[Node, ...]:
        return _nodes(items)

    def dict_item(self, meta: Any, items: list[Any]) -> Node:
        key, expression = items
        key_value = self._decode_key(key)
        line, column = self._location(meta, items)
        return Node("entry", value=key_value, children=(expression,), line=line, column=column)

    def integer_literal(self, meta: Any, items: list[Any]) -> Node:
        value = int(items[0])
        if value > _INT64_MIN_MAGNITUDE:
            self._range_error(meta, "integer literal is outside signed 64-bit range")
        line, column = self._location(meta, items)
        return Node("literal", value=value, line=line, column=column)

    def float_literal(self, meta: Any, items: list[Any]) -> Node:
        value = float(items[0])
        if not math.isfinite(value):
            self._range_error(meta, "floating-point literal must be finite")
        line, column = self._location(meta, items)
        return Node("literal", value=value, line=line, column=column)

    def string_literal(self, meta: Any, items: list[Any]) -> Node:
        value = python_ast.literal_eval(str(items[0]))
        line, column = self._location(meta, items)
        return Node("literal", value=value, line=line, column=column)

    def predicate_string_literal(self, meta: Any, items: list[Any]) -> Node:
        value = python_ast.literal_eval(str(items[0]))
        line, column = self._location(meta, items)
        return Node("literal", value=value, line=line, column=column)

    def true_literal(self, meta: Any, items: list[Any]) -> Node:
        line, column = self._location(meta, items)
        return Node("literal", value=True, line=line, column=column)

    def false_literal(self, meta: Any, items: list[Any]) -> Node:
        line, column = self._location(meta, items)
        return Node("literal", value=False, line=line, column=column)

    def null_literal(self, meta: Any, items: list[Any]) -> Node:
        line, column = self._location(meta, items)
        return Node("literal", value=None, line=line, column=column)

    @staticmethod
    def _decode_key(key: Any) -> str:
        text = str(key)
        if text[:1] in {"'", '"'}:
            value = python_ast.literal_eval(text)
            if not isinstance(value, str):
                raise ValueError("dictionary keys must be strings")
            return value
        return text

    @classmethod
    def _empty_block(cls, meta: Any) -> Node:
        return Node("block", children=(), line=int(getattr(meta, "line", 1)), column=int(getattr(meta, "column", 1)))

    @staticmethod
    def _expression_block(expression: Node, line: int, column: int) -> Node:
        return Node("block", children=(expression,), line=line, column=column)

    @staticmethod
    def _fold_binary(operator: str, items: list[Any], meta: Any) -> Node:
        nodes = [item for item in items if isinstance(item, Node)]
        result = nodes[0]
        for right in nodes[1:]:
            line, column = _Builder._location(meta, (result, right))
            result = Node("binary", value=operator, children=(result, right), line=line, column=column)
        return result

    @staticmethod
    def _fold_operator(kind: str, items: list[Any], meta: Any) -> Node:
        nodes = [item for item in items if isinstance(item, Node)]
        operators = [
            item for item in items
            if isinstance(item, Token) and item.type in {"ADD_OP", "MUL_OP"}
        ]
        result = nodes[0]
        for operator, right in zip(operators, nodes[1:]):
            line, column = _Builder._location(meta, (result, right))
            result = Node(kind, value=str(operator), children=(result, right), line=line, column=column)
        return result

    @staticmethod
    def _range_error(meta: Any, message: str) -> None:
        line = int(getattr(meta, "line", 1))
        column = int(getattr(meta, "column", 1))
        raise ValueError(f"{message} at line {line}, column {column}")


_GRAMMAR = Path(__file__).with_name("grammar.lark").read_text(encoding="utf-8")
_PARSER = Lark(
    _GRAMMAR,
    # Earley is used here because an optional newline before ``else`` must be
    # distinguishable from an ordinary statement separator. Its matched/open
    # grammar also makes nearest-else binding explicit.
    parser="earley",
    lexer="dynamic_complete",
    ambiguity="resolve",
    propagate_positions=True,
    maybe_placeholders=False,
)



def parse(source: str) -> Node:
    """Parse *source* into a ``program`` node.

    ``Lark`` exceptions are intentionally allowed through unchanged so callers
    retain the original line and column diagnostics for malformed input.
    """

    tree = _PARSER.parse(source)
    try:
        result = _Builder().transform(tree)
        _validate_integer_ranges(result)
        _validate_control_scope(result)
        return result
    except VisitError as error:
        # Transformer failures are normally wrapped by Lark.  Range and
        # literal validation are parser-level semantic diagnostics, so expose
        # their original exception while leaving syntax exceptions untouched.
        if isinstance(error.orig_exc, ValueError):
            raise error.orig_exc from None
        raise


__all__ = ["Node", "parse"]


def _validate_integer_ranges(node: Node, *, unary_minus_operand: bool = False) -> None:
    """Allow ``2**63`` only as the operand of unary minus.

    Keeping that one spelling available until the parent is known is what
    permits the signed minimum literal while still rejecting a positive
    out-of-range integer.
    """

    if node.kind == "host":
        def visit_host(tree: Any) -> None:
            for child in getattr(tree, "children", ()):
                if isinstance(child, Node):
                    _validate_integer_ranges(child)
                else:
                    visit_host(child)
        visit_host(node.value[0])
    if node.kind == "literal" and isinstance(node.value, int) and not isinstance(node.value, bool):
        if node.value > _INT64_MAX and not unary_minus_operand:
            raise ValueError(
                f"integer literal is outside signed 64-bit range at line {node.line}, column {node.column}"
            )
        return
    if node.kind == "unary" and node.value in {"+", "-"} and node.children:
        child = node.children[0]
        value = _static_integer(node)
        if value is not None and (value < -(1 << 63) or value > _INT64_MAX):
            raise ValueError(
                f"integer literal is outside signed 64-bit range at line {node.line}, column {node.column}"
            )
        _validate_integer_ranges(child, unary_minus_operand=node.value == "-")
        return
    for child in node.children:
        _validate_integer_ranges(child)


def _static_integer(node: Node) -> int | None:
    if node.kind == "literal" and isinstance(node.value, int) and not isinstance(node.value, bool):
        return node.value
    if node.kind == "unary" and node.value in {"+", "-"} and node.children:
        value = _static_integer(node.children[0])
        if value is not None:
            return value if node.value == "+" else -value
    return None


def _validate_control_scope(node: Node, *, loops: int = 0) -> None:
    """Validate handler placement and loop control before any effects run."""
    if node.kind == "handler":
        raise ValueError(f"on {node.value} is only valid at the beginning of a block (line {node.line})")
    if node.kind == "flow":
        if not loops:
            raise ValueError(f"{node.value} requires an enclosing foreach, while or repeat loop (line {node.line}, column {node.column})")
        return
    if node.kind in {"runnable", "inline_runnable"}:
        loops = 0
    if node.kind in {"foreach", "while", "repeat"}:
        _validate_control_scope(node.children[0], loops=loops)
        _validate_control_scope(node.children[1], loops=loops + 1)
        return
    if node.kind == "block":
        started = False
        handlers = set()
        for child in node.children:
            if child.kind == "handler":
                if started or child.value in handlers:
                    raise ValueError(f"on {child.value} must appear once at the beginning of a block (line {child.line})")
                handlers.add(child.value)
                _validate_control_scope(child.children[0], loops=loops)
            else:
                started = True
                _validate_control_scope(child, loops=loops)
        return
    if node.kind == "host":
        def visit_host(tree: Any, host_loops: int) -> None:
            if str(getattr(tree, "data", "")) in {"batch_statement", "durable_batch"}:
                host_loops = 0
            for child in getattr(tree, "children", ()):
                if isinstance(child, Node):
                    _validate_control_scope(child, loops=host_loops)
                else:
                    visit_host(child, host_loops)
        visit_host(node.value[0], loops)
    for child in node.children:
        _validate_control_scope(child, loops=loops)
