"""Current-language editing, callable metadata and source-backed help."""

from __future__ import annotations

from unittest.mock import Mock

import pytest
from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document

from clang_toolkit.cli.app import dispatch_result
from clang_toolkit.cli.completion import ReplCompleter
from clang_toolkit.cli.prompt import create_session
from clang_toolkit.cli.runtime import Runtime
from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
from clang_toolkit.cli.runtime.prototype.repl_editor import (
    PrototypeCompleter,
    highlight,
)
from clang_toolkit.cli.workspace_markdown import render_markdown
from clang_toolkit.cli.workspace_context import CommandContext
from clang_toolkit.cli.matcher_catalog import (
    MATCHER_METADATA,
    NESTED_MATCHERS,
    ROOT_MATCHERS,
)


@pytest.fixture(params=["compiled", "tree", "legacy"])
def runtime(request, tmp_path):
    value = (
        Runtime(Mock(), cwd=tmp_path, environment={})
        if request.param == "legacy"
        else PrototypeRuntime(
            Mock(), script_engine=request.param, cwd=tmp_path, environment={}
        )
    )
    yield value
    value.close()


def completer(runtime):
    base = ReplCompleter(
        references=runtime.completion_references,
        field_resolver=runtime.completion_suggestions,
        matcher_functions=runtime.matcher_function_names,
        function_help=runtime.callable_help,
    )
    return PrototypeCompleter(base) if isinstance(runtime, PrototypeRuntime) else base


def choices(completion, source, cursor=None):
    return list(
        completion.get_completions(
            Document(source, cursor_position=cursor),
            CompleteEvent(completion_requested=True),
        )
    )


def apply(source, cursor, item):
    return source[: cursor + item.start_position] + item.text + source[cursor:]


def test_combined_highlighting_distinguishes_current_language_roles():
    source = (
        '// saved helper\nlet find(tree, name = "Sample") = {\n'
        "  let rows = match cxxRecordDecl(\n"
        "    isExpansionInMainFile(), unless(isImplicit()), hasName(name)\n"
        '  ).bind("class") in tree\n'
        '  if rows.length > 0 then true else null\n}\nfind(tree, "Sample")'
    )
    fragments = highlight(source)
    assert "".join(text for _, text in fragments) == source
    styles = {text: style for style, text in fragments if text.strip()}
    assert styles["let"] == styles["match"] == styles["in"] == "class:keyword"
    assert styles["find"] == "class:function"
    assert styles["tree"] == "class:variable"
    assert styles["cxxRecordDecl"] == "class:matcher-root"
    assert (
        styles["isExpansionInMainFile"]
        == styles["isImplicit"]
        == "class:matcher-predicate"
    )
    assert styles["unless"] == "class:matcher"
    assert styles['"Sample"'] == "class:string"
    assert styles["0"] == "class:number"
    assert styles["true"] == "class:boolean"
    assert styles["null"] == "class:null"
    assert styles["// saved helper"] == "class:comment"


@pytest.mark.parametrize(
    "source",
    ['parse "sample.cc"', 'import "library.ctk"', "help find", "server status"],
)
def test_combined_highlighting_includes_existing_command_keywords(source):
    assert highlight(source)[0][0] == "class:keyword"


def test_completion_on_an_earlier_matcher_line_preserves_following_statements(runtime):
    source = (
        "match cxxRecordDecl(\n  isExpansionInMainF(), unless(isImplicit())\n"
        ') in tree\nprint "keep this statement"'
    )
    cursor = source.index("isExpansionInMainF") + len("isExpansionInMainF")
    item = next(
        item
        for item in choices(completer(runtime), source, cursor)
        if item.text == "isExpansionInMainFile"
    )
    completed = apply(source, cursor, item)
    assert completed == source.replace("isExpansionInMainF", "isExpansionInMainFile")
    assert item.display_meta_text.startswith("narrowing matcher")


