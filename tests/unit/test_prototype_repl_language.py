"""Composition tests for the compiled prototype and released REPL grammar."""

from __future__ import annotations

from lark import Tree
from lark.exceptions import UnexpectedInput
import pytest

from clang_toolkit.cli.runtime.prototype.repl_language import (
    grammar_text,
    parse,
    parser,
)
from clang_toolkit.cli.runtime.prototype.syntax import Node


def _host(node: Node) -> tuple[Tree, str]:
    assert node.kind == "host"
    tree, mode = node.value
    assert isinstance(tree, Tree)
    return tree, mode


def test_adapter_exposes_cached_composed_grammar_and_parser() -> None:
    assert "editor_start: (legacy_editor_token | proto_editor_token)*" in grammar_text()
    assert parser() is parser()


def test_plain_prototype_expressions_and_multiline_blocks_build_ir() -> None:
    program = parse(
        "let count = 2\n"
        "let total = $count * 3 + 1\n"
        "if $total == 7 do {\n"
        "  let label = {count: $total, text: true ? \"ok\" : \"bad\"}\n"
        "  print $label\n"
        "}"
    )

    assert program.kind == "program"
    assert [node.kind for node in program.children] == ["let", "let", "conditional"]
    branch = program.children[2].children[1]
    assert [node.kind for node in branch.children] == ["let", "print"]


def test_host_commands_remain_untransformed_leaves_at_top_level() -> None:
    program = parse("server status\nmatch functionDecl()\nhelp\nquit")
    assert [node.kind for node in program.children] == ["host"] * 4
    assert [(_host(node)[0].data, _host(node)[1]) for node in program.children] == [
        ("server_status", "statement"),
        ("match", "statement"),
        ("help", "statement"),
        ("quit", "statement"),
    ]
    match_tree, _ = _host(program.children[1])
    matcher = match_tree.children[1]
    assert isinstance(matcher, Tree)
    assert matcher.data == "matcher"


def test_native_match_command_can_live_inside_prototype_control_flow() -> None:
    program = parse(
        "let rows = match functionDecl()\n"
        "foreach $row in $rows do {\n"
        "  if $row.is_definition do print $row.name\n"
        "}"
    )

    assignment, loop = program.children
    assert assignment.kind == "let"
    match_tree, mode = _host(assignment.children[0])
    assert (match_tree.data, mode) == ("match", "expression")
    assert loop.kind == "foreach"
    assert loop.value == "row"
    condition = loop.children[1].children[0]
    assert condition.kind == "conditional"
    print_node = condition.children[1].children[0]
    assert print_node.kind == "print"


def test_foreach_accepts_legacy_iterator_sigil_and_optional_sigil() -> None:
    for source in (
        "foreach row in [1, 2] do $row + 1",
        "foreach $row in [1, 2] do $row + 1",
    ):
        loop = parse(source).children[0]
        assert loop.kind == "foreach"
        assert loop.value == "row"
        assert loop.children[0].kind == "list"


def test_dictionary_colon_and_conditional_colon_have_distinct_roles() -> None:
    result = parse('let value = {name: true ? "yes" : "no"}').children[0]
    assert result.kind == "let"
    dictionary = result.children[0]
    assert dictionary.kind == "dict"
    assert dictionary.children[0].value == "name"
    assert dictionary.children[0].children[0].kind == "conditional"


def test_nested_help_and_quit_are_rejected_with_clear_location() -> None:
    for command in ("help", "quit", "exit"):
        with pytest.raises(ValueError, match=rf"{command} is only valid as a top-level"):
            parse(f"if true do {command}")


def test_invalid_python_syntax_is_not_retried_as_a_host_command() -> None:
    with pytest.raises(UnexpectedInput):
        parse("def result(): pass")


def test_checked_literal_range_uses_prototype_parse_path() -> None:
    with pytest.raises(ValueError, match="signed 64-bit range"):
        parse("let value = 9223372036854775808")


def test_native_match_target_suffixes_stay_inside_host_command() -> None:
    program = parse(
        'let calls = match callExpr().bind("call") in $rows.f; '
        'let first = match callExpr() in $rows[0].f'
    )
    calls, first = program.children
    match_tree, mode = _host(calls.children[0])
    assert (match_tree.data, mode) == ("match", "expression")
    target = match_tree.children[-1]
    assert isinstance(target, Tree)
    assert target.data == "reference"
    assert [str(child) for child in target.children if not isinstance(child, Tree)] == [
        "$", "rows", ".", "f"
    ]
    matcher = match_tree.children[1]
    assert isinstance(matcher, Tree)
    assert matcher.children[-1].data == "bind"

    indexed_tree, _ = _host(first.children[0])
    indexed_target = indexed_tree.children[-1]
    assert isinstance(indexed_target, Tree)
    assert indexed_target.data == "reference"
    assert [str(child) for child in indexed_target.children if not isinstance(child, Tree)] == [
        "$", "rows", "[", "0", "]", ".", "f"
    ]


def test_grouping_allows_postfix_on_native_command_result() -> None:
    value = parse("let field = (match callExpr() in $rows).field").children[0]
    access = value.children[0]
    assert access.kind == "get"
    assert access.value == "field"
    assert access.children[0].kind == "host"


def test_legacy_reference_methods_remain_opaque_host_expressions() -> None:
    value = parse('let present = $row.f.hasField("decl_name")').children[0]
    tree, mode = _host(value.children[0])
    assert (tree.data, mode) == ("reference", "expression")
    assert isinstance(tree.children[-1], Tree)
    assert tree.children[-1].data == "has_field_call"


def test_strings_keep_original_token_for_legacy_interpolation() -> None:
    value = parse('let message = "Hello $name"').children[0].children[0]
    tree, mode = _host(value)
    assert (tree.data, mode) == ("display", "expression")
    assert str(tree.children[0]) == '"Hello $name"'
    assert tree.children[0].type == "STRING"
