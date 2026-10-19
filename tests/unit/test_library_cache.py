"""Library caches survive runtime restarts while definitions execute afresh."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock

import pytest

from clang_toolkit.cli.app import dispatch_result
from clang_toolkit.cli.runtime import EvaluationError
from clang_toolkit.cli.runtime.imports import preload_libraries
from clang_toolkit.cli.runtime.prototype import library_cache, repl_language
from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime


@pytest.fixture(autouse=True)
def isolated_cache(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))


def runtime(directory: Path, engine: str = "compiled") -> PrototypeRuntime:
    return PrototypeRuntime(Mock(), script_engine=engine, cwd=directory, environment={})


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_restart_uses_cached_syntax_with_fresh_bindings_and_callable_help(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, engine: str,
) -> None:
    definition = 'let greet(name, suffix = "!") = { "{prefix}{name}{suffix}" }'
    (tmp_path / "helpers.ctk").write_text('let prefix = $arg.prefix\n' + definition)
    first = runtime(tmp_path, engine)
    first.bindings["arg"] = {"prefix": "Hello "}
    preload_libraries(first, tmp_path)
    first.close()

    original_parse = repl_language.parse
    # Interpolation expressions are tiny and compiled afresh alongside Python code.
    def no_library_parse(source: str):
        assert source != 'let prefix = $arg.prefix\n' + definition
        return original_parse(source)
    monkeypatch.setattr(repl_language, "parse", no_library_parse)
    second = runtime(tmp_path, engine)
    second.bindings["arg"] = {"prefix": "Hi "}
    preload_libraries(second, tmp_path)
    assert dispatch_result(second.client, 'greet("Ada")', second).output == "Hi Ada!"
    assert second.callable_help()["greet"].definition == definition
    assert second.callable_help()["greet"].signature == 'greet(name, suffix = "!")'
    second.close()


def test_source_change_invalidates_even_with_same_size_and_mtime(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    import os

    source = tmp_path / "values.ctk"
    source.write_text("let answer = 41")
    first = runtime(tmp_path)
    preload_libraries(first, tmp_path)
    first.close()
    old_stat = source.stat()
    source.write_text("let answer = 42")
    os.utime(source, ns=(old_stat.st_atime_ns, old_stat.st_mtime_ns))
    parse = Mock(wraps=repl_language.parse)
    monkeypatch.setattr(repl_language, "parse", parse)
    second = runtime(tmp_path)
    preload_libraries(second, tmp_path)
    assert second.bindings["answer"] == 42
    parse.assert_called_once_with("let answer = 42")
    second.close()


def test_grammar_or_compiler_change_invalidates_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    source = "let answer = 42"
    library_cache.parse_library(source)
    monkeypatch.setattr(library_cache, "_fingerprint", lambda: "new-runtime-version")
    parse = Mock(wraps=repl_language.parse)
    monkeypatch.setattr(repl_language, "parse", parse)
    library_cache.parse_library(source)
    parse.assert_called_once_with(source)


@pytest.mark.parametrize("damage", ["truncated", "invalid-record", "wrong-format", "changed-value"])
def test_damaged_cache_reparses_and_repairs(monkeypatch: pytest.MonkeyPatch, damage: str) -> None:
    import json

    source = "let answer = 42"
    library_cache.parse_library(source)
    destination = next(library_cache._directory().glob("*.json"))
    payload = json.loads(destination.read_text())
    if damage == "truncated":
        destination.write_text('{"program":')
    elif damage == "invalid-record":
        payload["program"] = ["invalid"]
        destination.write_text(json.dumps(payload))
    elif damage == "wrong-format":
        payload["format"] = -1
        destination.write_text(json.dumps(payload))
    else:
        destination.write_text(destination.read_text().replace('"answer"', '"result"'))
    parse = Mock(wraps=repl_language.parse)
    monkeypatch.setattr(repl_language, "parse", parse)
    library_cache.parse_library(source)
    parse.assert_called_once_with(source)
    parse.reset_mock()
    library_cache.parse_library(source)
    parse.assert_not_called()


def test_unwritable_cache_is_optional(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    blocked = tmp_path / "blocked"
    blocked.write_text("file in place of directory")
    monkeypatch.setenv("XDG_CACHE_HOME", str(blocked))
    (tmp_path / "values.ctk").write_text("let answer = 42")
    instance = runtime(tmp_path)
    preload_libraries(instance, tmp_path)
    assert instance.bindings["answer"] == 42
    assert blocked.read_text() == "file in place of directory"
    instance.close()


def test_nested_imports_reexecute_and_detect_changed_dependencies(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    parts = tmp_path / "parts"
    parts.mkdir()
    dependency = parts / "constant.ctk"
    dependency.write_text("let answer = 41")
    parent = 'import "parts/constant.ctk"\nlet selected = answer'
    (tmp_path / "helpers.ctk").write_text(parent)
    first = runtime(tmp_path)
    preload_libraries(first, tmp_path)
    first.close()
    dependency.write_text("let answer = 42")
    parse = Mock(wraps=repl_language.parse)
    monkeypatch.setattr(repl_language, "parse", parse)
    second = runtime(tmp_path)
    preload_libraries(second, tmp_path)
    assert second.bindings["selected"] == 42
    parse.assert_called_once_with("let answer = 42")
    second.close()


def test_warm_cache_keeps_validation_rollback_and_library_error_location(tmp_path: Path) -> None:
    library = tmp_path / "invalid.ctk"
    library.write_text("let answer = 42\nlet invalid = missing")
    for _ in range(2):
        instance = runtime(tmp_path)
        with pytest.raises(EvaluationError, match=r"invalid.ctk:2:.*missing"):
            preload_libraries(instance, tmp_path)
        assert instance.bindings == {}
        assert instance._import_stack == []
        instance.close()
    library.write_text("let answer = 42\nprint answer")
    for _ in range(2):
        instance = runtime(tmp_path)
        with pytest.raises(EvaluationError, match=r"invalid.ctk:2: libraries accept"):
            preload_libraries(instance, tmp_path)
        assert instance.bindings == {}
        instance.close()


def test_cache_prunes_old_entries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(library_cache, "_MAX_ENTRIES", 2)
    for value in range(3):
        library_cache.parse_library(f"let answer = {value}")
    assert len(list(library_cache._directory().glob("*.json"))) == 2
    assert not list(library_cache._directory().glob(".script-*"))


def test_warm_library_loads_python_without_lowering(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from clang_toolkit.cli.runtime.prototype import compiler

    source = 'let offset = arg.offset\nlet add(value) = { value + offset }'
    (tmp_path / "helpers.ctk").write_text(source)
    first = runtime(tmp_path)
    first.bindings["arg"] = {"offset": 2}
    preload_libraries(first, tmp_path)
    first.close()
    assert list(library_cache._directory().glob("*.python.json"))

    def no_lowering(self):
        pytest.fail("warm library must load generated Python")
    with monkeypatch.context() as warm:
        warm.setattr(compiler._Lowerer, "module", no_lowering)
        second = runtime(tmp_path)
        second.bindings["arg"] = {"offset": 40}
        preload_libraries(second, tmp_path)
    assert dispatch_result(second.client, "add(2)", second).output == "42"
    second.close()


@pytest.mark.parametrize("damage", ["truncated", "python", "permissions", "wrong-body"])
def test_damaged_python_cache_recompiles(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, damage: str) -> None:
    from clang_toolkit.cli.runtime.prototype import compiler

    (tmp_path / "helpers.ctk").write_text("let answer = 42")
    first = runtime(tmp_path)
    preload_libraries(first, tmp_path)
    first.close()
    destination = next(library_cache._directory().glob("*.python.json"))
    if damage == "truncated":
        destination.write_text("{")
    elif damage == "python":
        destination.write_text(destination.read_text().replace("42", "99"))
    elif damage == "wrong-body":
        destination.write_text('{"body": [], "digest": "invalid"}')
    else:
        destination.chmod(0o666)
    original = compiler._Lowerer.module
    calls = []
    def lower(self):
        calls.append(True)
        return original(self)
    monkeypatch.setattr(compiler._Lowerer, "module", lower)
    second = runtime(tmp_path)
    preload_libraries(second, tmp_path)
    assert calls
    assert second.bindings["answer"] == 42
    second.close()


def test_python_cache_preserves_host_metadata_and_imports(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    parts = tmp_path / "parts"
    parts.mkdir()
    (parts / "prefix.ctk").write_text('let prefix = "Hi "')
    (tmp_path / "helpers.ctk").write_text(
        'import "parts/prefix.ctk"\nlet greet(name) = { "{prefix}{name}" }'
    )
    for _ in range(2):
        instance = runtime(tmp_path)
        preload_libraries(instance, tmp_path)
        assert dispatch_result(instance.client, 'greet("Ada")', instance).output == "Hi Ada"
        instance.close()


def test_warm_templates_and_host_blocks_skip_parsing_and_lowering(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from clang_toolkit.cli.runtime.prototype import compiler

    (tmp_path / "helpers.ctk").write_text(
        'let greet(name) = { "Hi {name}" }\n'
        'let functions(target) = {\nlet rows = match functionDecl() in target\nrows\n}'
    )
    first = runtime(tmp_path)
    preload_libraries(first, tmp_path)
    first.close()
    with monkeypatch.context() as warm:
        warm.setattr(repl_language, "parse", Mock(side_effect=AssertionError("unexpected parse")))
        warm.setattr(compiler._Lowerer, "module", Mock(side_effect=AssertionError("unexpected lowering")))
        second = runtime(tmp_path)
        preload_libraries(second, tmp_path)
    assert dispatch_result(second.client, 'greet("Ada")', second).output == "Hi Ada"
    assert "functions" in second.bindings
    second.close()


def test_warm_slice_library_reuses_compiled_python(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from clang_toolkit.cli.runtime.prototype import compiler

    (tmp_path / "helpers.ctk").write_text("let tail(values) = { values[1:] }")
    first = runtime(tmp_path)
    preload_libraries(first, tmp_path)
    first.close()
    with monkeypatch.context() as warm:
        warm.setattr(compiler._Lowerer, "module", Mock(side_effect=AssertionError("unexpected lowering")))
        second = runtime(tmp_path)
        preload_libraries(second, tmp_path)
    assert dispatch_result(second.client, "tail([1, 2, 3])", second).output == "2\n3"
    second.close()
