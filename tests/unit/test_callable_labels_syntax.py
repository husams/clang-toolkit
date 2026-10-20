"""Syntax contract for optional public labels and natural calls."""

from __future__ import annotations

import pytest
from lark.exceptions import UnexpectedInput

from clang_toolkit.cli.runtime.prototype import run_source
from clang_toolkit.cli.runtime.prototype.repl_language import parse
from clang_toolkit.cli.runtime.prototype.syntax import parse as parse_standalone


def test_colon_labels_and_shorthand_defaults_keep_slot_metadata() -> None:
    definition = parse(
        "let multiply(value, by: m, to: = 2) = value * m + to"
    ).children[0]

    assert definition.kind == "runnable"
    assert definition.value == (
        "multiply",
        ("value", "m", "to"),
    )
    assert definition.parameter_labels == (None, "by", "to")
    default = definition.children[1]
    assert default.kind == "parameter"
    assert default.value == "to"
    assert default.parameter_labels == ("to",)
    assert default.children[0].value == 2


def test_natural_call_and_regular_calls_lower_to_existing_call_shapes() -> None:
    program = parse(
        "let x = multiply 5 by 6\n"
        "let y = multiply(2, 4)\n"
        "let z = multiply(5, by = 6)\n"
        "let grouped = multiply (2 + 3) by (4 + 2)"
    )

    x, y, z, grouped = (statement.children[0] for statement in program.children)
    assert (x.kind, x.value) == ("call", "multiply")
    assert [child.kind for child in x.children] == ["literal", "keyword_arg"]
    assert x.children[1].value == "by"
    assert (y.kind, y.value) == ("call", "multiply")
    assert [child.value for child in y.children] == [2, 4]
    assert z.children[1].kind == "keyword_arg" and z.children[1].value == "by"
    assert grouped.children[0].kind == "binary"
    assert grouped.children[1].children[0].kind == "binary"


def test_word_calls_support_atomic_postfix_values_and_defaults_without_arguments() -> None:
    program = parse(
        "let a = multiply record.count by limits[0]\n"
        "let b = multiply source() by factor()\n"
        "let c = multiply 5"
    )
    a, b, c = (statement.children[0] for statement in program.children)
    assert a.kind == "call" and a.children[0].kind == "get"
    assert a.children[1].kind == "keyword_arg"
    assert a.children[1].children[0].kind == "index"
    assert b.children[0].kind == "call" and b.children[1].children[0].kind == "call"
    assert c.kind == "call" and len(c.children) == 1


def test_natural_calls_are_available_as_statements_and_assignment_values() -> None:
    program = parse("multiply 5 by 6\nx = multiply 2 by 4")
    assert program.children[0].kind == "call"
    assert program.children[1].kind == "assign"
    assert program.children[1].children[-1].kind == "call"


def test_natural_pipeline_stages_lower_to_existing_call_nodes() -> None:
    pipeline = parse("let result = 5 | multiply by 6 | add to 2").children[0].children[0]
    assert pipeline.kind == "pipe"
    assert [stage.kind for stage in pipeline.children] == ["literal", "call", "call"]
    assert [stage.value for stage in pipeline.children[1:]] == ["multiply", "add"]
    assert [stage.children[0].value for stage in pipeline.children[1:]] == ["by", "to"]


@pytest.mark.parametrize(
    "source",
    [
        "let f(value, value:) = value",
        "let f(by: local, by: other) = local",
    ],
)
def test_invalid_or_ambiguous_labeled_parameter_forms_are_rejected(source: str) -> None:
    with pytest.raises((UnexpectedInput, ValueError)):
        parse(source)


def test_grouped_cons_parameter_and_standalone_cons_binding_remain_available() -> None:
    labeled = parse("let first(head: tail) = tail").children[0]
    assert labeled.value == ("first", ("tail",))
    assert labeled.parameter_labels == ("head",)
    definition, binding = parse(
        "let first((head: tail)) = head\nlet head: tail = [1, 2]"
    ).children
    assert definition.value[0] == "first"
    assert definition.parameter_labels == (None,)
    assert binding.kind == "destructure"


def test_natural_calls_end_at_newline_and_preserve_subtraction_indexing_and_references() -> None:
    program = parse(
        "let f = multiply\n"
        "let indexed = items [0]\n"
        "let difference = value - 5\n"
        "let next = multiply 5 by 6\n"
        "let separate = 7"
    )
    assert program.children[0].children[0].kind == "ref"
    assert program.children[1].children[0].kind == "index"
    assert program.children[2].children[0].kind == "binary"
    assert program.children[3].children[0].kind == "call"
    assert program.children[4].children[0].kind == "literal"
    split = parse("let value = multiply\n5")
    assert [statement.kind for statement in split.children] == ["let", "literal"]
    assert split.children[0].children[0].kind == "ref"


