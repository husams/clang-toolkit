from __future__ import annotations

import pytest

from clang_toolkit.cli.runtime.prototype.compiler import compile_program
from clang_toolkit.cli.runtime.prototype.dependencies import execution_trees
from clang_toolkit.cli.runtime.prototype.semantics import Context, EvaluationError
from clang_toolkit.cli.runtime.prototype.syntax import parse
from clang_toolkit.cli.runtime.prototype.tree import evaluate


@pytest.fixture(params=["tree", "compiled"])
def execute(request):
    def run(source: str, context: Context | None = None):
        context = context or Context()
        program = parse(source)
        result = evaluate(program, context) if request.param == "tree" else compile_program(program)(context)
        return result, context
    return run


def test_labels_work_with_positional_calls_aliases_defaults_and_inline_callables(execute) -> None:
    value, _ = execute(
        "let multiply(value, by: m = 2) = value * m; let alias = multiply; "
        "let add = (value, to: amount) = value + amount; "
        "let a = alias 5 by 6; let b = alias(5); let c = add(3, to = 4); [a, b, c]"
    )
    assert value == [30, 10, 7]


def test_label_duplicate_is_rejected_before_argument_effects(execute) -> None:
    seen: list[int] = []
    context = Context(functions={"side": lambda: seen.append(1) or 1})
    with pytest.raises(EvaluationError, match="multiple values"):
        execute("let f(value, by: m) = value + m; f(side(), value = side())", context)
    assert seen == []


def test_unknown_label_is_rejected_before_argument_effects(execute) -> None:
    seen: list[int] = []
    context = Context(functions={"side": lambda: seen.append(1) or 1})
    with pytest.raises(EvaluationError, match="no parameter 'unknown'"):
        execute("let f(value, by: m) = value + m; f(1, unknown = side())", context)
    assert seen == []


def test_local_name_is_not_an_alias_for_an_external_label(execute) -> None:
    seen: list[int] = []
    context = Context(functions={"side": lambda: seen.append(1) or 1})
    with pytest.raises(EvaluationError, match="no parameter 'm'"):
        execute("let f(value, by: m) = value + m; f(1, m = side())", context)
    assert seen == []


def test_multiple_word_labels_are_preflighted_before_argument_effects(execute) -> None:
    seen: list[int] = []
    context = Context(functions={"side": lambda: seen.append(1) or 1})
    with pytest.raises(EvaluationError, match="no parameter 'unknown'"):
        execute("let f(value, from: first, to: second) = value; "
                "f side() from side() to side() unknown side()", context)
    assert seen == []


def test_named_arguments_are_evaluated_in_written_order(execute) -> None:
    seen: list[int] = []
    context = Context(functions={"next": lambda value: seen.append(value) or value})
    value, _ = execute(
        "let pair(from: first, to: second) = [first, second]; "
        "pair(to = next(2), from = next(1))", context
    )
    assert value == [1, 2]
    assert seen == [2, 1]


def test_labeled_defaults_run_in_declaration_order_with_reordered_keywords(execute) -> None:
    value, _ = execute(
        "let combine(base, amount: supplied = 2, previous: before = base + supplied, "
        "total: result = before + supplied) = [before, result]; "
        "combine(amount = 4, base = 3)"
    )
    assert value == [7, 11]


def test_pipeline_injected_slot_duplicate_is_preflighted(execute) -> None:
    seen: list[int] = []
    context = Context(functions={"side": lambda: seen.append(1) or 9})
    with pytest.raises(EvaluationError, match="multiple values"):
        execute("let f(value: item, by: factor) = item * factor; 5 | f(value = side())", context)
    assert seen == []


def test_dependency_admission_visits_omitted_default_and_skips_label_supplied_default() -> None:
    from clang_toolkit.cli.runtime.prototype import repl_language

    omitted = repl_language.parse(
        "let unsafe() = { background functionDecl() }; "
        "let choose(value, backup: fallback = unsafe()) = value; choose(1)"
    )
    omitted_trees = list(execution_trees(omitted, {}))
    assert any(tree.data == "background" for tree in omitted_trees)
    assert any(tree.data == "matcher" for tree in omitted_trees)

    supplied = repl_language.parse(
        "let unsafe() = { background functionDecl() }; "
        "let choose(value, backup: fallback = unsafe()) = value; "
        "choose(1, backup = 2)"
    )
    assert list(execution_trees(supplied, {})) == []


def test_cached_ir_preserves_parameter_labels(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    from clang_toolkit.cli.runtime.prototype import library_cache, repl_language

    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    source = "let f(value, backup: fallback = 2) = value"
    first = library_cache.parse_library(source)
    assert first.children[0].parameter_labels == (None, "backup")

    def unexpected_parse(_source: str):
        raise AssertionError("expected cached syntax")

    monkeypatch.setattr(repl_language, "parse", unexpected_parse)
    second = library_cache.parse_library(source)
    assert second.children[0].parameter_labels == (None, "backup")


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_cached_import_preserves_labels_through_callable_alias(
    monkeypatch: pytest.MonkeyPatch, tmp_path, engine: str,
) -> None:
    from unittest.mock import Mock

    from clang_toolkit.cli.app import dispatch_result
    from clang_toolkit.cli.runtime.imports import preload_libraries
    from clang_toolkit.cli.runtime.prototype import repl_language
    from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime

    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    source = "let multiply(value, by: factor = 2) = value * factor\nlet alias = multiply"
    (tmp_path / "helpers.ctk").write_text(source)

    first = PrototypeRuntime(Mock(), script_engine=engine, cwd=tmp_path, environment={})
    preload_libraries(first, tmp_path)
    first.close()

    original_parse = repl_language.parse

    def reject_warm_parse(text: str):
        assert text != source
        return original_parse(text)

    monkeypatch.setattr(repl_language, "parse", reject_warm_parse)
    second = PrototypeRuntime(Mock(), script_engine=engine, cwd=tmp_path, environment={})
    preload_libraries(second, tmp_path)
    result = dispatch_result(second.client, "alias 5 by 6", second)
    assert result.success, result.output
    assert result.output == "30"
    second.close()
