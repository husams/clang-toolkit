from __future__ import annotations

import pytest

from clang_toolkit.cli.runtime.prototype import run_source


@pytest.mark.parametrize("engine", ["tree", "compiled"])
@pytest.mark.parametrize(("source", "expected"), [
    ("()", ()),
    ("(3,)", (3,)),
    ("(3, 4)", (3, 4)),
])
def test_tuple_literals(engine: str, source: str, expected: tuple[object, ...]) -> None:
    assert run_source(source, engine=engine).value == expected


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_tuple_indexing_is_checked(engine: str) -> None:
    assert run_source("(3, 4)[1]", engine=engine).value == 4
    with pytest.raises(Exception, match="tuple index"):
        run_source("(3,)[1]", engine=engine)


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_nested_tuple_patterns_and_discards_in_foreach(engine: str) -> None:
    result = run_source(
        'let values = [(1, 2), (3, 4)]\n'
        'foreach ((_, a), (_, b)) in [((10, 20), (30, 40))] do $a + $b',
        engine=engine,
    )
    assert result.value == [60]


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_foreach_patterns_reject_duplicate_names(engine: str) -> None:
    with pytest.raises(ValueError, match="duplicate names"):
        run_source("foreach (value, (value, _)) in [(1, (2, 3))] do value", engine=engine)


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_tuple_parameters_and_named_record_expression_body(engine: str) -> None:
    result = run_source(
        'let convert((a, b), scale = 1) = {first: $a * $scale, second: $b}\n'
        'let row = (3, 4)\nlet converted = $row | convert(scale = 2)\n$converted',
        engine=engine,
    )
    assert result.value == {"first": 6, "second": 4}
