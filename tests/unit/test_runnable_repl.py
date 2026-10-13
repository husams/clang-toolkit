from __future__ import annotations

from unittest.mock import Mock

import pytest

from clang_toolkit.cli.app import dispatch_result
from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
from clang_toolkit.cli.runtime.prototype.runnables import RunnableBlock
from clang_toolkit.cli.runtime.matcher_functions import MatcherFunction
from clang_toolkit.cli.runtime.values import MatchSet
from clang_toolkit.client import Client


@pytest.fixture(params=["tree", "compiled"])
def runtime(request, tmp_path):
    instance = PrototypeRuntime(Client(), script_engine=request.param,
                                cwd=tmp_path, environment={})
    yield instance
    instance.close()
    instance.client.close()


def submit(runtime, source):
    result = dispatch_result(runtime.client, source, runtime)
    assert result.success, result.output
    return result.output


def test_definitions_and_calls_across_submissions(runtime):
    assert submit(runtime, "let twice(value) = { value * 2 }") == ""
    assert submit(runtime, "let answer = twice(21); print answer") == "42"
    assert submit(runtime, 'let hello() = { print "ready" }; hello()') == "ready"
    assert submit(runtime, "let alias = twice; alias(3)") == "6"


def test_bare_matcher_parameters_and_arguments(runtime):
    (runtime.cwd / "sample.cc").write_text("void Sample() {}\n")
    submit(runtime, "let named(name) = functionDecl(hasName(name))")
    runtime._match_target = Mock(return_value=MatchSet(()))
    submit(runtime, 'let find(path, name) = { match named(name) in path }')
    submit(runtime, 'let result = find("sample.cc", "Sample")')
    assert runtime._match_target.call_args.args[0] == 'functionDecl(hasName("Sample"))'
    assert runtime._match_target.call_args.args[1] == "sample.cc"


def test_runnable_returns_matcher_in_native_matcher_positions(runtime):
    submit(runtime, 'let named(name) = { functionDecl(hasName(name)) }')
    runtime.client.match = Mock(return_value=[])
    submit(runtime, 'let result = match named("Sample").bind("root")')
    assert runtime.client.match.call_args.args[0] == 'functionDecl(hasName("Sample")).bind("root")'
    submit(runtime, 'let value() = { 7 }')
    result = dispatch_result(runtime.client, 'match value()', runtime)
    assert not result.success and "match requires a matcher expression" in result.output


def test_runnable_values_compose_with_matcher_arguments_and_commands(runtime):
    submit(runtime, 'let name() = { "Sample" }; let target() = { "sample.cc" }')
    runtime.client.match = Mock(return_value=[])
    submit(runtime, 'let result = match functionDecl(hasName(name()))')
    assert runtime.client.match.call_args.args[0] == 'functionDecl(hasName("Sample"))'
    runtime.client.parse = Mock(return_value="parsed result")
    submit(runtime, 'let tree = parse target()')
    assert runtime.client.parse.call_args.args[0] == "sample.cc"


def test_definition_source_and_host_scope_survive_later_submission(runtime):
    submit(runtime, 'let make(name) = { let matcher() = { functionDecl(hasName(name)) }; matcher }')
    submit(runtime, 'let operation = make("Sample")')
    submit(runtime, "let predicate = operation()")
    assert runtime.bindings["predicate"].name == "functionDecl"
    assert runtime.bindings["predicate"].arguments[0].arguments == ("Sample",)


def test_invalid_redefinition_and_call_cleanup(runtime):
    submit(runtime, "let value = 7; let change() = { value /= 0 }")
    result = dispatch_result(runtime.client, "let value = change()", runtime)
    assert not result.success and "zero" in result.output
    assert runtime.bindings["value"] == 7
    assert runtime._scopes == []
    assert runtime._matcher_call_depth == 0


def test_auxiliary_native_matchers_are_not_parsed_as_runnable_calls(runtime):
    submit(runtime, 'let edges = cxxBaseSpecifier(hasType(cxxRecordDecl().bind("base")))')
    assert runtime.bindings["edges"].name == "cxxBaseSpecifier"
    result = dispatch_result(runtime.client, 'let cxxBaseSpecifier() = { 1 }', runtime)
    assert not result.success and "built-in callable" in result.output


def test_handlers_defaults_and_cleanup_display_across_submissions(runtime):
    assert submit(runtime, 'let divide(lhs, rhs = 1) = { on error 0; on exit { print "clean" }; lhs / rhs }') == ""
    assert submit(runtime, 'divide(10)') == "clean\n10.0"
    assert submit(runtime, 'divide(10, 0)') == "clean\n0"
    assert submit(runtime, 'let value = divide(10, 0); print value') == "0"
    assert submit(runtime, 'divide(10) on error 99') == "clean\n10.0"
    assert submit(runtime, '1 / 0 on error { print "handled"; 9 }') == "handled\n9"
    assert runtime._scopes == []


def test_loop_handlers_accept_native_host_actions(runtime):
    assert submit(runtime, 'let events = []; let values = foreach item in [1, 0, 2] do { on error continue; on exit { events.push(item) }; 10 / item }; print "{values.length}:{events.length}"') == "2:3"


def test_expression_definitions_and_calls_across_submissions(runtime):
    assert submit(runtime, "let add (l, r = 1) = l + r") == ""
    assert submit(runtime, "let inc(x) = add(x, 1); let constant(x) = add(1, 2)") == ""
    assert submit(runtime, "let identity(x) = x; let add_if(l, h) = if l < h then l + h else 0") == ""
    assert all(isinstance(runtime.bindings[name], RunnableBlock)
               for name in ("add", "inc", "constant", "identity", "add_if"))
    assert submit(runtime, '[add(2), inc(4), constant(9), identity(7), add_if(2, 5), add_if(5, 2)]') == "3\n5\n3\n7\n7\n0"
    assert submit(runtime, 'let divide(x) = (10 / x) on error 0; divide(0)') == "0"


def test_expression_runnables_preserve_builtin_matcher_templates(runtime):
    submit(runtime, 'let named(name) = functionDecl(hasName(name))')
    assert isinstance(runtime.bindings["named"], MatcherFunction)
    submit(runtime, 'let wrapped(name) = named(name)')
    assert isinstance(runtime.bindings["wrapped"], RunnableBlock)
    runtime.client.match = Mock(return_value=[])
    submit(runtime, 'let rows = match wrapped("Sample").bind("root")')
    assert runtime.client.match.call_args.args[0] == 'functionDecl(hasName("Sample")).bind("root")'



def test_inline_callback_can_return_a_native_matcher(runtime):
    submit(runtime, "let apply(operation, name) = operation(name)")
    submit(runtime, 'let selected(name) = apply((value) = functionDecl(hasName(value)), name)')
    runtime.client.match = Mock(return_value=[])
    submit(runtime, 'let result = match selected("Sample").bind("root")')
    assert runtime.client.match.call_args.args[0] == 'functionDecl(hasName("Sample")).bind("root")'
