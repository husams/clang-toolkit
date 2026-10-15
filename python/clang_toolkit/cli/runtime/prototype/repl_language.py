"""Combined parser for prototype expressions and the existing CTK REPL language.

Prototype syntax is compiled into the immutable prototype ``Node`` IR. Existing
CTK statements and command expressions remain their original Lark trees inside
``Node(kind="host", value=(tree, mode))`` leaves so the session layer can hand
them to the established evaluator without rewriting their syntax.
"""

from __future__ import annotations

import re
from functools import cache
from pathlib import Path
from typing import Any

from lark import Lark, Token, Tree
from lark.exceptions import VisitError

from .syntax import Node, _Builder, _validate_integer_ranges
from clang_toolkit.cli.matcher_catalog import SCRIPT_BUILTIN_MATCHERS

_PROTOTYPE_GRAMMAR = Path(__file__).with_name("grammar.lark")
_LEGACY_GRAMMAR = Path(__file__).resolve().parents[2] / "grammar.lark"
_PREFIX = "legacy_"
_PROTO_PREFIX = "proto_"
_IDENTIFIER = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z_][A-Za-z0-9_]*)(?![A-Za-z0-9_])")


def _prefix_grammar(source: str, prefix: str, *, prefix_aliases: bool = False) -> str:
    """Prefix grammar symbols without changing literals, regexes, or aliases."""
    output: list[str] = []
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("//"):
            output.append(line)
            continue
        if stripped.startswith("%import "):
            match = re.fullmatch(r"%import common\.([A-Z_]+)", stripped)
            if match:
                output.append(f"%import common.{match.group(1)} -> {prefix.upper()}{match.group(1)}")
            else:
                output.append(line)
            continue
        if stripped.startswith("%ignore "):
            name = stripped.removeprefix("%ignore ").strip()
            output.append(line if name.startswith("/") else f"%ignore {prefix.upper()}{name}")
            continue

        chars: list[str] = []
        index = 0
        alias_tail = False
        while index < len(line):
            char = line[index]
            if char in "\"'":
                end = index + 1
                while end < len(line):
                    if line[end] == "\\":
                        end += 2
                    elif line[end] == char:
                        end += 1
                        break
                    else:
                        end += 1
                chars.append(line[index:end])
                index = end
                continue
            if char == "/":
                if line.startswith("//", index):
                    chars.append(line[index:])
                    break
                end = index + 1
                while end < len(line):
                    if line[end] == "\\":
                        end += 2
                    elif line[end] == "/":
                        end += 1
                        break
                    else:
                        end += 1
                while end < len(line) and line[end].isalpha():
                    end += 1
                chars.append(line[index:end])
                index = end
                continue
            if line.startswith("->", index):
                alias_tail = True
                chars.append("->")
                index += 2
                continue
            if char.isalpha() or char == "_":
                end = index + 1
                while end < len(line) and (line[end].isalnum() or line[end] == "_"):
                    end += 1
                word = line[index:end]
                symbol_prefix = prefix.upper() if word[0].isupper() else prefix
                chars.append((prefix + word if prefix_aliases else word) if alias_tail else symbol_prefix + word)
                index = end
                continue
            chars.append(char)
            index += 1
        output.append("".join(chars))
    return "\n".join(output)


