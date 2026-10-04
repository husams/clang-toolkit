from __future__ import annotations

from clang_toolkit.cli.input_state import input_state


def test_open_delimiters_need_more_input():
    state = input_state("match callExpr(")
    assert state.stack == ("(",)
    assert state.open_string is False
    assert state.error_at is None
    assert state.needs_more is True


def test_nested_delimiters_balance():
    state = input_state("foo({[1]})")
    assert state.stack == ()
    assert state.error_at is None
    assert state.needs_more is False


def test_mismatched_delimiter_is_an_error_not_incomplete():
    state = input_state("foo([)]")
    assert state.stack == ("(",)
    assert state.error_at == 5
    assert state.needs_more is False


def test_brackets_inside_strings_are_opaque():
    state = input_state("foo(\"[ { ) ]\", '{[}')")
    assert state.stack == ()
    assert state.open_string is False
    assert state.error_at is None
    assert state.needs_more is False


def test_unterminated_string_needs_more_input():
    state = input_state('foo("unterminated [')
    assert state.open_string is True
    assert state.stack == ("(",)
    assert state.error_at is None
    assert state.needs_more is True


def test_trailing_escape_keeps_string_open():
    state = input_state('match hasName("abc\\')
    assert state.open_string is True
    assert state.error_at is None
    assert state.needs_more is True


def test_escaped_quotes_and_nested_quote_styles_are_opaque():
    text = 'foo("[escaped \\" quote {]", \'{[double " quote]}\')'
    state = input_state(text)
    assert state.stack == ()
    assert state.open_string is False
    assert state.error_at is None


def test_even_escape_count_closes_string_but_odd_count_does_not():
    even = input_state('foo("a\\\\")')
    odd = input_state(r'foo("a\")')
    assert even.open_string is False
    assert even.stack == ()
    assert odd.open_string is True


def test_unrecognized_character_is_an_error():
    state = input_state("foo(@")
    assert state.error_at == 4
    assert state.needs_more is False


def test_multiline_foreach_block_waits_for_done():
    pending = input_state('foreach $x in $items do\n    "${x}"')
    assert pending.block_depth == 1
    assert pending.needs_more is True
    complete = input_state('foreach $x in $items do\n    "${x}"\ndone')
    assert complete.block_depth == 0
    assert complete.needs_more is False
    assert input_state('foreach $x in $items do "${x}"').needs_more is False
