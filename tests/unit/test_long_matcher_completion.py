"""Long scripts must retain the full Clang catalog at the editing cursor."""

from __future__ import annotations

import pytest
from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document

from clang_toolkit.cli.completion import ReplCompleter
from clang_toolkit.cli.matcher_catalog import NESTED_MATCHERS, ROOT_MATCHERS
from clang_toolkit.cli.runtime.prototype.repl_editor import PrototypeCompleter


def choices(source: str, *, manual: bool, cursor: int | None = None):
    return list(PrototypeCompleter(ReplCompleter()).get_completions(
        Document(source, cursor_position=cursor),
        CompleteEvent(completion_requested=manual, text_inserted=not manual)))


@pytest.mark.parametrize("manual", [False, True])
@pytest.mark.parametrize("end,expected", [
    ("match ", ROOT_MATCHERS),
    ("let selected = ", NESTED_MATCHERS),
    ("let selected = functionDecl(hasDescendant(", NESTED_MATCHERS),
    ("match functionDecl(" + "isDefinition(), " * 40, NESTED_MATCHERS),
])
def test_full_clang_catalog_survives_a_long_multiline_prefix(manual, end, expected):
    source = "print 1\n" * 1100 + end
    offered = {item.display_text.removesuffix("(") for item in choices(source, manual=manual)}
    assert set(expected) <= offered
    assert {"functionDecl", "cxxRecordDecl"} <= offered


@pytest.mark.parametrize("manual", [False, True])
def test_completion_in_a_long_matcher_does_not_reparse_earlier_arguments(manual):
    source = "match functionDecl(" + "isDefinition(), " * 40 + "cxxR"
    item = next(item for item in choices(source, manual=manual)
                if item.display_text == "cxxRecordDecl(")
    assert item.display_meta_text.startswith("node matcher ·")


def test_earlier_line_completion_in_a_long_assignment_preserves_existing_text():
    source = "print 1\n" * 1100 + 'let selected = functionDecl(\n  hasDescendant(cxxR())\n)\nprint "KEEP"'
    cursor = source.index("cxxR") + len("cxxR")
    item = next(item for item in choices(source, manual=True, cursor=cursor)
                if item.display_text == "cxxRecordDecl")
    start = cursor + item.start_position
    assert source[:start] + item.text + source[cursor:] == source.replace("cxxR()", "cxxRecordDecl()")


def test_recovered_root_context_keeps_predicates_out_of_match_root_picker():
    source = "print 1\n" * 1100 + "match hasN"
    assert "hasName(" not in {item.text for item in choices(source, manual=True)}


def test_long_literal_keeps_the_completion_work_limit(monkeypatch):
    import clang_toolkit.cli.completion as completion

    def unexpected_context(*_args):
        raise AssertionError("large literal must not enter the legacy parser")

    monkeypatch.setattr(completion, "cursor_context", unexpected_context)
    source = 'let selected = functionDecl(hasName("' + "x" * 9000
    assert choices(source, manual=False) == []


@pytest.mark.parametrize("tail", ['# cxxR', '"cxxR'])
def test_recovery_does_not_offer_matchers_at_the_end_of_a_comment_or_open_string(tail):
    source = "print 1\n" * 1100 + "let selected = functionDecl(" + tail
    assert choices(source, manual=True) == []


def test_assignment_inside_a_runnable_keeps_node_matcher_suggestions():
    source = 'let find() = {\n  let selected = cxxR()\n  print "KEEP"\n}'
    cursor = source.index("cxxR") + len("cxxR")
    item = next(item for item in choices(source, manual=True, cursor=cursor)
                if item.display_text == "cxxRecordDecl")
    start = cursor + item.start_position
    assert source[:start] + item.text + source[cursor:] == source.replace("cxxR()", "cxxRecordDecl()")
