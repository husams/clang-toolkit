from __future__ import annotations

from unittest.mock import Mock

import pytest
from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import to_plain_text

from clang_toolkit.cli.app import dispatch_result
from clang_toolkit.cli.completion import ReplCompleter
from clang_toolkit.cli.highlight import TOKEN_STYLES
from clang_toolkit.cli.runtime.prototype.filters import FILTER_SIGNATURES
from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
from clang_toolkit.cli.runtime.prototype.repl_editor import (
    PrototypeCompleter,
    highlight,
)


def test_pipe_completion_offers_registry_stages_with_signatures(tmp_path):
    runtime = PrototypeRuntime(Mock(), cwd=tmp_path, environment={})
    try:
        base = ReplCompleter(
            function_help=runtime.callable_help,
            matcher_functions=runtime.matcher_function_names,
        )
        completer = PrototypeCompleter(base)
        options = {
            item.text: item
            for item in completer.get_completions(
                Document("print [] | "), CompleteEvent()
            )
        }
        for name, signature in FILTER_SIGNATURES.items():
            item = options[f"{name}("]
            meta = to_plain_text(item.display_meta)
            assert f"{name}(" in meta
            assert meta.startswith("pipeline stage · ")

        partial = {
            item.text: item
            for item in completer.get_completions(
                Document("print [] | sor"), CompleteEvent()
            )
        }
        assert "sort(" in partial
        assert "sort_by(" in partial
        assert to_plain_text(partial["sort_by("].display_meta) == (
            "pipeline stage · sort_by(callback, reverse=false) (input supplied by |)"
        )
        argument_options = {
            item.text: item
            for item in completer.get_completions(
                Document("print [] | sort_by("), CompleteEvent()
            )
        }
        assert "callback=" in argument_options
        assert "reverse=" in argument_options
        assert "value=" not in argument_options

        multiline = {
            item.display_text
            for item in completer.get_completions(
                Document("print [] |\n  sor"), CompleteEvent()
            )
        }
        assert "sort_by(" in multiline
        assert not list(
            completer.get_completions(
                Document('print "a | b"'), CompleteEvent()
            )
        )
        assert not list(
            completer.get_completions(
                Document("print [] // |"), CompleteEvent()
            )
        )

        help_options = list(
            completer.get_completions(Document("help pi"), CompleteEvent())
        )
        assert any(item.display_text == "pipes" for item in help_options)

        help_result = dispatch_result(runtime.client, "help pipes", runtime)
        assert help_result.success
        for name in FILTER_SIGNATURES:
            assert f"{name}(" in help_result.output
        assert runtime.client.mock_calls == []
    finally:
        runtime.close()


def test_pipe_completion_includes_user_runnables_and_tuple_signatures(tmp_path):
    runtime = PrototypeRuntime(Mock(), cwd=tmp_path, environment={})
    try:
        result = dispatch_result(
            runtime.client,
            'let my_filter(input, arg) = input + arg; '
            'let tuple_filter((name, count), prefix = "") = prefix + name; '
            'let single_filter((item,)) = item',
            runtime,
        )
        assert result.success, result.output
        description = runtime.callable_help()["tuple_filter"]
        assert description.signature == 'tuple_filter((name, count), prefix = "")'
        assert runtime.callable_help()["single_filter"].signature == 'single_filter((item,))'
        assert "strict=true" in runtime.callable_help()["zip"].signature
        assert "fill=null" in runtime.callable_help()["zip_longest"].signature

        completer = PrototypeCompleter(
            ReplCompleter(function_help=runtime.callable_help)
        )
        options = {
            item.text: item
            for item in completer.get_completions(
                Document("print [] | my_"), CompleteEvent()
            )
        }
        assert to_plain_text(options["my_filter("].display_meta) == (
            "pipeline stage · my_filter(arg) (input supplied by |)"
        )
        arguments = {
            item.text
            for item in completer.get_completions(
                Document("print [] | my_filter("), CompleteEvent()
            )
        }
        assert arguments == {"arg="}

        alias = dispatch_result(runtime.client, "let json_alias = json", runtime)
        assert alias.success, alias.output
        assert runtime.callable_help()["json_alias"].signature == "json_alias(value, indent=0)"
    finally:
        runtime.close()


def test_pipeline_separator_is_highlighted_as_an_operator(tmp_path):
    fragments = highlight("print values | map((x) = x)")
    assert ("class:operator", "|") in fragments
    assert ("class:function", "map") in fragments
    assert TOKEN_STYLES["PIPE"] == "operator"


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_private_callables_stay_out_of_expression_and_pipe_suggestions(tmp_path, engine):
    (tmp_path / "helpers.ctk").write_text(
        "let _ctkBase(edge, extra = 1) = edge + extra\n"
        "let __private(edge) = edge\n"
        "let directBases(edge) = _ctkBase(edge)\n"
        "let visibleBase = _ctkBase\n"
        "let _privateData = [1, 2]\n"
    )
    runtime = PrototypeRuntime(Mock(), script_engine=engine, cwd=tmp_path, environment={})
    try:
        result = dispatch_result(runtime.client, 'import "helpers.ctk"', runtime)
        assert result.success, result.output
        base = ReplCompleter(
            references=runtime.completion_references,
            matcher_functions=runtime.matcher_function_names,
            function_help=runtime.callable_help,
        )
        completer = PrototypeCompleter(base)
        for source in (
            "print _", "print __", "print _ctk", "print $_",
            "let found = _", "match _", "match recordDecl(_",
            "print [] | ", "print [] | _", "print [] |\n  _ctk",
            "help _",
        ):
            for adapter in (base, completer):
                choices = {
                    item.display_text
                    for item in adapter.get_completions(Document(source), CompleteEvent())
                }
                assert not any("_ctkBase" in name or "__private" in name for name in choices), (
                    source, choices
                )
        for source in ("print d", "print [] | d"):
            choices = {
                item.text for item in completer.get_completions(Document(source), CompleteEvent())
            }
            assert "directBases(" in choices
        for source in ("print v", "print [] | v"):
            choices = {
                item.text for item in completer.get_completions(Document(source), CompleteEvent())
            }
            assert "visibleBase(" in choices
        # Underscore data bindings and fields keep their normal completion behavior.
        choices = {
            item.text for item in completer.get_completions(Document("print _priv"), CompleteEvent())
        }
        assert "_privateData" in choices
        arguments = {
            item.text for item in completer.get_completions(
                Document("print 2 | _ctkBase("), CompleteEvent()
            )
        }
        assert arguments == {"extra="}
        result = dispatch_result(runtime.client, "print 2 | _ctkBase(extra=3)", runtime)
        assert result.success and result.output == "5"
        result = dispatch_result(runtime.client, "help _ctkBase", runtime)
        assert result.success and "_ctkBase(edge, extra = 1)" in result.output
        assert runtime.client.mock_calls == []
    finally:
        runtime.close()


def test_private_matcher_without_help_cannot_leak_as_a_reference():
    base = ReplCompleter(
        references={"_helper": (), "publicHelper": (), "_data": ("_field",)},
        matcher_functions=("_helper", "publicHelper"),
    )
    for completer in (base, PrototypeCompleter(base)):
        for source in ("match _", "print $_", "print [] | _"):
            choices = {
                item.display_text
                for item in completer.get_completions(Document(source), CompleteEvent())
            }
            assert not any("_helper" in name for name in choices)
        fields = {
            item.text for item in completer.get_completions(Document("print $_data._"), CompleteEvent())
        }
        assert "_field" in fields
