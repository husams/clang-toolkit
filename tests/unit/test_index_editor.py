"""Index commands keep completion and highlighting aligned in every console."""

from __future__ import annotations

import pytest
from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document
from prompt_toolkit.output import DummyOutput

from clang_toolkit.cli.prompt import create_session


KINDS = {"function", "class", "variable", "alias"}


def choices(source, engine, *, cursor=None, manual=False):
    session = create_session(output=DummyOutput(), script_engine=engine)
    return list(
        session.completer.get_completions(
            Document(source, cursor_position=cursor),
            CompleteEvent(completion_requested=manual, text_inserted=not manual),
        )
    )


@pytest.mark.parametrize("engine", ["legacy", "tree", "compiled"])
@pytest.mark.parametrize("manual", [False, True])
@pytest.mark.parametrize("prefix", ["", "let hits = ", "print 1\n"])
def test_kind_menu_offers_only_supported_values(engine, manual, prefix):
    items = choices(prefix + 'index find "flow" kind ', engine, manual=manual)
    assert {item.text for item in items} == KINDS
    assert all(item.display_meta_text == "symbol kind" for item in items)


@pytest.mark.parametrize("engine", ["legacy", "tree", "compiled"])
@pytest.mark.parametrize(
    "partial,expected",
    [
        ("f", "function"),
        ("c", "class"),
        ("v", "variable"),
        ("a", "alias"),
    ],
)
def test_partial_kind_replaces_only_the_editable_name(engine, partial, expected):
    source = 'index find "flow" exact kind ' + partial + ' in "ctk-lab"'
    cursor = source.index(' in "ctk-lab"')
    items = choices(source, engine, cursor=cursor)
    assert len(items) == 1
    item = items[0]
    start = cursor + item.start_position
    assert source[:start] + item.text + source[cursor:] == (
        'index find "flow" exact kind ' + expected + ' in "ctk-lab"'
    )


@pytest.mark.parametrize("engine", ["legacy", "tree", "compiled"])
def test_index_options_and_cancel_complete_from_grammar(engine):
    assert {item.text for item in choices('index find "flow" ', engine)} == {
        "exact",
        "kind",
        "in",
    }
    assert {item.text for item in choices('index find "flow" k', engine)} == {"kind"}
    assert {item.text for item in choices('index find "flow" e', engine)} == {"exact"}
    assert {item.text for item in choices("index ca", engine)} == {"cancel"}


@pytest.mark.parametrize("engine", ["legacy", "tree", "compiled"])
def test_kind_completion_preserves_the_existing_suffix(engine):
    source = 'index find "flow" kind function in "ctk-lab"'
    cursor = source.index("function") + 3
    items = choices(source, engine, cursor=cursor)
    assert len(items) == 1
    item = items[0]
    assert (
        source[: cursor + item.start_position] + item.text + source[cursor:] == source
    )


@pytest.mark.parametrize("prefix", ["print 1\n" * 1100, "let search() = {\n  "])
def test_compiled_index_commands_recover_context_in_large_or_nested_scripts(prefix):
    assert {
        item.text for item in choices(prefix + 'index find "flow" kind ', "compiled")
    } == KINDS


@pytest.mark.parametrize("separator", ["\n", "; "])
def test_completed_index_commands_keep_script_completion_on_the_next_statement(
    separator,
):
    items = choices("index list" + separator + "wh", "compiled")
    assert "while" in {item.text for item in items}


@pytest.mark.parametrize("engine", ["legacy", "tree", "compiled"])
@pytest.mark.parametrize(
    "source,keywords",
    [
        (
            'index find "flow" exact kind function in "ctk-lab"',
            {"index", "find", "exact", "kind", "in"},
        ),
        ('index cancel "ctk-lab"', {"index", "cancel"}),
        ('index lookup "usr" in "ctk-lab"', {"index", "lookup", "in"}),
        ('index resume "ctk-lab"', {"index", "resume"}),
        ('index start "ctk-lab"', {"index", "start"}),
        ('index status "ctk-lab"', {"index", "status"}),
        ('index pause "ctk-lab"', {"index", "pause"}),
        ("index list", {"index", "list"}),
    ],
)
def test_index_keywords_are_highlighted_in_the_actual_prompt(engine, source, keywords):
    session = create_session(output=DummyOutput(), script_engine=engine)
    fragments = session.lexer.lex_document(Document(source))(0)
    assert "".join(text for _, text in fragments) == source
    assert keywords <= {text for style, text in fragments if style == "class:keyword"}
    assert all(
        style == "class:string" for style, text in fragments if text.startswith('"')
    )


@pytest.mark.parametrize("engine", ["legacy", "tree", "compiled"])
@pytest.mark.parametrize("source", ['index find "kind', 'index find "flow" # kind '])
def test_kind_choices_do_not_leak_into_strings_or_comments(engine, source):
    assert not choices(source, engine)
