from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from clang_toolkit import Matcher, allOf, functionDecl, hasName, hasParameter, unless
from clang_toolkit.cursors import file_request, retained_request


def test_matcher_composes_reuses_and_binds_immutably() -> None:
    name = hasName('quoted "name"\\path\n')
    predicate = allOf(name, unless(hasName("generated")))
    original = functionDecl(predicate)
    bound = original.bind("function")

    assert original.to_query() == (
        "functionDecl(allOf(hasName('quoted \"name\"\\path\n'), "
        'unless(hasName("generated"))))'
    )
    assert bound.to_query() == original.to_query() + '.bind("function")'
    assert original.binding is None
    assert str(bound) == bound.to_query()
    assert predicate.arguments[0] is name


def test_literals_are_safe_and_only_supported_scalars_are_accepted() -> None:
    assert Matcher("rareMatcher", "a\tb", True, False, 4, -2.5).to_query() == (
        'rareMatcher("a\tb", true, false, 4, -2.5)'
    )
    with pytest.raises(TypeError, match="unsupported matcher argument"):
        Matcher("rareMatcher", object())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="finite"):
        Matcher("rareMatcher", float("nan"))
    with pytest.raises(ValueError, match="finite"):
        Matcher("rareMatcher", float("inf"))

    class InjectingInt(int):
        def __str__(self) -> str:
            return "1), injectedMatcher("

    with pytest.raises(TypeError, match="unsupported matcher argument"):
        Matcher("rareMatcher", InjectingInt(1))
    with pytest.raises(ValueError, match="both quote delimiters"):
        Matcher("hasName", "both ' and \" quotes").to_query()


def test_generic_matcher_supports_server_matchers_without_factories() -> None:
    uncommon = Matcher("hasParameter", 1, hasName("value"))
    assert uncommon.to_query() == 'hasParameter(1, hasName("value"))'
    assert hasParameter(1, hasName("value")) == uncommon


def test_match_request_builders_normalize_typed_and_string_queries() -> None:
    typed = functionDecl(hasName("needle")).bind("fn")
    query = 'functionDecl(hasName("needle")).bind("fn")'
    assert file_request("source.cc", typed).query == file_request("source.cc", query).query
    assert retained_request("cursor-id", typed, bind="fn").query == query
    assert retained_request("cursor-id", query, bind="fn").query == query
    with pytest.raises(TypeError, match="string or Matcher"):
        file_request("source.cc", object())  # type: ignore[arg-type]


def test_matcher_is_frozen_and_validates_names_and_bindings() -> None:
    matcher = functionDecl()
    with pytest.raises(FrozenInstanceError):
        matcher.name = "other"  # type: ignore[misc]
    with pytest.raises(ValueError, match="identifier"):
        Matcher("bad-name")
    with pytest.raises(ValueError, match="identifier"):
        Matcher("")
    with pytest.raises(ValueError, match="binding name"):
        matcher.bind("")
    with pytest.raises(ValueError, match="binding name"):
        Matcher("functionDecl", binding="")
