from __future__ import annotations

import pytest
from lark.exceptions import UnexpectedInput

from clang_toolkit.cli.runtime.prototype.syntax import parse


def test_expression_precedence_and_right_associative_conditional() -> None:
    program = parse("let value = $a + 2 * -3 ? 10 : $b ? 20 : 30")
    expression = program.children[0].children[0]

    assert expression.kind == "conditional"
    condition = expression.children[0]
    assert condition.kind == "binary" and condition.value == "+"
    assert condition.children[1].kind == "binary"
    assert condition.children[1].value == "*"
    false_block = expression.children[2]
    assert false_block.children[0].kind == "conditional"


def test_layout_and_grouped_collection_newlines_are_not_statements() -> None:
    program = parse(
        "let value = (\n 1 + 2\n)\n"
        "let values = [\n 1,\n 2,\n]\n"
        "let record = {\n name: $value,\n if: true,\n \"display name\": \"ok\"\n}"
    )

    assert [node.kind for node in program.children] == ["let", "let", "let"]
    record = program.children[2].children[0]
    assert record.kind == "dict"
    assert [entry.value for entry in record.children] == ["name", "if", "display name"]


def test_grouped_newlines_can_split_operators_without_hiding_body_layout() -> None:
    program = parse(
        "if true {\n"
        " let value = (1 +\n 2)\n"
        " print $value\n"
        "}"
    )
    body = program.children[0].children[1]
    assert [node.kind for node in body.children] == ["let", "print"]
    assert body.children[0].children[0].value == "+"


def test_foreach_is_a_value_expression_and_collects_a_block_shape() -> None:
    program = parse("let rows = foreach item in range(100) do ({index: $item})")
    loop = program.children[0].children[0]
    assert loop.kind == "foreach" and loop.value == "item"
    assert loop.children[0].kind == "call" and loop.children[0].value == "range"
    assert loop.children[1].kind == "block"
    assert loop.children[1].children[0].kind == "dict"


def test_unbraced_control_bodies_consume_the_complete_expression() -> None:
    program = parse(
        "let rows = foreach item in [1, 2] do "
        "foreach other in [3, 4] do $item * $other"
    )
    outer = program.children[0].children[0]
    inner = outer.children[1].children[0]
    product = inner.children[1].children[0]
    assert product.kind == "binary" and product.value == "*"
    assert [child.value for child in product.children] == ["item", "other"]

    conditional = parse("if false do 1 + 2 else 3 * 4").children[0]
    assert conditional.kind == "conditional"
    assert conditional.children[1].children[0].value == "+"
    assert conditional.children[2].children[0].value == "*"


def test_member_and_returned_calls_keep_their_callee_expressions() -> None:
    member_call = parse("$obj.fn()").children[0]
    assert member_call.kind == "invoke"
    assert (member_call.children[0].kind, member_call.children[0].value) == ("get", "fn")
    returned_call = parse("range(1)()").children[0]
    assert returned_call.kind == "invoke"
    assert (returned_call.children[0].kind, returned_call.children[0].value) == ("call", "range")


def test_member_index_and_assignment_targets_keep_their_structure() -> None:
    program = parse("$records[0].count += 1")
    assignment = program.children[0]

    target = assignment.children[0]
    assert target.kind == "get" and target.value == "count"
    indexed = target.children[0]
    assert indexed.kind == "index"
    assert indexed.children[0].kind == "ref" and indexed.children[0].value == "records"
    assert indexed.children[1].kind == "literal" and indexed.children[1].value == 0


def test_if_unless_foreach_and_nearest_else_lower_to_blocks() -> None:
    program = parse(
        'if $outer do if $inner do print "inner"\n'
        'else print "middle"\nelse print "outer"\n'
        'unless $found do "missing" else "found"\n'
        'foreach item in range(1, 4) do print $item'
    )

    outer = program.children[0]
    assert outer.kind == "conditional"
    assert outer.children[2].children[0].kind == "print"
    nested = outer.children[1].children[0]
    assert nested.kind == "conditional"
    assert nested.children[2].children[0].children[0].value == "middle"

    unless = program.children[1]
    assert unless.kind == "conditional"
    assert unless.children[0].kind == "unary" and unless.children[0].value == "not"
    assert unless.children[0].children[0].kind == "ref"
    assert unless.children[0].children[0].value == "found"
    assert unless.children[1].children[0].value == "missing"
    assert unless.children[2].children[0].value == "found"

    loop = program.children[2]
    assert loop.kind == "foreach" and loop.value == "item"
    assert loop.children[0].kind == "call" and loop.children[0].value == "range"


