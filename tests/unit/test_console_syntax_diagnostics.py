"""Helpful, grammar-backed diagnostics for malformed console input."""

from unittest.mock import Mock

import pytest
from prompt_toolkit.utils import get_cwidth

from clang_toolkit.cli.app import dispatch
from clang_toolkit.cli.help import COMMANDS
from clang_toolkit.cli.runtime import Runtime
from clang_toolkit.cli.syntax_diagnostics import (
    _expected_summary,
    unknown_command_diagnostic,
)
from clang_toolkit.client import Client


def test_scoped_match_assignment_suggests_match_and_validated_correction():
    client = Mock(spec=Client)
    source = 'let m = functionDecl(isExpansionInMainFile()).bind("f") in $f'

    result = dispatch(client, source)

    assert "line 1, column 9" in result
    assert "missing `match` after `=` before the matcher" in result
    source_line, caret_line = result.splitlines()[1:3]
    assert source_line == source
    assert caret_line == "        ^"
    assert f"Try: `let m = match {source[len('let m = '):]}`" in result
    client.match.assert_not_called()


def test_scoped_match_suggestion_is_bounded_for_long_source():
    client = Mock(spec=Client)
    source = f'let m = functionDecl().bind("{"x" * 10_000}") in $f'

    result = dispatch(client, source)

    assert "missing `match` after `=` before the matcher" in result
    assert "Try:" not in result
    assert len(result) < 700
    source_line, caret_line = result.splitlines()[1:3]
    assert len(source_line) <= 161
    assert caret_line.endswith("^")
    assert len(caret_line) <= 161
    client.match.assert_not_called()


def test_scoped_match_location_handles_multiline_source_and_tab_alignment():
    client = Mock(spec=Client)
    source = 'let m =\n\tfunctionDecl().bind("f") in $f'

    result = dispatch(client, source)

    assert "line 2, column 2" in result
    source_line, caret_line = result.splitlines()[1:3]
    assert source_line.startswith("    functionDecl")
    assert caret_line == "    ^"
    client.match.assert_not_called()


@pytest.mark.parametrize(
    "source",
    [
        'print "界" @',
        'print "界"\t@',
    ],
)
def test_caret_uses_terminal_cells_for_wide_characters_and_following_tabs(source):
    client = Mock(spec=Client)

    result = dispatch(client, source)

    source_line, caret_line = result.splitlines()[-2:]
    marker = source_line.index("@")
    assert caret_line.index("^") == get_cwidth(source_line[:marker])
    client.match.assert_not_called()


def test_cropped_caret_keeps_wide_characters_on_display_cell_boundaries():
    client = Mock(spec=Client)
    source = 'print "' + "界" * 100 + '" @'

    result = dispatch(client, source)

    source_line, caret_line = result.splitlines()[-2:]
    marker = source_line.index("@")
    assert source_line.startswith("…")
    assert get_cwidth(source_line) <= 160
    assert caret_line.index("^") == get_cwidth(source_line[:marker])
    client.match.assert_not_called()


@pytest.mark.parametrize("mark", ["\u0301", "\ufe0f"])
def test_invisible_printable_marks_cannot_expand_the_source_preview(mark):
    client = Mock(spec=Client)
    source = 'print "' + mark * 10_000 + '" @'

    result = dispatch(client, source)

    source_line, caret_line = result.splitlines()[-2:]
    assert len(result) < 500
    assert len(source_line) <= 160
    assert len(caret_line) <= 161
    assert get_cwidth(source_line) <= 160
    assert caret_line.index("^") == get_cwidth(source_line[:source_line.index("@")])


def test_scoped_match_caret_bounds_display_columns_for_many_tabs():
    client = Mock(spec=Client)
    source = 'let m =\n' + "\t" * 100 + 'functionDecl().bind("f") in $f'

    result = dispatch(client, source)

    assert "line 2, column 101" in result
    source_line, caret_line = result.splitlines()[1:3]
    assert len(source_line) <= 161
    assert len(caret_line) <= 161
    assert source_line.startswith("…")
    assert caret_line.index("^") == source_line.index("functionDecl")
    client.match.assert_not_called()


def test_bare_matcher_assignment_remains_valid():
    client = Mock(spec=Client)
    runtime = Runtime(client)

    assert dispatch(client, "let m = functionDecl()", runtime) == ""
    assert runtime.bindings["m"].name == "functionDecl"
    client.match.assert_not_called()


def test_missing_value_has_actionable_expected_value_message():
    client = Mock(spec=Client)

    result = dispatch(client, "let result =")

    assert "expected a value after `=`" in result
    assert "matcher" in result and "reference" in result
    client.match.assert_not_called()


def test_dangling_parenthesis_and_bracket_name_the_closing_delimiter():
    client = Mock(spec=Client)

    paren = dispatch(client, "match functionDecl(")
    bracket = dispatch(client, 'match functionDecl() in ["file.cc"')

    assert "end of input" in paren
    assert "expected `)` to close" in paren
    assert "end of input" in bracket
    assert "expected `]` to close" in bracket
    client.match.assert_not_called()


def test_eof_position_uses_the_end_of_multiline_input():
    client = Mock(spec=Client)

    result = dispatch(client, "match functionDecl(\n")

    assert "line 2, column 1" in result
    assert "unexpected end of input; expected `)`" in result
    assert result.endswith("\n^")
    client.match.assert_not_called()