def _combined_grammar() -> str:
    proto_source = _PROTOTYPE_GRAMMAR.read_text(encoding="utf-8")
    # A dollar sign is optional on the iterator to retain existing CTK style.
    proto_source = proto_source.replace(
        'closed_foreach_expr.10: "foreach" pattern PRED_IN',
        'closed_foreach_expr.10: "foreach" "$"? pattern PRED_IN',
    )
    proto_source = proto_source.replace(
        'open_foreach_expr.10: "foreach" pattern PRED_IN',
        'open_foreach_expr.10: "foreach" "$"? pattern PRED_IN',
    )
    # Let and print priorities are defined by the standalone grammar.
    proto_source = proto_source.replace(
        'postfix_part: soft_newlines "." soft_newlines CNAME -> member_part',
        'postfix_part: soft_newlines "." soft_newlines MEMBER_NAME -> member_part',
    )
    proto_source = proto_source.replace(
        'target_part: "." CNAME       -> target_member_part',
        'target_part: "." MEMBER_NAME       -> target_member_part',
    )
    proto_source = proto_source.replace(
        'CNAME: /[A-Za-z_][A-Za-z0-9_]*/',
        'MEMBER_NAME: /(?!(?:hasField|fieldState|fieldOr|joinWith|unique|sort|filter|push|pop|delete|set|insert|remove|clear)\\s*\\()[A-Za-z_][A-Za-z0-9_]*/\nCNAME: /[A-Za-z_][A-Za-z0-9_]*/',
    )
    builtin_matcher_names = "|".join(re.escape(name) for name in sorted(SCRIPT_BUILTIN_MATCHERS))
    matcher_names = "|".join(re.escape(name) for name in sorted(
        SCRIPT_BUILTIN_MATCHERS | {"glob"}))
    proto_source = proto_source.replace(
        'named_call: CNAME "(" arguments? ")"',
        'named_call: ROUTINE_NAME "(" arguments? ")"\n'
        + r'ROUTINE_NAME.20: /(?!(?:' + matcher_names + r')\s*\()[A-Za-z_][A-Za-z0-9_]*(?=\s*\()/',
    )
    # Leave command syntax in the released grammar; expose native commands as
    # opaque leaves while ordinary assignments/displays/loops use prototype IR.
    legacy_source = _prefix_grammar(_LEGACY_GRAMMAR.read_text(encoding="utf-8"), _PREFIX)
    proto_source = _prefix_grammar(proto_source, _PROTO_PREFIX, prefix_aliases=True)
    legacy_source = legacy_source.replace("legacy_reference:", "legacy_reference.10:")
    legacy_source = legacy_source.replace("?legacy_command_expression:", "?legacy_command_expression.10:")
    legacy_source = legacy_source.replace(
        "| LEGACY_PRINT legacy_value_expression [LEGACY_TO legacy_output_path [LEGACY_MODE (LEGACY_REPLACE | LEGACY_APPEND)]] -> print",
        "| LEGACY_PRINT legacy_value_expression LEGACY_TO legacy_output_path [LEGACY_MODE (LEGACY_REPLACE | LEGACY_APPEND)] -> print",
    )
    proto_source = proto_source.replace(
        "?proto_closed_statement: proto_let_stmt",
        "?proto_closed_statement: legacy_statement -> host_statement\n"
        "                  | proto_let_stmt",
    )
    legacy_source = legacy_source.replace(
        "legacy_editor_start: (legacy_editor_token | proto_editor_token)*",
        "legacy_editor_start: (legacy_editor_token | proto_editor_token)*",
    )
    legacy_source = legacy_source.replace(
        "?legacy_statement: legacy_assignment\n          | legacy_matcher_definition\n          | legacy_command_expression\n          | legacy_collection_command\n          | LEGACY_QUIT                            -> quit\n          | LEGACY_EXIT                            -> exit\n          | legacy_display_expression              -> display",
        "?legacy_statement: legacy_matcher_definition\n          | legacy_command_expression\n          | legacy_collection_command\n          | LEGACY_QUIT                            -> quit\n          | LEGACY_EXIT                            -> exit",
    )
    proto_source = proto_source.replace(
        "?proto_postfix: proto_atom proto_postfix_part*\n",
        "?proto_postfix: proto_atom proto_postfix_part*\n              | proto_host_atom\n",
    )
    proto_source = proto_source.replace(
        "proto_named_call: PROTO_ROUTINE_NAME",
        """?proto_host_atom: legacy_reference LEGACY_DOT legacy_method_call -> host_expression
                | legacy_root_matcher -> host_expression
                | legacy_command_expression -> host_expression
                | legacy_collection_command -> host_expression
                | legacy_glob_call -> host_expression
                | legacy_parse_expression -> host_expression
                | legacy_read_expression -> host_expression
                | legacy_file_set_expression -> host_expression
                | legacy_analysis_block -> host_expression
                | legacy_pop_expression -> host_expression
                | legacy_split_expression -> host_expression
                | legacy_join_expression -> host_expression
                | legacy_flatten_expression -> host_expression
                | legacy_bare_access -> host_expression

proto_named_call: PROTO_ROUTINE_NAME""",
    )
    return "\n".join(
        (
            legacy_source,
            proto_source,
            # The legacy LALR parser removes expression newlines in its
            # postlexer. Earley's dynamic lexer cannot use that postlexer, so
            # preserve matcher continuation here as formal grammar rules.
            # Hidden newline tokens retain source positions without changing
            # the host trees consumed by the legacy evaluator.
            r"""
_host_newlines: _HOST_NEWLINE*
_HOST_NEWLINE: /\r?\n/

%override legacy_reference: LEGACY_DOLLAR? LEGACY_NAME (LEGACY_DOT legacy_property_name | LEGACY_DOT legacy_method_call | LEGACY_LSQB legacy_index_expression LEGACY_RSQB)*

%override legacy_batch_statement: LEGACY_BATCH LEGACY_NAME LEGACY_IN legacy_reference legacy_batch_grouping legacy_batch_option* LEGACY_DO proto_block -> compiled_batch_statement
               | (LEGACY_DURABLE | LEGACY_BACKGROUND) LEGACY_BATCH LEGACY_NAME LEGACY_IN legacy_reference legacy_batch_grouping legacy_durable_batch_option* LEGACY_DO legacy_statement_block -> durable_batch
               | LEGACY_BATCH LEGACY_STATUS legacy_reference -> batch_status
               | LEGACY_BATCH LEGACY_CANCEL legacy_reference -> batch_cancel
               | LEGACY_BATCH LEGACY_RESUME legacy_reference -> batch_resume
               | LEGACY_BATCH LEGACY_RETRY legacy_reference -> batch_retry
               | LEGACY_BATCH LEGACY_PROMOTE legacy_reference -> batch_promote

%override legacy_matcher_definition.30: LEGACY_LET LEGACY_NAME LEGACY_LPAR _host_newlines [legacy_parameters] _host_newlines LEGACY_RPAR LEGACY_EQUAL legacy_definition_matcher
legacy_definition_matcher: LEGACY_DEFINITION_MATCHER_NAME LEGACY_LPAR _host_newlines [legacy_arguments] _host_newlines LEGACY_RPAR legacy_bind? -> matcher
%override legacy_parameters: LEGACY_NAME (_host_newlines LEGACY_COMMA _host_newlines LEGACY_NAME)*
%override legacy_root_matcher: LEGACY_ROOT_MATCHER_NAME LEGACY_LPAR _host_newlines [legacy_arguments] _host_newlines LEGACY_RPAR legacy_bind? -> matcher
%override legacy_nested_matcher: LEGACY_MATCHER_NAME _host_newlines LEGACY_LPAR _host_newlines [legacy_arguments] _host_newlines LEGACY_RPAR legacy_bind? -> matcher
%override legacy_arguments: legacy_argument (_host_newlines LEGACY_COMMA _host_newlines legacy_argument)*
%override legacy_bind: LEGACY_BIND LEGACY_LPAR _host_newlines LEGACY_STRING _host_newlines LEGACY_RPAR
%override legacy_target_matcher: LEGACY_NAME LEGACY_LPAR _host_newlines [legacy_target_arguments] _host_newlines LEGACY_RPAR legacy_bind? -> matcher
%override legacy_target_arguments: legacy_target_expression (_host_newlines LEGACY_COMMA _host_newlines legacy_target_expression)*
""",
            'LEGACY_DEFINITION_MATCHER_NAME: /(?:' + builtin_matcher_names + r')(?=\s*\()/',
            """
repl_start: proto_start
editor_start: (legacy_editor_token | proto_editor_token)*
proto_editor_token: PROTO_ROUTINE_NAME | PROTO_ASSIGN_OP | PROTO_COMPARE_OP | PROTO_ADD_OP | PROTO_MUL_OP | PROTO_UNARY_OP | PROTO_FLOAT | PROTO_INT | PROTO_STRING | PROTO_PREDICATE_STRING | PROTO_PRED_AND | PROTO_PRED_OR | PROTO_MEMBER_NAME | PROTO_CNAME | PROTO_NEWLINE
""",
        )
    )


