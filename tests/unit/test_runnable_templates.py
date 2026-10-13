from __future__ import annotations

from unittest.mock import Mock, patch

import pytest

from clang_toolkit.cli.app import dispatch_result
from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime


@pytest.fixture(params=["tree", "compiled"])
def runtime(request, tmp_path):
    instance = PrototypeRuntime(Mock(), script_engine=request.param,
                                cwd=tmp_path, environment={})
    yield instance
    instance.close()


def submit(runtime, source):
    result = dispatch_result(runtime.client, source, runtime)
    assert result.success, result.output
    return result.output


def test_bare_expression_interpolation_and_escaped_braces(runtime):
    assert submit(runtime, 'let n = 6; "answer={n * 7}; {{n}}"') == "answer=42; {n}"
    assert submit(runtime, "'literal {n}'") == "literal {n}"
    assert submit(runtime, 'let obj = {values: [4]}; "{obj.values[0]}"') == "4"


def test_runnable_keeps_interpolation_code_after_cache_eviction(runtime):
    submit(runtime, 'let twice(n) = { n * 2 }; let describe(n) = { "result={twice(n)}" }')
    runtime._prototype_session.cache.clear()
    with patch("clang_toolkit.cli.runtime.prototype.templates.compile_template",
               side_effect=AssertionError("body was reparsed")):
        assert submit(runtime, "describe(21)") == "result=42"


def test_matcher_interpolation_retains_definition_templates(runtime):
    submit(runtime, 'let named(name) = functionDecl(hasName("{name}"))')
    runtime.client.match.return_value = []
    submit(runtime, 'let result = match named("Sample")')
    assert runtime.client.match.call_args.args[0] == 'functionDecl(hasName("Sample"))'


@pytest.mark.parametrize("source", ['"{missing}"', '"{}"', '"{n"', '"}"', '"{let n = 1}"'])
def test_invalid_interpolation_is_reported(runtime, source):
    result = dispatch_result(runtime.client, source, runtime)
    assert not result.success
    assert runtime._scopes == []



@pytest.mark.parametrize("body", ["x + 1", "{ on error 0; x + 1 }"])
def test_inline_arguments_inside_compiled_interpolation(runtime, body):
    submit(runtime, "let apply(operation, value) = operation(value)")
    assert submit(runtime, f'"answer={{apply((x) = {body}, 41)}}"') == "answer=42"
