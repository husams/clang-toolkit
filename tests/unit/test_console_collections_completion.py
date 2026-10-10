"""Completion for collection operations and local import paths."""

from __future__ import annotations

from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import to_plain_text

from clang_toolkit.cli.completion import ReplCompleter
from clang_toolkit.cli.runtime.evaluator import CompletionField


def _options(completer: ReplCompleter, source: str) -> dict[str, object]:
    return {
        item.text: item
        for item in completer.get_completions(Document(source), None)
    }


def test_collection_keywords_are_offered_in_their_grammar_positions():
    completer = ReplCompleter()

    assert "import" in _options(completer, "im")
    assert "push" in _options(completer, "pu")
    assert "pop" in _options(completer, "po")
    assert "delete" in _options(completer, "del")
    assert "split" in _options(completer, "spl")
    assert "join" in _options(completer, "joi")
    assert "by" in _options(completer, 'split "a/b" ')
    assert "with" in _options(completer, "join xs ")
    assert ":" in _options(completer, '{"a" ')


def test_flatten_completes_in_expression_contexts_and_preserves_join():
    completer = ReplCompleter()

    for source in (
        "fla",
        "let rows = fla",
        "print fla",
        "[fla",
        "{rows: fla",
        "(fla",
        "flatten(fla",
    ):
        options = _options(completer, source)
        assert "flatten" in options, source

    assignment = _options(completer, "let rows = fla")["flatten"]
    assert assignment.text == "flatten"
    assert assignment.start_position == -3

    assert "flatten" not in _options(completer, 'print "fla')
    assert "flatten" not in _options(completer, "# fla")
    assert "join" in _options(completer, "joi")
    assert "with" in _options(completer, "join xs ")


def test_collection_reference_completion_labels_methods_and_preserves_fields():
    def fields(reference: str) -> tuple[CompletionField, ...]:
        if reference == "$dict":
            return (
                CompletionField("keys", "property", "property · list"),
                CompletionField("values", "property", "property · list"),
                CompletionField("get", "method", "method · read a key"),
                CompletionField("set", "method", "method · write a key"),
                CompletionField("clear", "method", "method · clear entries"),
            )
        if reference == "$items":
            return (
                CompletionField("length", "property", "property"),
                CompletionField("push", "method", "method · append an item"),
                CompletionField("pop", "method", "method · remove the last item"),
            )
        return ()

    completer = ReplCompleter(
        references={"dict": (), "items": ()}, field_resolver=fields
    )

    dictionary = _options(completer, "$dict.")
    assert {"keys", "values", "get(", "set(", "clear("} <= dictionary.keys()
    assert to_plain_text(dictionary["get("].display_meta) == "method · read a key"
    assert to_plain_text(dictionary["keys"].display_meta) == "property · list"

    sequence = _options(completer, "$items.")
    assert {"length", "push(", "pop("} <= sequence.keys()
    assert to_plain_text(sequence["push("].display_meta) == "method · append an item"


def test_keyword_shaped_dictionary_properties_complete_beside_methods():
    def fields(reference: str) -> tuple[CompletionField, ...]:
        assert reference == "$dict"
        return (
            CompletionField("import", "property", "dictionary key"),
            CompletionField("delete", "property", "dictionary key"),
            CompletionField("delete", "method", "method · delete a key"),
            CompletionField("push", "property", "dictionary key"),
            CompletionField("with", "property", "dictionary key"),
        )

    completer = ReplCompleter(
        references={"dict": ()}, field_resolver=fields
    )

    for partial, expected in (
        ("$dict.imp", "import"),
        ("$dict.del", "delete"),
        ("$dict.pus", "push"),
        ("$dict.wit", "with"),
    ):
        options = _options(completer, partial)
        assert expected in options

    delete_options = _options(completer, "$dict.del")
    assert {"delete", "delete("} <= delete_options.keys()


def test_import_completes_relative_library_paths(tmp_path):
    library_dir = tmp_path / "lib"
    library_dir.mkdir()
    (library_dir / "module.ctk").write_text("let answer = 42\n")
    (library_dir / "more.ctk").write_text("let other = 13\n")
    completer = ReplCompleter(cwd=tmp_path)

    directory_options = _options(completer, 'import "li')
    assert '"lib/"' in directory_options
    options = _options(completer, 'import "lib/mo')
    assert {'"lib/module.ctk"', '"lib/more.ctk"'} <= options.keys()
    cursor = len('import "lib/mo')
    closing_source = 'import "lib/mo"'
    closing_item = next(
        item
        for item in completer.get_completions(
            Document(closing_source, cursor_position=cursor), None
        )
        if item.display_text == "module.ctk"
    )
    start = cursor + closing_item.start_position
    assert (
        closing_source[:start]
        + closing_item.text
        + closing_source[cursor:]
    ) == 'import "lib/module.ctk"'
    assert not _options(completer, 'let value = "lib/mo')


def test_runtime_collection_methods_have_method_metadata(tmp_path):
    from unittest.mock import Mock

    from clang_toolkit.cli.runtime import Runtime
    from clang_toolkit.client import Client

    runtime = Runtime(Mock(spec=Client), cwd=tmp_path, environment={})
    runtime.bindings.update({"dict": {"a": 1}, "items": [1, 2]})
    completer = ReplCompleter(
        references=runtime.completion_references,
        field_resolver=runtime.completion_suggestions,
    )

    dictionary = _options(completer, "$dict.")
    assert {"keys", "values", "length", "isEmpty", "get(", "set(", "delete(", "hasKey(", "clear("} <= dictionary.keys()
    assert "property" in to_plain_text(dictionary["keys"].display_meta)
    assert "method" in to_plain_text(dictionary["get("].display_meta)

    sequence = _options(completer, "$items.")
    assert {"length", "isEmpty", "push(", "pop(", "insert(", "remove(", "clear(", "joinWith(", "unique(", "sort(", "filter("} <= sequence.keys()
    assert "method" in to_plain_text(sequence["push("].display_meta)
    runtime.close()


def test_runtime_dictionary_keyword_keys_complete_as_dotted_properties(tmp_path):
    from unittest.mock import Mock

    from clang_toolkit.cli.language import reference_parser
    from clang_toolkit.cli.runtime import Runtime
    from clang_toolkit.client import Client

    runtime = Runtime(Mock(spec=Client), cwd=tmp_path, environment={})
    runtime.bindings["dict"] = {
        "import": 1,
        "push": 2,
        "delete": 3,
        "with": 4,
    }
    completer = ReplCompleter(
        references=runtime.completion_references,
        field_resolver=runtime.completion_suggestions,
    )

    for name in ("import", "push", "delete", "with"):
        reference_parser().parse(f"$dict.{name}")
        assert name in _options(completer, f"$dict.{name[:3]}")

    delete_options = _options(completer, "$dict.del")
    assert {"delete", "delete("} <= delete_options.keys()
    runtime.close()
