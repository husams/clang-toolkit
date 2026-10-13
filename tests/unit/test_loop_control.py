from __future__ import annotations

import pytest
from lark import UnexpectedInput

from clang_toolkit.cli.runtime.prototype.compiler import compile_program
from clang_toolkit.cli.runtime.prototype.repl_language import parse as parse_repl
from clang_toolkit.cli.runtime.prototype.semantics import (
    CancelledError, Context, EvaluationError, ExecutionLimitError,
)
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
    ('foreach item in [] do item', []),
    ('foreach item in ["alpha"] do ({index: item.index, item: item})', [{"index": 0, "item": "alpha"}]),
    ('foreach item in [2, 4, 6] do { if item.index == 1 then continue; [item.index, item] }', [[0, 2], [2, 6]]),
    ('foreach item in [2, 4, 6] do { if item.index == 1 then break; [item.index, item] }', [[0, 2]]),
    ('foreach item in [2, 4] do { item = 99; [item.index, item] }', [[0, 99], [1, 99]]),
    ('foreach item in {a: 1, b: 2} do [item.index, item]', [[0, "a"], [1, "b"]]),
    ('foreach outer in [1, 2] do foreach inner in [3, 4] do [outer.index, inner.index, outer, inner]', [[[0, 0, 1, 3], [0, 1, 1, 4]], [[1, 0, 2, 3], [1, 1, 2, 4]]]),
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
    result, _ = execute('foreach item in source() do { grow(); [item.index, item] }', context)
    assert result == [[0, 1], [1, 2], [2, 3]]
    assert calls == ["source"]


def test_indexed_source_rebinding_and_shadowing(execute):
    result, context = execute('let items = [1, 2]; let index = 7; let item = 8; let result = foreach item in items do { items = [9]; [item.index, item] }; [result, index, item]')
    assert result == [[[0, 1], [1, 2]], 7, 8]
    assert context.bindings["items"] == [9]


@pytest.mark.parametrize("parser", [parse, parse_repl])
def test_comma_bindings_are_rejected_before_effects(execute, parser):
    context = Context(functions={"side": lambda: pytest.fail("effect ran")})
    with pytest.raises(UnexpectedInput):
        execute('side(); foreach index, item in [1] do item', context, parser)


def test_repl_indexed_legacy_iterator_compatibility(execute):
    result, _ = execute('foreach $item in [1, 2] do [item.index, item]', parser=parse_repl)
    assert result == [[0, 1], [1, 2]]


def test_indexed_engines_share_steps():
    program = parse('foreach item in [1, 2] do [item.index, item]')
    interpreted, compiled = Context(), Context()
    assert evaluate(program, interpreted) == compile_program(program)(compiled)
    assert interpreted.steps == compiled.steps


@pytest.mark.parametrize("source, expected", [
    ('let result = while false do 9; result', []),
    ('let result = repeat {} until true; result', [None]),
    ('let x = 0; let result = while x < 3 do x += 1; result', [1, 2, 3]),
    ('let x = 0; let result = while (x < 3) { x += 1; x }; result', [1, 2, 3]),
    ('let x = 0; let result = repeat x += 1 until x >= 3; result', [1, 2, 3]),
    ('let x = 0; let result = repeat { x += 1; x }\nuntil x >= 3; result', [1, 2, 3]),
    ('let x = 0; let result = repeat { x += 1; if x < 3 then continue; x } until x >= 3; result', [3]),
    ('let x = 0; let result = repeat { x += 1; continue } until x >= 3; result', []),
    ('let x = 0; let result = while x < 3 do { x += 1; continue }; result', []),
    ('let result = repeat break until missing; result', []),
    ('let result = while true do break; result', []),
    ('let x = 0; let result = repeat repeat x += 1 until x >= 2 until true; result', [[1, 2]]),
    ('let x = 0; let result = while x < 2 do if true then x += 1 else 9; result', [1, 2]),
    ('if true then while false do if false then 1 else 2 else 3', []),
    ('let repeat_count = 3; let record = {while: 1, repeat: 2, until: 3}; [repeat_count, record.while, record.repeat, record.until]', [3, 1, 2, 3]),
])
@pytest.mark.parametrize("parser", [parse, parse_repl])
def test_condition_loop_forms(execute, source, expected, parser):
    result, _ = execute(source, parser=parser)
    assert result == expected


