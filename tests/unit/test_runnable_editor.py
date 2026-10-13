from __future__ import annotations

from unittest.mock import Mock

from prompt_toolkit.completion import CompleteEvent
from prompt_toolkit.document import Document

from clang_toolkit.cli.app import dispatch_result
from clang_toolkit.cli.completion import ReplCompleter
from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
from clang_toolkit.cli.runtime.prototype.repl_editor import PrototypeCompleter, input_state, lex


def test_bare_bindings_calls_and_fields_complete_without_prefixes(tmp_path):
    runtime = PrototypeRuntime(Mock(), cwd=tmp_path, environment={})
    try:
        result = dispatch_result(runtime.client, 'let options = {minimum: 2}; let count(value) = { value }', runtime)
        assert result.success
        completer = PrototypeCompleter(ReplCompleter(
            references=runtime.completion_references,
            field_resolver=runtime.completion_suggestions,
            matcher_functions=runtime.matcher_function_names))
        def suggestions(source):
            return {item.text for item in completer.get_completions(Document(source), CompleteEvent())}
        assert "options" in suggestions("let answer = opt")
        assert "count(" in suggestions("cou")
        assert "minimum" in suggestions("options.mi")
        assert "minimum" in suggestions("options.")
        assert all("$" not in item for item in suggestions("match "))
    finally:
        runtime.close()


def test_runnable_multiline_editor_is_lossless_and_requests_completion():
    source = 'let scale(value, factor) = {\n value * factor\n}'
    assert ''.join(str(token) for token in lex(source)) == source
    assert not input_state(source).needs_more
    assert input_state('let scale(value, factor) = {\n value * factor').needs_more


def test_help_uses_let_bare_names_and_compiled_body_contract(tmp_path):
    runtime = PrototypeRuntime(Mock(), cwd=tmp_path, environment={})
    try:
        result = dispatch_result(runtime.client, "help let", runtime)
        assert result.success and "Python AST" in result.output
        assert "let twice(value) = { value * 2 }" in result.output
        assert "$" not in result.output
        assert "$" not in dispatch_result(runtime.client, "help match", runtime).output
    finally:
        runtime.close()
