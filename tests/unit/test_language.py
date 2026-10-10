from __future__ import annotations

import pytest
from lark.exceptions import UnexpectedInput

from clang_toolkit.cli.language import lex, parser


def test_parser_has_positions_and_command_aliases():
    assert parser().parse("match callExpr()").children[0].data == "match"
    assert parser().parse("cfg ns::Thing").children[0].data == "cfg"
    assert parser().parse("cfg Thing").children[0].data == "cfg"
    assert parser().parse("callgraph").children[0].data == "callgraph"
    assert parser().parse("help").children[0].data == "help"
    tree = parser().parse("match callExpr()")
    assert tree.meta.start_pos == 0
    assert tree.meta.end_pos == len("match callExpr()")


def test_root_nested_and_qualified_matcher_arguments_parse():
    text = 'match functionDecl(hasName("x"), ns::value)'
    assert parser().parse(text).children[0].data == "match"
    matcher_tokens = [
        (token.type, str(token))
        for token in lex(text)
        if token.type.endswith("MATCHER_NAME")
    ]
    assert matcher_tokens == [
        ("ROOT_MATCHER_NAME", "functionDecl"),
        ("MATCHER_NAME", "hasName"),
    ]


def test_lex_preserves_whitespace_and_covers_every_character():
    text = "let matchFoo = callExpr(\"[x]\", $arg.part).bind('label')"
    tokens = lex(text)
    assert "".join(str(token) for token in tokens) == text
    assert all(token.start_pos < token.end_pos for token in tokens)
    assert next(token for token in tokens if str(token) == "matchFoo").type == "NAME"
    assert next(token for token in tokens if str(token) == "let").type == "LET"
    assert next(token for token in tokens if str(token) == " ").type == "WS"
    assert next(token for token in tokens if str(token) == '"[x]"').type == "STRING"
    assert next(token for token in tokens if str(token) == "'label'").type == "STRING"


def test_multiline_done_token_is_losslessly_split_for_editor_consumers():
    text = 'foreach $m in $xs do $m\n# comment\ndone'
    tokens = lex(text)

    assert "".join(str(token) for token in tokens) == text
    assert [(token.type, str(token)) for token in tokens[-4:]] == [
        ("WS", "\n"),
        ("COMMENT", "# comment"),
        ("WS", "\n"),
        ("DONE", "done"),
    ]
    assert [(token.start_pos, token.end_pos) for token in tokens[-4:]] == [
        (23, 24),
        (24, 33),
        (33, 34),
        (34, 38),
    ]
def test_lex_marks_bad_characters_and_keeps_scanning():
    tokens = lex("foo @ bar")
    assert [(token.type, str(token)) for token in tokens] == [
        ("NAME", "foo"),
        ("WS", " "),
        ("ERROR", "@"),
        ("WS", " "),
        ("NAME", "bar"),
    ]


def test_keywords_require_identifier_boundaries():
    assert [
        (token.type, str(token))
        for token in lex("quit quitNow true-ish")
        if token.type != "WS"
    ] == [
        ("QUIT", "quit"),
        ("NAME", "quitNow"),
        ("NAME", "true"),
        ("ERROR", "-"),
        ("NAME", "ish"),
    ]


def test_command_keywords_do_not_split_longer_identifiers():
    for text in ("matchFoo", "quitNow", "callgraphExtra"):
        tokens = lex(text)
        assert [(token.type, str(token)) for token in tokens] == [("NAME", text)]
        assert "".join(str(token) for token in tokens) == text

    with pytest.raises(UnexpectedInput):
        parser().parse("matchFoo()")
    with pytest.raises(UnexpectedInput):
        parser().parse("callgraphExtra")


def test_lossless_lex_keeps_partial_suffix_after_command_prefix_identifier():
    text = "matchFoo @"
    tokens = lex(text)
    assert "".join(str(token) for token in tokens) == text
    assert [(token.type, str(token)) for token in tokens] == [
        ("NAME", "matchFoo"),
        ("WS", " "),
        ("ERROR", "@"),
    ]


def test_contextual_keywords_remain_names_where_grammar_expects_names():
    assert [
        (token.type, str(token))
        for token in lex("let match = fn()")
        if token.type != "WS"
    ] == [
        ("LET", "let"),
        ("NAME", "match"),
        ("EQUAL", "="),
        ("ROOT_MATCHER_NAME", "fn"),
        ("LPAR", "("),
        ("RPAR", ")"),
    ]
    assert [(token.type, str(token)) for token in lex("cfg $match")] == [
        ("CFG", "cfg"),
        ("WS", " "),
        ("DOLLAR", "$"),
        ("NAME", "match"),
    ]


def test_bind_spelling_is_contextual_inside_references():
    assert [
        (token.type, str(token)) for token in lex("cfg $fn.bind") if token.type != "WS"
    ] == [
        ("CFG", "cfg"),
        ("DOLLAR", "$"),
        ("NAME", "fn"),
        ("DOT", "."),
        ("NAME", "bind"),
    ]


def _accepted_after(text: str) -> set[str]:
    interactive = parser().parse_interactive(text)
    list(interactive.iter_parse())
    return set(interactive.accepts())


def test_matcher_name_roles_are_available_only_in_match_contexts():
    assert "ROOT_MATCHER_NAME" not in _accepted_after("")
    assert _accepted_after("match") >= {"ROOT_MATCHER_NAME", "DOLLAR"}
    assert _accepted_after("match\n") >= {"ROOT_MATCHER_NAME", "DOLLAR"}
    assert _accepted_after("let item =") >= {"ROOT_MATCHER_NAME", "DOLLAR"}
    assert "MATCHER_NAME" in _accepted_after("match functionDecl(")

    cfg_targets = _accepted_after("cfg ")
    assert "NAME" in cfg_targets
    assert "ROOT_MATCHER_NAME" not in cfg_targets
    assert "MATCHER_NAME" not in cfg_targets


def test_root_match_expression_rejects_scalars():
    with pytest.raises(UnexpectedInput):
        parser().parse("match 3")
    assert parser().parse('let item = "text"').children[0].data == "assignment"


def test_target_matcher_names_stay_generic():
    assert (
        parser().parse("cfg ordinaryTarget(nestedTarget())").children[0].data == "cfg"
    )
    tokens = [token for token in lex("cfg ordinaryTarget(nestedTarget())")]
    assert all(
        token.type not in {"ROOT_MATCHER_NAME", "MATCHER_NAME"} for token in tokens
    )


def test_common_number_forms_are_retained():
    assert (
        next(token for token in lex("1.25e+3") if token.type != "WS").type == "NUMBER"
    )
    assert parser().parse("match countIs(1.25e+3)").children[0].data == "match"