def test_word_call_spacing_and_newlines_are_lexical_boundaries() -> None:
    program = parse("let a = multiply\nlet b = 5\nf\narg")
    assert [node.kind for node in program.children] == ["let", "let", "ref", "ref"]
    assert program.children[0].children[0].kind == "ref"
    assert program.children[1].children[0].value == 5
    assert parse("let value = multiply5").children[0].children[0].value == "multiply5"
    with pytest.raises(UnexpectedInput):
        parse("multiply 5 by6")
    with pytest.raises(UnexpectedInput):
        parse("let value = multiply 5 by\n6")


def test_word_call_keywords_allow_keyword_shaped_local_names() -> None:
    definition = parse("let f(by: by) = by").children[0]
    assert definition.value == ("f", ("by",))
    assert definition.parameter_labels == ("by",)
    assert definition.children[0].children[0].value == "by"


def test_inline_runnables_carry_the_same_slot_labels() -> None:
    runnable = parse("let multiply = (value, by: m) = value * m").children[0].children[0]
    assert runnable.kind == "inline_runnable"
    assert runnable.value == ("<inline>", ("value", "m"))
    assert runnable.parameter_labels == (None, "by")


def test_word_calls_are_statement_or_rhs_forms_and_pipe_stages_are_label_only() -> None:
    for source in (
        "let values = [multiply 5 by 6]",
        "let value = 5 | multiply 5 by 6",
    ):
        with pytest.raises(UnexpectedInput):
            parse(source)


def test_single_natural_values_accept_same_line_postfix_without_changing_grouping() -> None:
    member = parse("f record.count").children[0]
    indexed = parse("f values[0]").children[0]
    ordinary_index = parse("f [0]").children[0]
    ordinary_call = parse("f (x)").children[0]
    assert member.kind == "call" and member.children[0].kind == "get"
    assert indexed.kind == "call" and indexed.children[0].kind == "index"
    assert ordinary_index.kind == "index"
    assert ordinary_call.kind == "call" and ordinary_call.children[0].value == "x"


def test_natural_postfix_cannot_continue_across_newline_but_grouped_values_can() -> None:
    with pytest.raises(UnexpectedInput):
        parse("f 1 by record\n.count")
    grouped = parse("f (record\n.count)").children[0]
    assert grouped.kind == "call"
    assert grouped.children[0].kind == "get"


@pytest.mark.parametrize("engine", ["tree", "compiled"])
@pytest.mark.parametrize(
    ("source", "bindings", "expected"),
    [
        ("false in [0]", {}, False),
        ("true in [1]", {}, False),
        ("false in [0, false]", {}, True),
        ("needle in [0]", {"needle": 0}, True),
        ("needle in (items)", {"needle": 2, "items": [1, 2]}, True),
    ],
)
def test_membership_words_booleans_and_literals_retain_shared_meaning(
    engine: str, source: str, bindings: dict[str, object], expected: bool
) -> None:
    assert run_source(source, engine=engine, bindings=bindings).value is expected


def test_reserved_word_membership_parse_matches_standalone_and_composed_grammars() -> None:
    for parser in (parse_standalone, parse):
        for source in ("false in [0]", "true in [1]", "needle in [0]", "needle in (items)"):
            expression = parser(source).children[0]
            assert expression.kind == "predicate" and expression.value == "in"
            assert expression.children[0].kind in {"literal", "ref"}


def test_word_call_parses_match_standalone_and_composed_grammars() -> None:
    source = "let f(by: local) = local\nlet value = f 5 by 6"
    standalone = parse_standalone(source)
    composed = parse(source)
    for result in (standalone, composed):
        definition, assignment = result.children
        assert definition.parameter_labels == ("by",)
        call = assignment.children[0]
        assert call.kind == "call" and call.value == "f"
        assert [child.kind for child in call.children] == ["literal", "keyword_arg"]


def test_prefix_commands_and_existing_runnable_engine_forms_keep_their_parse() -> None:
    hosts = parse(
        'read sample.cc\nimport "lib.ctk"\nsave report to "out.json"\nhelp'
    ).children
    assert all(host.kind == "host" for host in hosts)
    assert [host.value[0].data for host in hosts] == [
        "read_expression", "import_command", "save_command", "help"
    ]

    expression = parse("let value = (x) = if x then x else 0").children[0].children[0]
    assert expression.kind == "inline_runnable"
    assert expression.children[0].kind == "block"
