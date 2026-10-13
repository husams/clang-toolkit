from __future__ import annotations

from unittest.mock import Mock

import pytest

from clang_toolkit.cli.app import dispatch_result
from clang_toolkit.cli.runtime.imports import preload_libraries
from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime


@pytest.fixture(params=["tree", "compiled"])
def runtime(request, tmp_path):
    instance = PrototypeRuntime(Mock(), script_engine=request.param,
                                cwd=tmp_path, environment={})
    yield instance
    instance.close()


def test_imports_register_dormant_runnables_and_aliases(runtime):
    (runtime.cwd / "lib.ctk").write_text(
        'let prefix = "Hello"\n'
        'let greet(name) = { "{prefix}{name}" }\n'
        'let alias = greet\n'
        'let dormant() = { resource status }\n')
    result = dispatch_result(runtime.client, 'import "lib.ctk"', runtime)
    assert result.success, result.output
    assert result.output == ""
    runtime.client.resource_status.assert_not_called()
    assert dispatch_result(runtime.client, 'alias("Ada")', runtime).output == "HelloAda"


def test_preloads_compile_bodies_and_nested_imports(runtime):
    (runtime.cwd / "parts").mkdir()
    (runtime.cwd / "parts" / "inner.ctk").write_text('let add(a, b) = { a + b }')
    (runtime.cwd / "lib.ctk").write_text('import "parts/inner.ctk"\nlet operation = add')
    preload_libraries(runtime, runtime.cwd)
    result = dispatch_result(runtime.client, 'operation(19, 23)', runtime)
    assert result.success and result.output == "42"


def test_failed_import_restores_definitions_and_containers(runtime):
    original = [1]
    runtime.bindings["items"] = original
    (runtime.cwd / "bad.ctk").write_text(
        'let modify() = { items.push(2) }\n'
        'let changed = modify()\nlet invalid = missing')
    result = dispatch_result(runtime.client, 'import "bad.ctk"', runtime)
    assert not result.success and "bad.ctk:3" in result.output
    assert runtime.bindings == {"items": [1]}
    assert runtime.bindings["items"] is original
    assert runtime._scopes == [] and runtime._import_stack == []


def test_import_validates_entire_library_before_running(runtime):
    (runtime.cwd / "invalid.ctk").write_text('let value = 1\nprint value')
    result = dispatch_result(runtime.client, 'import "invalid.ctk"', runtime)
    assert not result.success and "libraries accept let definitions" in result.output
    assert runtime.bindings == {}


def test_imported_body_error_retains_library_source_name(runtime):
    (runtime.cwd / "divide.ctk").write_text('let divide(n) = { 1 / n }')
    assert dispatch_result(runtime.client, 'import "divide.ctk"', runtime).success
    result = dispatch_result(runtime.client, "divide(0)", runtime)
    assert not result.success and "divide.ctk" in result.output
    assert "defined at line 1" in result.output and "called at line 1" in result.output


def test_failed_import_restores_mutable_captures_of_escaping_closures(runtime):
    assert dispatch_result(runtime.client,
                           'let make() = { let data = {count: 0}; let increment() = { data.count += 1 }; increment }; '
                           'let counter = make()', runtime).success
    (runtime.cwd / "bad.ctk").write_text('let changed = counter()\nlet invalid = missing')
    assert not dispatch_result(runtime.client, 'import "bad.ctk"', runtime).success
    assert dispatch_result(runtime.client, 'counter()', runtime).output == "1"


def test_library_syntax_error_uses_library_source(runtime):
    (runtime.cwd / "syntax.ctk").write_text('let value = 1\nlet malformed = @')
    result = dispatch_result(runtime.client, 'import "syntax.ctk"', runtime)
    assert not result.success and "syntax.ctk" in result.output
    assert "line 2" in result.output


def test_imported_defaults_and_handlers_retain_compiled_code(runtime):
    (runtime.cwd / "handlers.ctk").write_text('let divide(lhs, rhs = 1) = { on error 0; on exit 99; lhs / rhs }\n')
    assert dispatch_result(runtime.client, 'import "handlers.ctk"', runtime).success
    for value in range(65):
        assert dispatch_result(runtime.client, f"let unused = {value}", runtime).success
    assert dispatch_result(runtime.client, "let answer = [divide(10), divide(10, 0)]", runtime).success
    assert runtime.bindings["answer"] == [10, 0]