@cache
def grammar_text() -> str:
    """Return the formal combined grammar for parser and editor consumers."""
    return _combined_grammar()


@cache
def parser() -> Lark:
    """Build the combined parser once, preserving source locations."""
    return Lark(
        grammar_text(),
        parser="earley",
        lexer="dynamic_complete",
        ambiguity="resolve",
        start="repl_start",
        propagate_positions=True,
        maybe_placeholders=False,
    )


def _normalize_host_tree(tree: Tree[Any]) -> Tree[Any]:
    """Restore the legacy parser's original token names inside opaque leaves."""
    children = [
        _normalize_host_tree(child)
        if isinstance(child, Tree)
        else Token.new_borrow_pos(child.type.removeprefix("LEGACY_"), str(child), child)
        if isinstance(child, Token) and child.type.startswith("LEGACY_")
        else child
        for child in tree.children
    ]
    if str(tree.data) == "reference" and children and str(children[0]) != "$":
        children.insert(0, Token.new_borrow_pos("DOLLAR", "$", children[0]))
    return Tree(tree.data, children, meta=tree.meta)


class _CombinedBuilder(_Builder):
    def __default__(self, data: str, children: list[Any], meta: Any) -> Any:
        if data == "compiled_batch_statement":
            children = [Tree("statement_block", [item], meta=meta)
                        if isinstance(item, Node) else item for item in children]
            return _normalize_host_tree(Tree("batch_statement", children, meta=meta))
        if data == "proto_string_literal":
            token = next(item for item in children if isinstance(item, Token))
            string_token = Token.new_borrow_pos("STRING", str(token), token)
            tree = Tree("display", [string_token])
            return Node(
                "host",
                value=(tree, "expression"),
                line=int(getattr(meta, "line", 1)),
                column=int(getattr(meta, "column", 1)),
            )
        if data == "host_statement":
            tree = _normalize_host_tree(next(item for item in children if isinstance(item, Tree)))
            return Node(
                "host",
                value=(tree, "statement"),
                line=int(getattr(meta, "line", 1)),
                column=int(getattr(meta, "column", 1)),
            )
        if data == "host_expression":
            tree_items = [item for item in children if isinstance(item, Tree)]
            tree = tree_items[0]
            if tree.data == "reference" and len(tree_items) > 1:
                combined = list(tree.children)
                seen_first = False
                for item in children:
                    if item is tree and not seen_first:
                        seen_first = True
                        continue
                    combined.append(item)
                tree = Tree("reference", combined, meta=tree.meta)
            tree = _normalize_host_tree(tree)
            return Node(
                "host",
                value=(tree, "expression"),
                line=int(getattr(meta, "line", 1)),
                column=int(getattr(meta, "column", 1)),
            )
        if data.startswith(_PROTO_PREFIX):
            method = getattr(_Builder, data[len(_PROTO_PREFIX):], None)
            if method is not None:
                normalized = [
                    Token.new_borrow_pos("CNAME" if item.type == "PROTO_MEMBER_NAME" else item.type.removeprefix("PROTO_"), str(item), item)
                    if isinstance(item, Token) and item.type.startswith("PROTO_")
                    else item
                    for item in children
                ]
                return method(self, meta, normalized)
            return Tree(data[len(_PROTO_PREFIX):], children, meta=meta)
        if data.startswith(_PREFIX):
            return Tree(data[len(_PREFIX):], children, meta=meta)
        if data == "repl_start":
            nodes = tuple(item for item in children if isinstance(item, Node))
            return nodes[0] if nodes else Node("program")
        return super().__default__(data, children, meta)


