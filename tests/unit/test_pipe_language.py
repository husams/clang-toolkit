from __future__ import annotations

import pytest

from clang_toolkit.cli.runtime.prototype import run_source


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_pipe_stages_are_left_associative_and_inject_as_first_argument(engine: str) -> None:
    result = run_source(
        'let add(a, b) = $a + $b\nlet result = 2 | add(3) | add(4)\n$result',
        engine=engine,
    )
    assert result.value == 9


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_pipe_accepts_bare_and_called_stages(engine: str) -> None:
    result = run_source(
        'let inc(x) = $x + 1\nlet twice(x) = $x * 2\n3 | inc | twice()',
        engine=engine,
    )
    assert result.value == 8


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_named_arguments_work_for_runnables_and_pipe_stages(engine: str) -> None:
    result = run_source(
        'let pack(a, b = 0) = {left: $a, right: $b}\n7 | pack(b = 9)',
        engine=engine,
    )
    assert result.value == {"left": 7, "right": 9}


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_callable_and_arity_are_checked_before_argument_effects(engine: str) -> None:
    effects: list[int] = []
    with pytest.raises(Exception, match="unregistered host function 'unknown'"):
        run_source(
            'unknown(touch())',
            engine=engine,
            functions={"touch": lambda: effects.append(1)},
        )
    assert effects == []


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_named_arguments_must_fill_required_slots_before_effects(engine: str) -> None:
    effects: list[int] = []
    with pytest.raises(Exception, match=r"expects 2..3 argument\(s\)"):
        run_source(
            'let combine(a, b, c = 0) = $a + $b + $c\ncombine(b = touch(), c = touch())',
            engine=engine,
            functions={"touch": lambda: effects.append(1)},
        )
    assert effects == []


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_error_recovery_wraps_the_whole_pipeline(engine: str) -> None:
    result = run_source("1 | unknown on error 99", engine=engine)
    assert result.value == 99


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_newline_before_pipe_continues_without_grouping(engine: str) -> None:
    result = run_source("let inc(x) = x + 1\nlet value = 1\nvalue\n| inc", engine=engine)
    assert result.value == 2


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_uninspectable_host_callables_keep_native_arity_validation(engine: str) -> None:
    result = run_source("maximum(1, 2)", engine=engine, functions={"maximum": max})
    assert result.value == 2


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_explicit_host_functions_override_filter_registry(engine: str) -> None:
    result = run_source("'x' | upper", engine=engine, functions={"upper": lambda value: value + "!"})
    assert result.value == "x!"


@pytest.mark.parametrize("engine", ["tree", "compiled"])
@pytest.mark.parametrize("items", ["[(1,)]", "[(1, 2, 3)]"])
def test_tuple_callback_arity_is_checked_before_callback_effects(engine: str, items: str) -> None:
    effects: list[int] = []
    with pytest.raises(Exception, match="expects 2 argument"):
        run_source(
            f"let combine(a, b) = touch()\n{items} | map(combine)",
            engine=engine,
            functions={"touch": lambda: effects.append(1)},
        )
    assert effects == []


def test_dependency_traversal_skips_overridden_keyword_defaults() -> None:
    from clang_toolkit.cli.runtime.prototype.dependencies import execution_trees
    from clang_toolkit.cli.runtime.prototype.syntax import parse

    source = "let unsafe() = ctk('background functionDecl()')\nlet f(a, b = unsafe()) = a\nf(a = 1, b = 2)"
    assert list(execution_trees(parse(source), {})) == []


def test_dependency_traversal_admits_missing_keyword_defaults() -> None:
    from clang_toolkit.cli.runtime.prototype.dependencies import execution_trees
    from clang_toolkit.cli.runtime.prototype.syntax import parse

    source = "let unsafe() = ctk('background functionDecl()')\nlet f(a, b = unsafe()) = a\nf(a = 1)"
    trees = list(execution_trees(parse(source), {}))
    assert [tree.data for tree in trees] == ["dynamic_command"]


def test_dependency_traversal_counts_pipe_injection_and_keyword_overrides() -> None:
    from clang_toolkit.cli.runtime.prototype.dependencies import execution_trees
    from clang_toolkit.cli.runtime.prototype.syntax import parse

    source = (
        "let unsafe() = ctk('background functionDecl()')\n"
        "let f(input, option = unsafe()) = input\n"
        "1 | f(option = 2)"
    )
    assert list(execution_trees(parse(source), {})) == []


def test_dependency_traversal_visits_bare_pipe_stage_and_callback_defaults() -> None:
    from clang_toolkit.cli.runtime.prototype.dependencies import execution_trees
    from clang_toolkit.cli.runtime.prototype.syntax import parse

    bare_stage = (
        "let f(input) = ctk('background functionDecl()')\n"
        "[1] | f"
    )
    assert [tree.data for tree in execution_trees(parse(bare_stage), {})] == ["dynamic_command"]

    callback_default = (
        "let unsafe() = ctk('background functionDecl()')\n"
        "let f(item, option = unsafe()) = item\n"
        "[(1, 2)] | map(f)"
    )
    assert [tree.data for tree in execution_trees(parse(callback_default), {})] == ["dynamic_command"]


def test_dependency_traversal_follows_callbacks_forwarded_through_pipe_input() -> None:
    from clang_toolkit.cli.runtime.prototype.dependencies import execution_trees
    from clang_toolkit.cli.runtime.prototype.syntax import parse

    forwarded = (
        "let apply(callback, items) = items | map(callback)\n"
        "let cb = (x) = ctk('background functionDecl()')\n"
        "cb | apply([1])"
    )
    assert [tree.data for tree in execution_trees(parse(forwarded), {})] == ["dynamic_command"]

    inline = (
        "let apply(callback, items) = items | map(callback)\n"
        "((x) = ctk('background functionDecl()')) | apply([1])"
    )
    assert [tree.data for tree in execution_trees(parse(inline), {})] == ["dynamic_command"]
