from __future__ import annotations

from prompt_toolkit.completion import Completion
from prompt_toolkit.document import Document

from clang_toolkit.cli.completion import ReplCompleter
from clang_toolkit.cli.matcher_catalog import NESTED_MATCHERS, ROOT_MATCHERS


def completions(
    text: str, cursor: int | None = None, **kwargs: object
) -> list[Completion]:
    document = Document(text, cursor_position=cursor)
    return list(ReplCompleter(**kwargs).get_completions(document, None))


def complete(text: str, cursor: int | None = None, **kwargs: object) -> list[str]:
    return [item.text for item in completions(text, cursor, **kwargs)]


def apply(document: Document, item: Completion) -> str:
    start = document.cursor_position + item.start_position
    return document.text[:start] + item.text + document.text[document.cursor_position :]


def test_blank_and_partial_input_offer_commands_only():
    blank = complete("")
    partial = complete("ma")
    assert {"match", "let", "cfg", "callgraph"}.issubset(blank)
    assert partial == ["match"]
    assert complete("matchFoo") == []
    assert complete("quitNow") == []


def test_legacy_command_and_session_keywords_remain_available():
    assert "background" in complete("")
    assert set(complete("session ")) == {"start", "add", "match", "pause", "resume", "close", "label"}
    assert complete("session pa") == ["pause"]
    assert complete("session res") == ["resume"]


def test_match_uses_roots_and_let_offers_nested_matcher_constructors():
    root = complete("match ")
    assignment = complete("let selected = ")
    assert root == [f"{name}(" for name in sorted(ROOT_MATCHERS)]
    assert {"hasType(", "pointerType(", "hasName("}.issubset(assignment)
    assert not {"hasName(", "matchesName(", "allOf(", "hasDescendant("}.intersection(
        root
    )
    assert not {"let", "cfg", "callgraph"}.intersection(root)


def test_exact_match_command_appends_root_matcher_with_separator():
    document = Document("match")
    choices = completions(document.text)
    names = {item.display_text: item for item in choices}
    assert "match" not in names
    assert names["functionDecl("].text == " functionDecl("
    assert names["functionDecl("].start_position == 0
    assert apply(document, names["functionDecl("]) == "match functionDecl("


def test_nested_matcher_arguments_use_nested_catalog_without_commands():
    nested = complete("match callExpr(")
    assert {f"{name}(" for name in NESTED_MATCHERS}.issubset(nested)
    assert ")" in nested
    assert not {"match", "let", "cfg", "callgraph"}.intersection(nested)
    assert "returns(" in nested
    assert "hasReturnType(" not in nested


def test_cfg_and_callgraph_targets_do_not_offer_matcher_catalog(tmp_path):
    assert complete("cfg ", cwd=tmp_path) == []
    assert complete("callgraph ", cwd=tmp_path) == []


def test_references_are_injected_and_fields_follow_dot():
    refs = {"fn": ("body", "name")}
    assert complete("cfg $") == []
    assert complete("cfg $", references=refs) == ["fn"]
    assert complete("cfg $fn.", references=refs) == ["body", "name"]
    assert complete("cfg $fn.b", references=refs) == ["body"]
    two_refs = {"first": ("firstField",), "second": ("secondField",)}
    assert complete("match callExpr($first, $second.", references=two_refs) == [
        "secondField"
    ]


def test_bind_completion_and_strings_do_not_invent_values():
    assert complete("match callExpr()") == [".bind", "in"]
    assert complete("match callExpr().") == [".bind"]
    assert complete("match callExpr().bi") == [".bind"]
    assert complete("match callExpr().bind(") == []
    assert complete('match callExpr().bind("capture")') == ["in"]
    assert (
        complete('match hasName("function")', cursor=len('match hasName("func')) == []
    )
    assert complete('match hasName("unfinished') == []


def test_cursor_suffix_and_multiline_nested_context_are_preserved():
    existing_open = completions("match functionD()", cursor=len("match functionD"))
    assert [item.text for item in existing_open] == ["functionDecl"]
    assert existing_open[0].start_position == -len("functionD")
    spaced = Document("match functionD\n()", cursor_position=len("match functionD"))
    choice = completions(spaced.text, spaced.cursor_position)[0]
    assert apply(spaced, choice) == "match functionDecl\n()"
    assert complete(
        "match functionDecl(isD)",
        cursor=len("match functionDecl(isD"),
        matchers=("isDeclaration",),
    ) == ["isDeclaration("]
    nested = complete("match callExpr(\n  ")
    assert "hasName(" in nested and ")" in nested


def test_custom_matcher_catalogs_remain_injectable():
    custom = ("customNode",)
    assert complete("match custom", matchers=custom) == ["customNode("]
    assert complete("match custom", matchers=(name for name in custom)) == [
        "customNode("
    ]
    assert complete("match custom", matchers=("nestedOnly",), root_matchers=custom) == [
        "customNode("
    ]


def test_invalid_assignment_prefix_does_not_offer_matchers():
    assert complete('let "abc" ') == []
    assert complete("@match ") == []


def test_runtime_list_and_filesystem_properties_complete_from_live_bindings(tmp_path):
    from unittest.mock import Mock

    from clang_toolkit.cli.app import dispatch
    from clang_toolkit.cli.runtime import Runtime
    from clang_toolkit.client import Client

    client = Mock(spec=Client)
    runtime = Runtime(client, cwd=tmp_path, environment={})
    completer = ReplCompleter(references=runtime.completion_references)

    def live(text: str) -> list[str]:
        return [item.text for item in completer.get_completions(Document(text), None)]

    assert live("$files.") == []
    (tmp_path / "a.cpp").write_text("x")
    dispatch(client, 'let files = glob("*.cpp")', runtime)
    runtime.bindings["file"] = runtime.bindings["files"][0]
    assert live("$files.") == ["isEmpty", "joinWith(", "length"]
    assert live("$files.joinW") == ["joinWith("]
    assert live("$file.") == [
        "absolute",
        "basename",
        "dirname",
        "modified",
        "parts",
        "size",
    ]
