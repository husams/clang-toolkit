from __future__ import annotations

from unittest.mock import Mock

import pytest
from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import to_plain_text

from clang_toolkit.cli.app import dispatch_result
from clang_toolkit.cli.callable_help import CallableHelp
from clang_toolkit.cli.completion import ReplCompleter
from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
from clang_toolkit.cli.runtime.prototype.repl_editor import PrototypeCompleter


@pytest.fixture(params=["tree", "compiled"])
def runtime(request, tmp_path):
    value = PrototypeRuntime(
        Mock(), script_engine=request.param, cwd=tmp_path, environment={}
    )
    try:
        yield value
    finally:
        value.close()


def test_callable_help_displays_public_labels_locals_and_defaults(runtime):
    result = dispatch_result(
        runtime.client,
        "let multiply(value, by: m = 2) = value * m; let shorthand(value, by:) = value * by",
        runtime,
    )
    assert result.success, result.output
    descriptions = runtime.callable_help()
    assert descriptions["multiply"].signature == "multiply(value, by: m = 2)"
    assert descriptions["multiply"].pipeline_signature == "multiply(by: m = 2)"
    assert descriptions["multiply"].parameter_names == ("value", "by")
    assert descriptions["multiply"].pipeline_parameters == ("by",)
    assert descriptions["shorthand"].signature == "shorthand(value, by: by)"

    help_result = dispatch_result(runtime.client, "help multiply", runtime)
    assert help_result.success
    assert "Signature:\n  multiply(value, by: m = 2)" in help_result.output


def test_named_and_pipeline_completion_uses_public_labels(runtime):
    result = dispatch_result(
        runtime.client,
        "let multiply(value, by: m = 2) = value * m",
        runtime,
    )
    assert result.success, result.output
    completer = PrototypeCompleter(
        ReplCompleter(function_help=runtime.callable_help)
    )

    def options(source: str):
        return {
            item.text: item
            for item in completer.get_completions(Document(source), CompleteEvent())
        }

    named = options("let answer = multiply(5, b")
    assert "by=" in named
    assert "m=" not in named
    assert to_plain_text(named["by="].display_meta) == "argument · multiply"

    pipeline = options("print 5 | multiply b")
    assert "by " in pipeline
    assert to_plain_text(pipeline["by "].display_meta) == (
        "stage label · multiply (input supplied by |)"
    )

    pipeline_named = options("print 5 | multiply(b")
    assert "by=" in pipeline_named
    assert "m=" not in pipeline_named


def test_pipeline_completion_keeps_labels_after_destructured_input(runtime):
    result = dispatch_result(
        runtime.client,
        "let f((a, b), by: m) = a + b + m",
        runtime,
    )
    assert result.success, result.output
    description = runtime.callable_help()["f"]
    assert description.pipeline_signature == "f(by: m)"
    assert description.pipeline_parameters == ("by",)
    completer = PrototypeCompleter(
        ReplCompleter(function_help=runtime.callable_help)
    )
    options = {
        item.text
        for item in completer.get_completions(
            Document("print [1, 2] | f b"), CompleteEvent()
        )
    }
    assert "by " in options


def test_named_argument_completion_keeps_expression_candidates():
    completer = PrototypeCompleter(
        ReplCompleter(
            references={"record": ()},
            function_help={
                "f": CallableHelp(
                    "f", "f(value, by: amount)", "value + amount",
                    pipeline_signature="f(by: amount)",
                    pipeline_parameters=("by",),
                    parameter_names=("value", "by"),
                )
            },
        )
    )
    for source in ("f(", "f(1, ", "f(rec", "f(1, rec"):
        options = {
            item.text
            for item in completer.get_completions(Document(source), CompleteEvent())
        }
        assert "record" in options
        if source in {"f(", "f(1, "}:
            assert "by=" in options
