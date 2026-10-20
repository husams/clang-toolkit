"""Indexed project names are grammar-scoped, quoted, and unambiguous."""

from __future__ import annotations

import pytest
from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document
from prompt_toolkit.output import DummyOutput

from clang_toolkit.cli.prompt import create_session


def complete(source, engine="compiled", roots=("/projects/ctk-lab",), cursor=None):
    session = create_session(
        output=DummyOutput(), script_engine=engine, indexed_projects=lambda: roots
    )
    return list(
        session.completer.get_completions(
            Document(source, cursor_position=cursor),
            CompleteEvent(completion_requested=True),
        )
    )


@pytest.mark.parametrize("engine", ["legacy", "tree", "compiled"])
@pytest.mark.parametrize("atom", ["", "ct", '"ct', "'ct"])
def test_project_names_complete_after_in_with_balanced_quotes(engine, atom):
    source = 'index find "flow" kind function in ' + atom
    items = complete(source, engine)
    assert len(items) == 1
    item = items[0]
    expected = "'ctk-lab'" if atom.startswith("'") else '"ctk-lab"'
    assert source[: len(source) + item.start_position] + item.text == (
        'index find "flow" kind function in ' + expected
    )
    assert item.display_text == "ctk-lab"
    assert "/projects/ctk-lab" in item.display_meta_text


@pytest.mark.parametrize("engine", ["legacy", "tree", "compiled"])
def test_mid_string_completion_preserves_existing_suffix_and_later_statements(engine):
    source = 'index find "flow" in "ctk-lab"; print "KEEP"'
    cursor = source.index("ctk-lab") + 2
    (item,) = complete(source, engine, cursor=cursor)
    assert (
        source[: cursor + item.start_position] + item.text + source[cursor:] == source
    )


def test_duplicate_project_names_insert_full_paths_and_show_provenance():
    roots = ("/one/ctk-lab", "/two/ctk-lab", "/one/ctk-lab")
    items = complete('index find "flow" in "ct', roots=roots)
    assert {item.text for item in items} == {'"/one/ctk-lab"', '"/two/ctk-lab"'}
    assert all(item.display_text == "ctk-lab" for item in items)
    assert len({item.display_meta_text for item in items}) == 2


@pytest.mark.parametrize(
    "prefix",
    ["let hits = ", "print 1\n" * 1100, "let find() = {\n"],
    ids=["assigned", "long", "runnable"],
)
def test_compiled_scopes_recover_project_completion(prefix):
    (item,) = complete(prefix + 'index find "flow" in "ct')
    assert item.text == '"ctk-lab"'


@pytest.mark.parametrize(
    "source",
    [
        'index find "ct',
        'match functionDecl() in "ct',
        'index find "flow" # in ct',
        'index find "flow" in "ctk-lab" ',
        'index find "flow" in "ctk-lab"; print "ct',
    ],
)
def test_project_names_do_not_leak_into_other_contexts(source):
    assert not any(
        "indexed project" in item.display_meta_text for item in complete(source)
    )


def test_quoting_protects_interpolation_and_special_characters():
    root = '/projects/ctk-$lab"\\name'
    (item,) = complete('index find "flow" in ', roots=(root,))
    assert item.text == '"ctk-\\$lab\\"\\\\name"'


def test_full_path_prefix_and_empty_catalog():
    (item,) = complete('index find "flow" in "/projects/ct')
    assert item.text == '"/projects/ctk-lab"'
    assert complete('index find "flow" in ', roots=()) == []


def test_exact_in_keyword_and_empty_quotes_insert_valid_literals():
    source = 'index find "flow" in'
    (item,) = complete(source)
    assert source + item.text == source + ' "ctk-lab"'
    source = 'index find "flow" in ""'
    cursor = len(source) - 1
    (item,) = complete(source, cursor=cursor)
    assert source[: cursor + item.start_position] + item.text + source[cursor:] == (
        'index find "flow" in "ctk-lab"'
    )


def test_names_with_spaces_are_quoted_and_other_contexts_do_not_load_the_catalog():
    source = 'index find "flow" in '
    (item,) = complete(source, roots=("/remote/project with spaces",))
    assert item.text == '"project with spaces"'
    calls = []
    session = create_session(
        output=DummyOutput(),
        script_engine="compiled",
        indexed_projects=lambda: calls.append(True) or (),
    )
    list(
        session.completer.get_completions(
            Document('index find "flow" kind '), CompleteEvent()
        )
    )
    list(session.completer.get_completions(Document("match fun"), CompleteEvent()))
    assert not calls


@pytest.mark.parametrize(
    "source",
    [
        'index find "flow" in ct; print "KEEP"',
        'let search() = { index find "flow" in ct }',
    ],
)
def test_unquoted_prefix_completion_preserves_following_code(source):
    cursor = source.index("in ct") + len("in ct")
    (item,) = complete(source, cursor=cursor)
    assert source[: cursor + item.start_position] + item.text + source[cursor:] == (
        source[: cursor - 2] + '"ctk-lab"' + source[cursor:]
    )