def test_semicolon_separates_same_line_statements_and_signed_minimum_parses() -> None:
    program = parse("let n = -9223372036854775808; $n = $n + 1; print $n")
    assert [node.kind for node in program.children] == ["let", "assign", "print"]
    minimum = program.children[0].children[0]
    assert minimum.kind == "literal" and minimum.value == -(1 << 63)


def test_parse_errors_are_lark_errors_with_location() -> None:
    with pytest.raises(UnexpectedInput) as raised:
        parse("let value = @")
    assert raised.value.line == 1
    assert raised.value.column >= 1


def test_integer_outside_signed_64_bit_range_is_rejected() -> None:
    with pytest.raises(ValueError, match="signed 64-bit"):
        parse("let value = 9223372036854775809")


def test_mixed_then_do_dangling_else_binds_to_nearest_unbraced_conditional():
    nested = parse("if false then if true do 1 else 2").children[0]
    assert nested.kind == "conditional"
    assert not nested.children[2].children
    inner = nested.children[1].children[0]
    assert inner.kind == "conditional"
    assert inner.children[2].children[0].value == 2

    inverse = parse("if false do if true then 1 else 2").children[0]
    assert not inverse.children[2].children
    assert inverse.children[1].children[0].children[2].children[0].value == 2


def test_explicit_then_block_keeps_else_on_outer_conditional():
    outer = parse("if false then { if true do 1 } else 2").children[0]
    assert outer.children[2].children[0].value == 2
    assert not outer.children[1].children[0].children[2].children


def test_dangling_else_keeps_explicit_inner_else_and_grouping():
    explicit_inner = parse(
        "if false then if true then 1 else {} else 2"
    ).children[0]
    assert explicit_inner.children[2].children[0].value == 2
    inner = explicit_inner.children[1].children[0]
    assert inner.children[2].kind == "block"
    assert not inner.children[2].children

    grouped = parse("if false then (if true then 1) else 2").children[0]
    assert grouped.children[2].children[0].value == 2
    assert grouped.children[1].children[0].kind == "conditional"


def test_value_predicates_build_the_shared_predicate_ir():
    cases = {
        "$record has a": ("has", "ref", "record", "literal", "a"),
        '$record has "a"': ("has", "ref", "record", "literal", "a"),
        "$record has 'a'": ("has", "ref", "record", "literal", "a"),
        "$record has ($key)": ("has", "ref", "record", "ref", "key"),
        "$record does not have a": ("does_not_have", "ref", "record", "literal", "a"),
        "2 in $items": ("in", "literal", 2, "ref", "items"),
        "2 not in $items": ("not_in", "literal", 2, "ref", "items"),
        "$node is CXXRecord": ("is_kind", "ref", "node", "literal", "CXXRecord"),
        "$node is not CXXRecord": ("is_not_kind", "ref", "node", "literal", "CXXRecord"),
        "$x is defined": ("is_defined", "ref", "x", None, None),
        "$x is not defined": ("is_not_defined", "ref", "x", None, None),
        "$x is set": ("is_set", "ref", "x", None, None),
        "$x is not set": ("is_not_set", "ref", "x", None, None),
    }
    for source, (kind, left_kind, left_value, right_kind, right_value) in cases.items():
        predicate = parse(source).children[0]
        assert predicate.kind == "predicate" and predicate.value == kind
        assert (predicate.children[0].kind, predicate.children[0].value) == (left_kind, left_value)
        if right_kind is None:
            assert len(predicate.children) == 1
        else:
            assert (predicate.children[1].kind, predicate.children[1].value) == (right_kind, right_value)


@pytest.mark.parametrize("source", ["1 < 2 < 3", "$x is set is defined", "$r has a has b"])
def test_chained_comparisons_and_predicates_are_rejected(source: str) -> None:
    with pytest.raises(UnexpectedInput):
        parse(source)


@pytest.mark.parametrize("source", ["$x.member is defined", "false is set", "($x + 1) is not defined"])
def test_defined_and_set_predicates_require_a_root_reference(source: str) -> None:
    with pytest.raises(ValueError, match=r"root variable reference at line 1, column"):
        parse(source)


def test_grouped_root_reference_is_valid_for_binding_predicates() -> None:
    predicate = parse("($x) is defined").children[0]
    assert predicate.kind == "predicate" and predicate.value == "is_defined"
    assert predicate.children[0].kind == "ref" and predicate.children[0].value == "x"


def test_predicate_words_do_not_split_identifiers_or_postfix_access() -> None:
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
        assert parse(source).children[0].kind in {"ref", "get", "index", "predicate"}


def test_logical_word_operators_do_not_split_reference_names() -> None:
    expression = parse("true and $candy or $forever").children[0]
    assert expression.kind == "binary" and expression.value == "or"
    assert expression.children[0].kind == "binary" and expression.children[0].value == "and"
