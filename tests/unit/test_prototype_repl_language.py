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


@pytest.mark.parametrize("command", ["match", 'cursor open "sample.cc"', "cfg"])
def test_multiline_matchers_keep_legacy_host_tree_shape(command: str) -> None:
    matcher = 'functionDecl(\n hasName(\n "caller"\n )\n, unless(isImplicit())\n).bind(\n "f"\n)'
    tree, mode = _host(parse(f"{command} {matcher}").children[0])
    single_line = f"{command} " + matcher.replace("\n", " ")
    assert tree == _host(parse(single_line).children[0])[0]
    assert mode == "statement"


def test_invalid_multiline_matcher_keeps_original_error_coordinates() -> None:
    with pytest.raises(UnexpectedInput) as failure:
        parse("let class = recordDecl(\n isExpansionInMainFile(),\n @\n)")
    assert (failure.value.line, failure.value.column) == (3, 2)


def test_semicolon_is_not_matcher_argument_whitespace() -> None:
    with pytest.raises(UnexpectedInput):
        parse("let class = recordDecl(\n isExpansionInMainFile();\n unless(isImplicit())\n)")


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


def test_then_is_conditional_body_syntax_in_composed_repl_grammar():
    program = parse(
        "let x = 2\n"
        "let y = if $x > 0 then $x * 10 else 1\n"
        "let z = if $x < 0 then 0 else if $x > 0 then {\n"
        "  let local = 3\n"
        "  $local\n"
        "} else 1"
    )
    assert [node.kind for node in program.children] == ["let", "let", "let"]
    assert program.children[1].children[0].kind == "conditional"
    nested = program.children[2].children[0]
    assert nested.kind == "conditional"
    assert nested.children[2].children[0].kind == "conditional"


def test_then_does_not_become_a_foreach_body_keyword():
    with pytest.raises(UnexpectedInput):
        parse("foreach item in [1] then $item")


def test_composed_parser_preserves_mixed_then_do_else_association():
    program = parse(
        "if false then if true do 1 else 2\n"
        "if false do if true then 1 else 2\n"
        "if false then { if true do 1 } else 2"
    )
    outer, inverse, explicit = program.children
    assert not outer.children[2].children
    assert outer.children[1].children[0].children[2].children[0].value == 2
    assert not inverse.children[2].children
    assert inverse.children[1].children[0].children[2].children[0].value == 2
    assert explicit.children[2].children[0].value == 2


def test_then_remains_a_bare_dictionary_key_and_field():
    value = parse("let r = {then: 3}; $r.then").children
    assert value[0].children[0].children[0].value == "then"
    assert value[1].value == "then"


def test_combined_parser_preserves_explicit_empty_else_and_grouped_inner_if():
    program = parse(
        "let a = if false then if true then 1 else {} else 2\n"
        "let b = if false then (if true then 1) else 2"
    )
    explicit_inner, grouped = (node.children[0] for node in program.children)
    assert explicit_inner.children[2].children[0].value == 2
    assert grouped.children[2].children[0].value == 2


def test_compiled_parser_builds_the_same_value_predicate_ir():
    from clang_toolkit.cli.runtime.prototype.syntax import parse as parse_standalone

    sources = (
        "$record has a",
        '$record has "a"',
        "$record has 'a'",
        "$record has ($key)",
        "$record does not have a",
        "2 in $items",
        "2 not in $items",
        "$node is CXXRecord",
        "$node is not CXXRecord",
        "$x is defined",
        "$x is not defined",
        "$x is set",
        "$x is not set",
    )
    for source in sources:
        assert parse(source) == parse_standalone(source)

    # The same words keep their existing collection/control and dictionary roles.
    program = parse("foreach $item in [1] do $item; let row = {has: 1, is: 2}; $row.is")
    assert program.children[0].kind == "foreach"
    assert [entry.value for entry in program.children[1].children[0].children] == ["has", "is"]
    assert program.children[2].kind == "get" and program.children[2].value == "is"


def test_predicate_keywords_remain_valid_field_names_and_allow_soft_newlines():
    for source, key in (
        ("$row has has", "has"),
        ("$row does not have not", "not"),
        ("$row has\n name", "name"),
        ("$row does not\n have\n name", "name"),
    ):
        predicate = parse(source).children[0]
        assert predicate.kind == "predicate"
        assert predicate.children[1].kind == "literal"
        assert predicate.children[1].value == key

    dictionary = parse("let row = {has: 1, does: 2, not: 3, have: 4}").children[0]
    assert [entry.value for entry in dictionary.children[0].children] == [
        "has", "does", "not", "have"
    ]


def test_predicate_words_do_not_split_identifiers_in_the_compiled_parser():
    from clang_toolkit.cli.runtime.prototype.syntax import parse as parse_standalone

    for source in (
        "$data.disabled",
        "$this",
        "$pin[1]",
        "$row.has_value",
        "$row.doesMore",
        "$row.have_name",
        "$row.inside",
        "$row.island",
        "$row.notable",
        "$row.definedness",
        "$row.setting",
        "$candy",
        "$forever",
        "$information",
        "$records[0].item is CXXRecord",
        "$records[0].item is not CXXRecord",
        "$records[0].record_name is CXXRecord",
        "$records[0].record_name is not CXXRecord",
    ):
        assert parse(source) == parse_standalone(source)