@pytest.mark.parametrize("kind", ["while", "repeat"])
def test_condition_timing_and_break(execute, kind):
    checks = []
    context = Context(functions={"check": lambda value: checks.append(value) or value >= 3})
    source = 'let x = 0; let result = ' + (
        'while not check(x) do { x += 1; x }' if kind == 'while'
        else 'repeat { x += 1; x } until check(x)') + '; result'
    result, _ = execute(source, context)
    assert result == [1, 2, 3]
    assert checks == ([0, 1, 2, 3] if kind == 'while' else [1, 2, 3])
    checks.clear()
    source = 'let x = 0; let result = ' + (
        'while not check(x) do break' if kind == 'while' else 'repeat break until check(x)') + '; result'
    result, _ = execute(source, context)
    assert result == []
    assert checks == ([0] if kind == 'while' else [])


@pytest.mark.parametrize("loop", [
    'while x < 3 do { on exit clean(x); x += 1; if x < 3 then continue; x }',
    'repeat { on exit clean(x); x += 1; if x < 3 then continue; x } until x >= 3',
])
def test_loop_cleanup_scope_and_continued_values(execute, loop):
    cleaned = []
    context = Context(functions={"clean": lambda value: cleaned.append(value)})
    result, _ = execute('let x = 0; let result = '+loop+'; result', context)
    assert result == [3]
    assert cleaned == [1, 2, 3]
    assert context.call_depth == context.cleanup_depth == 0


def test_nested_control_exits_only_nearest_loop(execute):
    result, _ = execute('foreach i in [1, 2] do { let x = 0; let inner = repeat { x += 1; while true do break; if x == 2 then break; x } until false; inner }')
    assert result == [[1], [1]]


@pytest.mark.parametrize("source", [
    'while false do break; continue',
    'if false then break',
    'while true do { let f() = { break }; break }',
    'repeat { let f() = { continue }; break } until true',
    'while if true then break else false do 1',
])
def test_control_validation_precedes_effects(execute, source):
    context = Context(functions={"side": lambda: pytest.fail("effect ran")})
    with pytest.raises(ValueError, match="requires an enclosing foreach, while or repeat loop"):
        execute('side(); '+source, context)


@pytest.mark.parametrize("source", ['while 1 do {}', 'repeat {} until 1'])
def test_strict_boolean_condition(execute, source):
    with pytest.raises(EvaluationError, match="requires bool.*line 1"):
        execute(source)


def test_repeat_condition_cannot_read_body_local(execute):
    with pytest.raises(EvaluationError, match="undefined binding 'finished'"):
        execute('repeat { let finished = true } until finished')


@pytest.mark.parametrize("loop", ['while x < 5 do x += 1', 'repeat x += 1 until x >= 5'])
def test_standalone_loops_do_not_collect_unused_results(execute, loop):
    result, context = execute('let x = 0; '+loop, Context(max_items=0))
    assert result is None
    assert context.bindings['x'] == 5


@pytest.mark.parametrize("loop", ['while true do { x += 1; x }', 'repeat { x += 1; x } until false'])
def test_collection_limit_preserves_assignment_target(execute, loop):
    context = Context(max_items=2, bindings={"saved": 99, "x": 0})
    with pytest.raises(ExecutionLimitError, match="result exceeds item limit"):
        execute('saved = '+loop, context)
    assert context.bindings == {"saved": 99, "x": 3}
    assert context.scopes == (context.bindings,)


@pytest.mark.parametrize("loop", ['while true do continue', 'repeat continue until false', 'while true do {}', 'repeat {} until false'])
def test_empty_and_continued_loops_exhaust_step_budget(execute, loop):
    context = Context(max_steps=25)
    with pytest.raises(ExecutionLimitError, match="step limit.*line 1"):
        execute(loop, context)
    assert context.steps == 26
    assert context.scopes == (context.bindings,)


@pytest.mark.parametrize("loop", ['while true do { on exit clean(); stop() }', 'repeat { on exit clean(); stop() } until false'])
def test_cancellation_runs_cleanup_and_preserves_target(execute, loop):
    stopped = False
    cleaned = []
    def stop():
        nonlocal stopped
        stopped = True
    context = Context(bindings={"saved": 99}, cancel_hook=lambda: stopped,
                      functions={"stop": stop, "clean": lambda: cleaned.append("exit")})
    with pytest.raises(CancelledError, match="cancelled"):
        execute('saved = '+loop, context)
    assert context.bindings == {"saved": 99}
    assert context.scopes == (context.bindings,)
    assert cleaned == ["exit"]
    assert context.cleanup_depth == 0


@pytest.mark.parametrize("source", [
    'let x = 0; let result = while x < 3 do { x += 1; if x == 2 then continue; x }; result',
    'let x = 0; let result = repeat { x += 1; if x == 2 then continue; x } until x >= 3; result',
])
def test_condition_loop_engines_share_steps(source):
    program = parse(source)
    interpreted, compiled = Context(), Context()
    assert evaluate(program, interpreted) == compile_program(program)(compiled) == [1, 3]
    assert interpreted.steps == compiled.steps


