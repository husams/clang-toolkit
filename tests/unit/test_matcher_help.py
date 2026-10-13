"""Offline Clang matcher help and categorized completion in both console views."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from prompt_toolkit.document import Document

from clang_toolkit.client import Client
from clang_toolkit.cli.app import dispatch
from clang_toolkit.cli.completion import ReplCompleter
from clang_toolkit.cli.help import MATCHER_HELP, render_help_markdown
from clang_toolkit.cli.input_state import input_state
from clang_toolkit.cli.language import parser
from clang_toolkit.cli.matcher_catalog import MATCHER_METADATA, NESTED_MATCHERS
from clang_toolkit.cli.runtime import Runtime
from clang_toolkit.cli.workspace_context import CommandContext


def choices(source: str, **kwargs: object):
    return list(ReplCompleter(**kwargs).get_completions(Document(source), None))


def test_every_registered_matcher_has_offline_help_and_a_working_shortcut():
    client = Mock(spec=Client)
    assert set(MATCHER_HELP) == set(NESTED_MATCHERS)
    for name in NESTED_MATCHERS:
        assert MATCHER_METADATA[name][1].strip()
        output = dispatch(client, f"help {name}")
        assert output == dispatch(client, f"{name}?")
        assert f"Kind: {MATCHER_METADATA[name][0]} matcher" in output
        assert f"{name}(" in output
        assert "Reference: https://clang.llvm.org/" in output
        assert "Examples:" in output
        state = input_state(f"{name}?")
        assert not state.needs_more and state.error_at is None
    assert client.mock_calls == []


@pytest.mark.parametrize(
    "name,kind,argument,description",
    [
        (
            "functionDecl",
            "node",
            "Matcher<FunctionDecl>...",
            "Matches function declarations.",
        ),
        ("hasName", "narrowing", "StringRef Name", "specified name"),
        ("hasDescendant", "traversal", "Matcher<*>", "descendant AST nodes"),
    ],
)
def test_help_includes_category_arguments_description_and_workspace_markdown(
    name,
    kind,
    argument,
    description,
):
    client = Mock(spec=Client)
    output = dispatch(client, f"help {name}")
    assert f"Kind: {kind} matcher" in output
    assert argument in output and description in output
    assert dispatch(client, f"help matchers {name}") == output
    markdown = render_help_markdown(parser().parse(f"{name}?").children[0])
    assert f"## {name}" in markdown
    assert f"Kind: {kind} matcher" in markdown
    assert "```text" in markdown
    assert client.mock_calls == []


def test_overloaded_matcher_documents_both_declaration_and_type_arguments():
    output = dispatch(Mock(spec=Client), "hasType?")
    assert "Matcher<Decl> InnerMatcher" in output
    assert "Matcher<QualType> InnerMatcher" in output
    assert "Matcher<Expr> hasType" in output
    assert "Matcher<ValueDecl> hasType" in output


def test_category_indexes_list_each_matcher_only_in_its_reference_category():
    client = Mock(spec=Client)
    overview = dispatch(client, "help matchers")
    assert str(len(NESTED_MATCHERS)) in overview
    assert "matchers" in dispatch(client, "help")
    for kind in ("node", "narrowing", "traversal"):
        output = dispatch(client, f"help matchers {kind}")
        for name, metadata in MATCHER_METADATA.items():
            assert (f"  {name}: " in output) == (metadata[0] == kind)
    assert dispatch(client, "help matchers unknown").startswith("unknown help topic:")
    assert client.mock_calls == []


@pytest.mark.parametrize(
    "source,name,kind",
    [
        ("match functionD", "functionDecl", "node"),
        ("match functionDecl(hasNam", "hasName", "narrowing"),
        ("match functionDecl(hasDescend", "hasDescendant", "traversal"),
        ("let selected = hasNam", "hasName", "narrowing"),
        ("help hasNam", "hasName", "narrowing"),
        ("help matchers hasDescend", "hasDescendant", "traversal"),
    ],
)
def test_completion_hints_identify_matcher_kind_and_description(source, name, kind):
    item = next(
        item for item in choices(source) if item.display_text.rstrip("(") == name
    )
    assert item.display_meta_text.startswith(f"{kind} matcher · ")
    assert item.display_meta_text != f"{kind} matcher · "


def test_existing_parenthesis_and_injected_matchers_preserve_completion_hints():
    document = Document("match functionD()", cursor_position=len("match functionD"))
    item = next(iter(ReplCompleter().get_completions(document, None)))
    assert item.text == "functionDecl"
    assert item.display_meta_text.startswith("node matcher")
    custom = choices("match custom", matchers=("customNode",))[0]
    assert custom.display_meta_text == "AST matcher"
    saved = choices("let selected = hasNam", matcher_functions=("hasName",))[0]
    assert saved.display_meta_text == "saved matcher function"


def test_matcher_help_remains_visible_when_values_are_redirected(tmp_path):
    client = Mock(spec=Client)
    runtime = Runtime(client, cwd=tmp_path, environment={})
    destination = tmp_path / "values.txt"
    runtime.output.configure(str(destination))
    try:
        assert "Kind: narrowing matcher" in runtime.execute("hasName?")
        assert "Kind: traversal matcher" in dispatch(client, "help hasType", runtime)
        assert destination.read_text() == ""
    finally:
        runtime.close()
    assert client.mock_calls == []


@pytest.mark.parametrize(
    "source,name,kind",
    [
        ("match functionDecl(", "functionDecl", "node"),
        ('match functionDecl(hasName("', "hasName", "narrowing"),
        ("match functionDecl(hasDescendant(", "hasDescendant", "traversal"),
        ('match functionDecl(hasName("x"), ', "functionDecl", "node"),
        ("help hasName", "hasName", "narrowing"),
    ],
)
def test_workspace_context_follows_the_innermost_matcher(source, name, kind):
    panel = CommandContext()
    panel.update(source, ".")
    markdown = panel.render_key[0]
    assert markdown.startswith(f"## {name}\n")
    assert f"{kind.capitalize()} matcher." in markdown
    assert f"help {name}" in markdown


def test_workspace_context_previews_selected_completion_and_returns_to_command_help():
    panel = CommandContext()
    panel.update("match functionDecl(has", ".", completion="hasDescendant(")
    assert "Traversal matcher." in panel.render_key[0]
    panel.update("match", ".")
    assert panel.render_key[0].startswith("## match\n")
    panel.update('match functionDecl(hasName("hasDescendant("', ".")
    assert panel.render_key[0].startswith("## hasName\n")
