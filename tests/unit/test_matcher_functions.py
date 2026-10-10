from unittest.mock import Mock

import pytest

from clang_toolkit.client import Client
from clang_toolkit.cli.app import dispatch
from clang_toolkit.cli.runtime import Runtime
from clang_toolkit.cli.runtime.matcher_functions import MatcherFunction


@pytest.fixture
def runtime(tmp_path):
    client = Mock(spec=Client)
    client.match.return_value = []
    session = Runtime(client, cwd=tmp_path, environment={})
    yield session
    session.close()


def test_definition_is_quiet_and_calls_expand_before_requests(runtime):
    assert runtime.execute('let matcher(name) = functionDecl(hasName($name))') == ""
    assert isinstance(runtime.bindings["matcher"], MatcherFunction)
    assert runtime.execute("$matcher") == "matcher(name)"
    runtime.execute('match matcher("xxx")')
    runtime.client.match.assert_called_once_with(
        'functionDecl(hasName("xxx"))', files=None,
        working_directory=runtime.cwd, compile_arguments=[],
    )
    assert not runtime._scopes


def test_nested_calls_parameters_and_bindings_stay_typed(runtime):
    runtime.execute("let named(name) = hasName($name)")
    runtime.execute("let functions(name, predicate) = functionDecl(named($name), $predicate)")
    runtime.execute('let first = functions("alpha", isDefinition()).bind("fn")')
    runtime.execute('let second = functions("beta", isImplicit())')
    assert runtime.execute("$first") == 'functionDecl(hasName("alpha"), isDefinition()).bind("fn")'
    assert runtime.execute("$second") == 'functionDecl(hasName("beta"), isImplicit())'
    runtime.client.match.assert_not_called()


def test_nested_expansion_never_sends_unexpanded_function_source(runtime):
    runtime.execute('let named(name) = hasName($name)')
    runtime.execute('match functionDecl(named("xxx"))')
    assert runtime.client.match.call_args.args == ('functionDecl(hasName("xxx"))',)


def test_background_query_expands_routines_before_starting(runtime):
    runtime.execute('let named(name) = functionDecl(hasName($name))')
    runtime.execute('background named("xxx") in ["sample.cc"]')
    runtime.client.start_background_query.assert_called_once_with(
        'functionDecl(hasName("xxx"))', [str(runtime.cwd / "sample.cc")],
        working_directory=runtime.cwd, compile_arguments=[],
    )


def test_arguments_fields_interpolation_and_outer_variables(runtime):
    runtime.bindings["record"] = {"name": "outside"}
    runtime.execute('let name = "outer"')
    runtime.execute('let named(name) = functionDecl(hasName("prefix_${name}"))')
    runtime.execute('let value = named($record.name)')
    assert runtime.execute("$value") == 'functionDecl(hasName("prefix_outside"))'
    assert runtime.execute("$name") == "outer"
    assert not runtime._scopes


def test_zero_parameters_and_body_bind_can_be_overridden(runtime):
    runtime.execute('let definitions() = functionDecl(isDefinition()).bind("original")')
    runtime.execute('let value = definitions().bind("selected")')
    assert runtime.execute("$value") == 'functionDecl(isDefinition()).bind("selected")'


@pytest.mark.parametrize("call", ['named()', 'named("a", "b")'])
def test_wrong_arity_preserves_existing_assignment_and_scope(runtime, call):
    runtime.execute('let named(name) = functionDecl(hasName($name))')
    runtime.execute('let value = "previous"')
    assert "expects 1 argument" in dispatch(runtime.client, f"let value = {call}", runtime)
    assert runtime.bindings["value"] == "previous"
    assert not runtime._scopes
    runtime.client.match.assert_not_called()


def test_invalid_definitions_preserve_old_binding(runtime):
    runtime.execute('let named(name) = functionDecl(hasName($name))')
    previous = runtime.bindings["named"]
    assert "duplicate parameter" in dispatch(runtime.client, 'let named(name, name) = functionDecl()', runtime)
    assert runtime.bindings["named"] is previous
    assert "built-in matcher name" in dispatch(runtime.client, 'let functionDecl(name) = functionDecl()', runtime)


def test_failure_and_recursion_restore_local_scopes(runtime):
    runtime.execute('let broken(name) = functionDecl(hasName($missing))')
    assert "unknown variable" in dispatch(runtime.client, 'let value = broken("x")', runtime)
    runtime.execute('let recursive(name) = recursive($name)')
    assert "call depth exceeds" in dispatch(runtime.client, 'let value = recursive("x")', runtime)
    assert not runtime._scopes
    assert runtime._matcher_call_depth == 0


def test_routine_result_must_be_a_matcher_and_root_rule_is_retained(runtime):
    runtime.execute('let identity(value) = $value')
    assert "must return a matcher" in dispatch(runtime.client, 'let result = identity("x")', runtime)
    runtime.execute('let named(name) = hasName($name)')
    assert "top-level matcher" in dispatch(runtime.client, 'match named("xxx")', runtime)
    runtime.client.match.assert_not_called()


def test_other_variables_resolve_at_call_time_and_parameters_allow_fields(runtime):
    runtime.execute('let prefix = "one"')
    runtime.execute('let named(record) = functionDecl(hasName("${prefix}_${record.name}"))')
    runtime.bindings["record"] = {"name": "value"}
    runtime.execute('let first = named($record)')
    runtime.execute('let prefix = "two"')
    runtime.execute('let second = named($record)')
    assert runtime.execute("$first") == 'functionDecl(hasName("one_value"))'
    assert runtime.execute("$second") == 'functionDecl(hasName("two_value"))'


def test_definition_in_local_scope_does_not_leak(runtime):
    runtime._scopes.append({})
    try:
        runtime.execute('let named(name) = functionDecl(hasName($name))')
        assert runtime.matcher_function_names() == ("named",)
        runtime.execute('let value = named("xxx")')
        assert "named" not in runtime.bindings
    finally:
        runtime._scopes.pop()
    assert runtime.matcher_function_names() == ()


def test_completion_tracks_defined_routines(runtime):
    from prompt_toolkit.document import Document
    from clang_toolkit.cli.completion import ReplCompleter

    completer = ReplCompleter(matcher_functions=runtime.matcher_function_names)
    def choices(source):
        return [choice.text for choice in completer.get_completions(Document(source), None)]

    root_candidates = choices("match named")
    value_candidates = choices("let value = named")
    assert "named(" not in root_candidates
    runtime.execute('let named(name) = functionDecl(hasName($name))')
    assert set(choices("match named")) == set(root_candidates) | {"named("}
    assert set(choices("let value = named")) == set(value_candidates) | {"named("}
    assert "named(" in choices("match functionDecl(")
    runtime.execute("let named = 3")
    assert choices("match named") == root_candidates