def test_compiled_condition_loops_do_not_dispatch_tree(monkeypatch):
    program = compile_program(parse('let x = 0; let result = repeat { x += 1; while false do {}; x } until x >= 3; result'))
    monkeypatch.setattr('clang_toolkit.cli.runtime.prototype.semantics.eval_expr', lambda *_: pytest.fail('tree dispatch'))
    monkeypatch.setattr('clang_toolkit.cli.runtime.prototype.semantics.eval_statement', lambda *_: pytest.fail('tree dispatch'))
    assert program(Context()) == [1, 2, 3]


@pytest.mark.parametrize("source, expected", [
    ('let result = foreach item in [1, 2] do { let x = 0; while x < item do x += 1 }; result', [[1], [1, 2]]),
    ('let x = 0; let result = repeat { let y = 0; x += 1; repeat y += 1 until y >= x } until x >= 2; result', [[1], [1, 2]]),
    ('let f() = { let x = 0; while x < 2 do x += 1 }; f()', [1, 2]),
])
def test_nested_loop_values_are_consumed_by_final_body_statement(execute, source, expected):
    value, _ = execute(source)
    assert value == expected


@pytest.mark.parametrize("parser", [parse, parse_repl])
@pytest.mark.parametrize("source, expected", [
    ('foreach item in [{index: 42, value: 7}] do [item.index, item.value.index, item.value.value, item]',
     [[0, 42, 7, {"index": 42, "value": 7}]]),
    ('foreach item in [{index: 42}] do { let alias = item; [item.index, alias.index] }', [[0, 42]]),
    ('let identity(value) = value; foreach item in [{index: 42}] do identity(item).index', [42]),
    ('foreach outer in [4, 5] do foreach inner in [6, 7] do [outer.index, inner.index]',
     [[[0, 0], [0, 1]], [[1, 0], [1, 1]]]),
    ('foreach item in [4, 5] do { let nested = foreach item in [6, 7] do item.index; [item.index, nested] }',
     [[0, [0, 1]], [1, [0, 1]]]),
    ('foreach item in [{index: 42}] do { if true then { let item = {index: 9}; print item.index }; item.index }', [0]),
    ('foreach item in [{index: 42}] do { item.value.index += 1; [item.index, item.value.index] }', [[0, 43]]),
    ('foreach item in [4, 5] do { item = {index: 9}; [item.index, item.value.index] }', [[0, 9], [1, 9]]),
    ('foreach item in [{index: 42}] do { let item = {index: 9}; item.index }', [9]),
    ('let items = foreach item in [4, 5] do item; items', [4, 5]),
])
def test_loop_metadata_is_lexical_and_values_stay_plain(execute, parser, source, expected):
    result, context = execute(source, parser=parser)
    assert result == expected
    assert context._loop_indices == {}


@pytest.mark.parametrize("source", [
    'foreach item in [4] do { let alias = item; alias.index }',
    'foreach item in [4] do item; item.index',
    'let identity(value) = value; foreach item in [4] do identity(item).index',
])
def test_loop_metadata_does_not_escape_its_binding(execute, source):
    context = Context()
    with pytest.raises(EvaluationError):
        execute(source, context)
    assert context._loop_indices == {}
    assert context.scopes == (context.bindings,)


@pytest.mark.parametrize("property_name", ["index", "value"])
@pytest.mark.parametrize("operator", ["=", "+="])
def test_loop_metadata_is_read_only_before_rhs_effects(execute, property_name, operator):
    record = {"index": 42, "value": 7}
    context = Context(bindings={"items": [record]}, functions={"side": lambda: pytest.fail("rhs ran")})
    with pytest.raises(EvaluationError, match="loop metadata .* is read-only.*line 1"):
        execute(f'foreach item in items do item.{property_name} {operator} side()', context)
    assert record == {"index": 42, "value": 7}
    assert context._loop_indices == {}
    assert context.scopes == (context.bindings,)


def test_loop_metadata_is_available_to_exit_handler(execute):
    cleaned = []
    context = Context(functions={"clean": lambda ordinal, value: cleaned.append((ordinal, value))})
    result, _ = execute('foreach item in [4, 5] do { on exit clean(item.index, item); continue }', context)
    assert result == []
    assert cleaned == [(0, 4), (1, 5)]
    assert context._loop_indices == {}


def test_loop_metadata_cancellation_unwinds_and_preserves_target(execute):
    context = Context(bindings={"saved": 99}, max_steps=40)
    context.cancel_hook = lambda: context.steps >= 30
    with pytest.raises(CancelledError):
        execute('saved = foreach item in [1, 2, 3] do repeat continue until false', context)
    assert context.bindings["saved"] == 99
    assert context._loop_indices == {}
    assert context.scopes == (context.bindings,)
