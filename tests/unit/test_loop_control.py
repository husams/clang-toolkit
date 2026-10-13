from __future__ import annotations

import pytest

from clang_toolkit.cli.runtime.prototype.compiler import compile_program
from clang_toolkit.cli.runtime.prototype.repl_language import parse as parse_repl
from clang_toolkit.cli.runtime.prototype.semantics import Context
from clang_toolkit.cli.runtime.prototype.syntax import parse
from clang_toolkit.cli.runtime.prototype.tree import evaluate


@pytest.fixture(params=["tree", "compiled"])
def execute(request):
    def run(source, context=None, parser=parse):
        context = context or Context()
        program = parser(source)
        result = evaluate(program, context) if request.param == "tree" else compile_program(program)(context)
        assert context.scopes == (context.bindings,)
        return result, context
    return run


@pytest.mark.parametrize("source, expected", [
    ('foreach index, item in [] do item', []),
    ('foreach index, item in ["alpha"] do ({index: index, item: item})', [{"index": 0, "item": "alpha"}]),
    ('foreach index, item in [2, 4, 6] do { if index == 1 then continue; [index, item] }', [[0, 2], [2, 6]]),
    ('foreach index, item in [2, 4, 6] do { if index == 1 then break; [index, item] }', [[0, 2]]),
    ('foreach index, item in [2, 4] do { index = 99; index }', [99, 99]),
    ('foreach index, item in {a: 1, b: 2} do [index, item]', [[0, "a"], [1, "b"]]),
    ('foreach i, outer in [1, 2] do foreach j, inner in [3, 4] do [i, j, outer, inner]', [[[0, 0, 1, 3], [0, 1, 1, 4]], [[1, 0, 2, 3], [1, 1, 2, 4]]]),
])
def test_indexed_iteration(execute, source, expected):
    result, _ = execute(source)
    assert result == expected


def test_indexed_source_runs_once_and_keeps_live_iterator(execute):
    values = [1]
    calls = []
    def source():
        calls.append("source")
        return values
    def append():
        if len(values) < 3:
            values.append(len(values) + 1)
    context = Context(functions={"source": source, "grow": append})
    result, _ = execute('foreach index, item in source() do { grow(); [index, item] }', context)
    assert result == [[0, 1], [1, 2], [2, 3]]
    assert calls == ["source"]


def test_indexed_source_rebinding_and_shadowing(execute):
    result, context = execute('let items = [1, 2]; let index = 7; let item = 8; let result = foreach index, item in items do { items = [9]; [index, item] }; [result, index, item]')
    assert result == [[[0, 1], [1, 2]], 7, 8]
    assert context.bindings["items"] == [9]


@pytest.mark.parametrize("parser", [parse, parse_repl])
def test_duplicate_bindings_fail_before_effects(execute, parser):
    context = Context(functions={"side": lambda: pytest.fail("effect ran")})
    with pytest.raises(ValueError, match="duplicate foreach binding.*line 1"):
        execute('side(); foreach item, item in [1] do item', context, parser)


def test_repl_indexed_legacy_iterator_compatibility(execute):
    result, _ = execute('foreach $index, $item in [1, 2] do [index, item]', parser=parse_repl)
    assert result == [[0, 1], [1, 2]]


def test_indexed_engines_share_steps():
    program = parse('foreach index, item in [1, 2] do [index, item]')
    interpreted, compiled = Context(), Context()
    assert evaluate(program, interpreted) == compile_program(program)(compiled)
    assert interpreted.steps == compiled.steps