def test_completion_on_second_statement_keeps_newline_context(runtime):
    source = "let total = 2\nmatch cxxRec()\nprint 1"
    cursor = source.index("cxxRec") + len("cxxRec")
    item = next(
        item
        for item in choices(completer(runtime), source, cursor)
        if item.text == "cxxRecordDecl"
    )
    assert apply(source, cursor, item) == source.replace("cxxRec", "cxxRecordDecl")


def test_callable_help_and_completion_use_the_same_live_definition(runtime):
    definition = "let named(name) = functionDecl(hasName($name))"
    assert dispatch_result(runtime.client, definition, runtime).success
    completion = completer(runtime)
    item = next(
        item
        for item in choices(completion, "let result = nam")
        if item.text == "named("
    )
    assert item.display_meta_text == "user defined · named(name)"
    help_choice = next(
        item for item in choices(completion, "help nam") if item.text == "named"
    )
    assert help_choice.display_meta_text == item.display_meta_text
    normal = dispatch_result(runtime.client, "help named", runtime)
    shortcut = dispatch_result(runtime.client, "named?", runtime)
    assert normal.success and shortcut.success
    assert normal.output == shortcut.output
    assert normal.markdown == shortcut.markdown
    assert "named(name)" in normal.output and definition in normal.output
    assert "### Signature" in normal.markdown and "### Definition" in normal.markdown
    assert f"```ctk\n{definition}\n```" in normal.markdown
    assert dispatch_result(runtime.client, "let named = 3", runtime).success
    assert "named(" not in {
        item.text for item in choices(completion, "let result = nam")
    }
    assert dispatch_result(runtime.client, "named?", runtime).output.startswith(
        "unknown help topic:"
    )


def test_imported_matcher_help_keeps_only_its_original_definition(runtime):
    library = runtime.cwd / "matchers.ctk"
    definition = "let named(name) = functionDecl(hasName($name))"
    library.write_text("let unrelated = 123\n" + definition + "\nlet after = 321\n")
    assert dispatch_result(runtime.client, f'import "{library}"', runtime).success
    assert runtime.callable_help()["named"].definition == definition


@pytest.mark.parametrize("engine", ["compiled", "tree"])
def test_imported_runnable_help_preserves_defaults_body_and_alias(engine, tmp_path):
    library = tmp_path / "helpers.ctk"
    definition = (
        'let scale(value, factor = 2, title = "two  words") = {\n'
        "  // preserve this body\n  value * factor\n}"
    )
    library.write_text("let unrelated = 123\n" + definition + "\nlet after = 321\n")
    runtime = PrototypeRuntime(
        Mock(), script_engine=engine, cwd=tmp_path, environment={}
    )
    try:
        result = dispatch_result(
            runtime.client, f'import "{library}"; let operation = scale', runtime
        )
        assert result.success, result.output
        entry = runtime.callable_help()["operation"]
        assert entry.signature == 'operation(value, factor = 2, title = "two  words")'
        assert entry.definition == definition
        assert (
            dispatch_result(runtime.client, "help scale", runtime).markdown
            == runtime.callable_help()["scale"].markdown()
        )
        text, lines = render_markdown(entry.markdown(), 100)
        assert "preserve this body" in text and "###" not in text
        colors = {style for line in lines for style, token in line if token.strip()}
        assert len(colors) >= 6
        assert runtime.bindings["after"] == 321
    finally:
        runtime.close()


def test_prior_comment_does_not_block_later_function_and_field_completion(tmp_path):
    runtime = PrototypeRuntime(Mock(), cwd=tmp_path, environment={})
    try:
        assert dispatch_result(
            runtime.client,
            "let options = {minimum: 2}; let count(value) = value",
            runtime,
        ).success
        completion = completer(runtime)
        source = '// earlier comment\nlet total = cou()\nprint "keep"'
        cursor = source.index("cou(") + len("cou")
        item = next(
            item for item in choices(completion, source, cursor) if item.text == "count"
        )
        assert apply(source, cursor, item) == source.replace("cou()", "count()")
        source = '// earlier comment\nlet n = options.mi\nprint "keep"'
        cursor = source.index("options.mi") + len("options.mi")
        assert "minimum" in {item.text for item in choices(completion, source, cursor)}
        for source, cursor in [
            ('print "count"', len('print "cou')),
            ("// count\nprint 1", len("// cou")),
        ]:
            assert choices(completion, source, cursor) == []
    finally:
        runtime.close()