def parse(source: str) -> Node:
    """Parse a complete REPL script into prototype nodes plus host leaves.

    Syntax and transformer errors are reported directly; the adapter never
    retries a failed parse through the legacy parser.
    """
    tree = parser().parse(source)
    try:
        result = _CombinedBuilder().transform(tree)
        if not isinstance(result, Node):
            raise TypeError("combined REPL parser did not produce a prototype node")
        _validate_integer_ranges(result)
        from .syntax import _validate_control_scope

        _validate_control_scope(result)
        _validate_host_control_scope(result)
        return result
    except VisitError as error:
        if isinstance(error.orig_exc, ValueError):
            raise error.orig_exc from None
        raise


def _validate_host_control_scope(program: Node) -> None:
    controls = {"quit", "exit", "help", "help_shortcut"}

    def visit(node: Node, *, top_level: bool) -> None:
        if node.kind == "host":
            tree, _mode = node.value
            if not top_level and str(tree.data) in controls:
                raise ValueError(
                    f"{tree.data} is only valid as a top-level REPL command "
                    f"(line {node.line}, column {node.column})"
                )
            return
        for child in node.children:
            visit(child, top_level=False)

    for child in program.children:
        visit(child, top_level=True)


__all__ = ["Node", "grammar_text", "parse", "parser"]
