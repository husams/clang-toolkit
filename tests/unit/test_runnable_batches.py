from __future__ import annotations

import pytest

from clang_toolkit.cli.app import dispatch_result
from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
from clang_toolkit.resources import FileSet, InputDescriptor
from tests.unit.test_console_file_batch_runtime import _Client


@pytest.fixture(params=["tree", "compiled"])
def runtime(request, tmp_path):
    instance = PrototypeRuntime(_Client(), script_engine=request.param,
                                cwd=tmp_path, environment={})
    instance.bindings["inputs"] = FileSet(tuple(InputDescriptor.from_path(path)
                                               for path in ("a.cc", "b.cc")))
    yield instance
    instance.close()


def submit(runtime, source):
    result = dispatch_result(runtime.client, source, runtime)
    assert result.success, result.output
    return result.output


def test_groups_freeze_plain_captures_and_preserve_callable_aliases(runtime):
    submit(runtime, 'let options = {count: 0}; let increment() = { options.count += 1 }; let alias = increment')
    submit(runtime, 'let report = batch chunk in inputs size 1 progress off do { alias() }')
    report = runtime.bindings["report"]
    assert report["completed_groups"] == 2
    assert report["results"] == [1, 1]
    assert runtime.bindings["options"]["count"] == 0
    assert runtime._scopes == []
    assert all(scope.released for scope in runtime.client.scopes)


def test_batch_calls_use_group_parameters_and_compiled_body(runtime):
    submit(runtime, 'let count(items) = { len(items.inputs) }')
    submit(runtime, 'let report = batch chunk in inputs size 1 progress off do { count(chunk) }')
    assert runtime.bindings["report"]["completed_groups"] == 2


def test_bare_names_work_in_file_operations_and_mutation_targets(runtime):
    submit(runtime, 'let open_first(items) = { file open items.inputs[0] into source; file info source }')
    submit(runtime, 'let info = open_first(inputs)')
    assert runtime.bindings["info"]["lease_id"] == "lease-1"
    assert "source" not in runtime.bindings
    submit(runtime, 'let options = {items: [1]}; options.items.push(2); set options.items[0] = 7')
    assert runtime.bindings["options"]["items"] == [7, 2]


@pytest.mark.parametrize("definition, call", [
    ('let unsafe() = { background functionDecl() }', 'unsafe()'),
    ('let unsafe() = { background functionDecl() }; let alias = unsafe', 'alias()'),
    ('let unsafe() = { background functionDecl() }; let apply(operation) = { operation() }', 'apply(unsafe)'),
    ('let unsafe() = { ctk("resource status") }', 'unsafe()'),
    ('let unsafe() = { background functionDecl() }; let template() = { "{unsafe()}" }', 'template()'),
])
def test_reachable_unsafe_calls_are_rejected_before_admission(runtime, definition, call):
    submit(runtime, definition)
    result = dispatch_result(runtime.client,
                             f'let report = batch chunk in inputs size 1 progress off do {{ {call} }}', runtime)
    assert not result.success and "foreground" in result.output
    assert runtime.client.scopes == []


def test_callables_cannot_escape_as_batch_results_or_exports(runtime):
    submit(runtime, 'let operation() = { 1 }')
    result = dispatch_result(runtime.client,
                             'let report = batch chunk in inputs size 1 progress off do { operation }', runtime)
    assert result.success
    assert runtime.bindings["report"]["failed_groups"] == 1
    assert runtime.bindings["report"]["results"] == []
    assert all(scope.released for scope in runtime.client.scopes)
    result = dispatch_result(runtime.client, 'save operation to "out.json" as json', runtime)
    assert not result.success
    assert not (runtime.cwd / "out.json").exists()


def test_requirements_ignore_dormant_bodies_and_follow_reachable_calls(runtime):
    session = runtime._prototype_session
    assert not session.requirements('let dormant() = { background functionDecl() }').background_query
    submit(runtime, 'let operation() = { background functionDecl() }; let alias = operation')
    assert session.requirements('alias()').background_query
    assert session.requirements('let helper() = { background functionDecl() }; helper()').background_query


def test_omitted_defaults_are_inspected_before_batch_admission(runtime):
    submit(runtime, 'let unsafe() = { background functionDecl() }; let apply(operation = unsafe) = { operation() }')
    result = dispatch_result(runtime.client, 'let report = batch chunk in inputs size 1 progress off do { apply() }', runtime)
    assert not result.success and "foreground" in result.output
    assert runtime.client.scopes == []
    assert not runtime._prototype_session.requirements('let dormant(a = unsafe()) = { a }').background_query
    assert runtime._prototype_session.requirements('let call(a = unsafe()) = { a }; call()').background_query
    assert not runtime._prototype_session.requirements('apply(null)').background_query