def test_explicit_completion_handles_long_multiline_draft():
    source = "\n".join("print 1" for _ in range(80)) + "\nmatch cxxRec"
    assert "cxxRecordDecl(" in {item.text for item in choices(ReplCompleter(), source)}
    session = create_session(script_engine="compiled")
    assert session.editor_lexer.lex_document(Document("let scale(x) = x"))(0)


def test_completion_inside_a_word_preserves_its_suffix_and_later_lines(runtime):
    source = 'match functionDecl(hasName("f"))\nprint "keep"'
    cursor = source.index("hasName") + len("hasN")
    item = next(
        item
        for item in choices(completer(runtime), source, cursor)
        if item.display_text == "hasName"
    )
    assert item.text == "hasN"
    assert apply(source, cursor, item) == source


def test_help_completion_inside_function_name_preserves_the_suffix(runtime):
    assert dispatch_result(
        runtime.client, "let named(name) = functionDecl(hasName($name))", runtime
    ).success
    source = 'help named\nprint "keep"'
    cursor = len("help nam")
    item = next(
        item
        for item in choices(completer(runtime), source, cursor)
        if item.display_text == "named"
    )
    assert apply(source, cursor, item) == source
    assert item.display_meta_text == "user defined · named(name)"


def test_return_type_and_auxiliary_matchers_are_available_in_runnable_body(tmp_path):
    runtime = PrototypeRuntime(Mock(), cwd=tmp_path, environment={})
    try:
        completion = completer(runtime)
        for partial, expected in [
            ("ret", "returns"),
            ("hasReturnTypeL", "hasReturnTypeLoc"),
        ]:
            source = (
                "let find(tree) = {\n  match functionDecl(\n    "
                + partial
                + "()\n  ) in tree\n}"
            )
            cursor = source.index(partial + "()") + len(partial)
            item = next(
                item
                for item in choices(completion, source, cursor)
                if item.text == expected
            )
            assert apply(source, cursor, item) == source.replace(
                partial + "()", expected + "()"
            )
            assert "matcher" in item.display_meta_text
        for name in (
            "cxxBaseSpecifier",
            "lambdaCapture",
            "templateArgument",
            "templateArgumentLoc",
            "templateName",
        ):
            assert name in NESTED_MATCHERS
            assert name in MATCHER_METADATA
            assert name not in ROOT_MATCHERS
            assert name + "(" in {
                item.text for item in choices(completion, "match cxxRecordDecl(")
            }
    finally:
        runtime.close()


def test_help_does_not_evaluate_defaults_and_context_follows_live_aliases(tmp_path):
    runtime = PrototypeRuntime(Mock(), cwd=tmp_path, environment={})
    try:
        definition = "let scale(value, factor = bump()) = value * factor"
        assert dispatch_result(
            runtime.client,
            "let hits = 0; let bump() = { hits += 1; hits }; "
            + definition
            + "; let alias = scale",
            runtime,
        ).success
        assert dispatch_result(runtime.client, "help scale", runtime).success
        assert runtime.bindings["hits"] == 0
        assert dispatch_result(
            runtime.client, "let scale(value) = 999", runtime
        ).success
        panel = CommandContext(runtime.callable_help)
        panel.update("ali", str(tmp_path), completion="alias(")
        assert "alias(value, factor = bump())" in panel.buffer.text
        assert definition in panel.render_key[0]
        assert "999" not in panel.buffer.text
        panel.update("help alias", str(tmp_path))
        assert definition in panel.render_key[0]
        assert runtime.bindings["hits"] == 0
    finally:
        runtime.close()
