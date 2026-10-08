from __future__ import annotations

import pytest

from clang_toolkit.cli.runtime.templates import TemplateError, evaluate_string


def test_invalid_interpolation_keeps_prefix_and_reports_interpolation_position():
    with pytest.raises(TemplateError) as raised:
        evaluate_string('"${value.}"', lambda _: "unused")

    message = str(raised.value)
    assert message.startswith("invalid interpolation: interpolation syntax error")
    assert "interpolation syntax error at line 1, column" in message
    assert "expected" in message
    assert message.endswith("$value.\n       ^")


def test_invalid_interpolation_diagnostic_bounds_the_expression_preview():
    with pytest.raises(TemplateError) as raised:
        evaluate_string('"${' + "value" * 2_000 + '.}"', lambda _: "unused")

    message = str(raised.value)
    assert len(message) < 500
    assert "Expected a name" in message
    assert message.splitlines()[-1].endswith("^")


def test_unclosed_placeholder_reports_end_position():
    with pytest.raises(TemplateError) as raised:
        evaluate_string('"prefix ${value.name"', lambda _: "unused")

    message = str(raised.value)
    assert "unclosed interpolation placeholder" in message
    assert "expected `}`" in message
    assert "line 1, column" in message
    assert "end of string" in message


def test_invalid_python_escape_reports_literal_syntax_and_position():
    with pytest.raises(TemplateError) as raised:
        evaluate_string('"\\xZ0"', lambda _: "unused")

    message = str(raised.value)
    assert message.startswith("invalid string literal:")
    assert "escape" in message
    assert "line 1, column" in message


def test_valid_interpolation_and_escaped_dollar_behavior_are_unchanged():
    def resolve(tree):
        return str(tree.children[1])

    assert evaluate_string('"value=$name; literal=\\$name"', resolve) == (
        "value=name; literal=$name"
    )
    assert evaluate_string("'$name'", resolve) == "$name"