def test_unterminated_quote_and_unexpected_token_are_readable():
    client = Mock(spec=Client)

    quote = dispatch(client, 'match functionDecl(hasName("foo)')
    token = dispatch(client, "match functionDecl(]")

    assert "unterminated quoted string" in quote
    assert "line 1, column" in quote
    assert "unexpected `]`" in token
    assert "expected" in token
    client.match.assert_not_called()


def test_unexpected_token_uses_contextual_parser_accepts():
    client = Mock(spec=Client)

    result = dispatch(client, "let m = functionDecl() blah")

    assert "unexpected `blah`" in result
    assert "`.bind(...)`" in result
    assert "end of command" in result
    assert "expected `)`" not in result
    assert "expected `]`" not in result
    client.match.assert_not_called()


def test_literal_keyword_choices_are_derived_from_grammar_terminals():
    client = Mock(spec=Client)

    set_result = dispatch(client, "set")
    cursor_result = dispatch(client, "cursor")

    assert "`traversal`" in set_result
    assert "`files`" in set_result
    assert "`open`" in cursor_result
    assert "`continue`" in cursor_result
    client.match.assert_not_called()


def test_quote_after_earlier_parse_error_does_not_hide_error_location():
    client = Mock(spec=Client)

    result = dispatch(client, 'match functionDecl(] "oops')

    assert "line 1, column 20" in result
    assert "unexpected `]`" in result
    assert "unterminated quoted string" not in result
    client.match.assert_not_called()


@pytest.mark.parametrize(
    ("source", "expected_hint"),
    [
        ("let name", "`=`"),
        ("parse", "quoted path"),
        ("match", "matcher call"),
        ("print", "quoted string"),
        ("inspect", "variable reference"),
        ("set", "`traversal`"),
        ("cursor", "`open`"),
        ("in parse file {", "`yield`"),
        ("print [", "`]`"),
        ("foreach", "variable reference"),
        ("load", "quoted path"),
        ("save $result", "`to`"),
        ("history", "`clear`"),
        ("session", "`start`"),
        ("traverse", "quoted path"),
        ("cursor open", "quoted path"),
        ("load 'cache.db' into", "variable reference"),
        ("print @", "unexpected character"),
    ],
)
def test_malformed_command_families_report_expected_syntax_and_caret(source, expected_hint):
    client = Mock(spec=Client)

    result = dispatch(client, source)

    assert "syntax error at line 1, column" in result
    assert expected_hint in result
    assert "Expected" in result
    assert source in result
    assert result.splitlines()[-1].endswith("^")
    client.match.assert_not_called()


def test_expected_name_error_points_at_the_missing_name_position():
    client = Mock(spec=Client)

    result = dispatch(client, "set traversal")

    assert "Expected a name" in result
    assert "set traversal" in result
    assert result.endswith("\n             ^")
    client.match.assert_not_called()


def test_unmapped_expected_token_gets_a_readable_fallback_label():
    assert _expected_summary({"MYSTERY_TOKEN"}) == " Expected a mystery token value."


@pytest.mark.parametrize(
    "source",
    [
        "print $node.hasField()",
        "print $functions[0].f.value.node.hasField()",
        "print $functions[0].f.value.node.cxx_method_decl.method.hasField()",
        'print [$node.hasField(), "next"]',
        "foreach $node in [] do $node.hasField() done",
    ],
)
def test_has_field_missing_argument_names_required_string_field(source):
    client = Mock(spec=Client)

    result = dispatch(client, source)

    assert 'hasField requires a field name: `hasField("field_name")`' in result
    source_line, caret_line = result.splitlines()[-2:]
    assert source_line == source
    assert caret_line.index("^") == source.index(")", source.index(".hasField("))
    assert "Expected a quoted string" not in result
    client.match.assert_not_called()


def test_has_field_at_eof_names_missing_string_argument():
    client = Mock(spec=Client)
    source = "print $node.hasField("

    result = dispatch(client, source)

    assert "hasField requires a field name" in result
    assert result.endswith("\n" + " " * len(source) + "^")
    client.match.assert_not_called()


def test_unexpected_token_preview_escapes_embedded_control_characters():
    client = Mock(spec=Client)
    source = 'let "a\nb" = 1'

    result = dispatch(client, source)

    header = result.splitlines()[0]
    assert "unexpected" in header
    assert r"\n" in header
    assert "Expected a name" in header
    assert result.endswith("^")
    client.match.assert_not_called()


def test_unknown_command_diagnostic_keeps_prefix_and_offers_help_or_typo():
    typo = unknown_command_diagnostic("  prnt", "prnt", COMMANDS)
    unknown = unknown_command_diagnostic("florp", "florp", COMMANDS)

    assert typo.startswith("unknown command: prnt")
    assert "line 1, column 3" in typo
    assert "Did you mean `print`?" in typo
    assert "Use `help` to see available commands." in typo
    assert typo.endswith("\n  prnt\n  ^")
    assert unknown.startswith("unknown command: florp")
    assert "Expected a command" in unknown or "Use `help`" in unknown
    assert unknown.endswith("\nflorp\n^")


def test_unknown_command_diagnostic_bounds_long_command_and_source_preview():
    command = "z" * 10_000
    result = unknown_command_diagnostic(command, command, COMMANDS)

    assert len(result) < 500
    assert result.startswith("unknown command: " + "z" * 32 + "…")
    source_line, caret_line = result.splitlines()[-2:]
    assert len(source_line) <= 161
    assert len(caret_line) <= 161
