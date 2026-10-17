from __future__ import annotations

import pytest

from clang_toolkit.cli.runtime.prototype.compiler import compile_program
from clang_toolkit.cli.runtime.prototype.semantics import Context, PrototypeError
from clang_toolkit.cli.runtime.prototype.syntax import parse
from clang_toolkit.cli.runtime.prototype.repl_language import parse as parse_repl
from clang_toolkit.cli.runtime.prototype.tree import evaluate


@pytest.fixture(params=[(parse, "tree"), (parse, "compiled"), (parse_repl, "tree"), (parse_repl, "compiled")])
def execute(request):
    parser, engine = request.param

    def run(source, context=None):
        context = context or Context()
        context.source = source
        program = parser(source)
        return evaluate(program, context) if engine == "tree" else compile_program(program)(context)

    return run


@pytest.mark.parametrize("source, expected", [
    ("let [a, b] = [10, 20]; a + b", 30),
    ("let (name, count) = (42, 3); count", 3),
    ("let head : tail = [10, 20, 30]; (head, tail)", (10, [20, 30])),
    ("let a : b : rest = [10, 20, 30]; (a, b, rest)", (10, 20, [30])),
    ("let [a, (b, c)] = [10, (20, 30)]; a + b + c", 60),
    ("let first(head : _) = head; first([10, 20])", 10),
    ("let two(a : b : _) = a + b; two([10, 20, 30])", 30),
    ("[[10, 20], [30, 40]] | map((head : _) head)", [10, 30]),
    ("let total = { ([]) 0; (head : tail) head + total(tail) }; total([10, 20, 30])", 60),
    ("let total = { ([]) 0; (head : tail) head + total(tail) }; total([])", 0),
    ("let describe = { ([]) 0; ([x]) x; (head : tail) 99 }; [describe([]), describe([7]), describe([1, 2])]", [0, 7, 99]),
    ("let f = { ([x], y) x + y; (head : tail, _) head }; f([10], 20)", 30),
    ("let xs = [1, 2]; let h : tail = xs; tail[0] = 9; xs", [1, 2]),
    ("let f = { ([]) 1; (_) 2 }; let old = f; let f = { (_) 3 }; [old([]), f([])]", [1, 3]),
    ("let only(head : []) = head; only([7])", 7),
    ("let f = { (_) 1; ([]) 2 }; f([])", 1),
    ("let make = { ([x]) (n) n + x; ([]) (n) n }; make([7])(3)", 10),
    ("let funcs = [{ ([x]) x; ([]) 0 }]; funcs[0]([7])", 7),
    ("foreach h : _ in [[1, 2], [3, 4]] do h", [1, 3]),
])
def test_list_patterns_and_clauses(execute, source, expected):
    assert execute(source) == expected


def test_destructuring_failure_is_atomic_and_rhs_runs_once(execute):
    effects = []
    context = Context(functions={"items": lambda: effects.append(1) or [10]})
    context.define("a", 7)
    with pytest.raises(PrototypeError, match="pattern"):
        execute("let [a, b] = items()", context)
    assert context.lookup("a") == 7
    assert effects == [1]


def test_no_matching_clause_and_single_clause_mismatch(execute):
    with pytest.raises(PrototypeError, match="matching clause"):
        execute("let f = { ([x]) x }; f([])")
    with pytest.raises(PrototypeError, match="pattern"):
        execute("let first(head : _) = head; first([])")


def test_matching_body_failure_does_not_fall_through(execute):
    with pytest.raises(PrototypeError, match="zero"):
        execute("let f = { ([x]) 1 / 0; (_) 42 }; f([1])")


def test_recognized_numeric_right_fold_handles_large_lists_without_recursion(execute):
    assert execute("let total = { ([]) 0; (head : tail) head + total(tail) }; total(range(5000))") == 12497500


def test_right_fold_preserves_arithmetic_order_and_does_not_slice(execute):
    class NoSlice(list):
        def __getitem__(self, index):
            assert not isinstance(index, slice), "optimized folds must not copy tails"
            return super().__getitem__(index)

    context = Context(functions={"items": lambda: NoSlice([1e16, -1e16, 1.0])})
    assert execute("let total = { ([]) 0; (head : tail) head + total(tail) }; total(items())", context) == 0.0
    assert "for index in range" in context.lookup("total").optimized.__ctk_source__


def test_fold_preserves_checked_overflow_and_execution_budget(execute):
    with pytest.raises(PrototypeError, match="overflow"):
        execute("let total = { ([]) 0; (head : tail) head + total(tail) }; total([9223372036854775807, 1])")
    with pytest.raises(PrototypeError, match="step limit"):
        execute("let total = { ([]) 0; (head : tail) head + total(tail) }; total(range(100))", Context(max_steps=100))


def test_fold_checks_cancellation_while_combining_results(execute):
    reached_base = False

    def cancelled():
        nonlocal reached_base
        if context.current_location[0] == 2:
            reached_base = True
        return reached_base and context.current_location[0] == 3

    context = Context(cancel_hook=cancelled)
    with pytest.raises(PrototypeError, match="cancelled"):
        execute("let total = {\n([]) 0\n(head : tail) head + total(tail)\n}; total([1, 2, 3])", context)


def test_fold_and_recursive_execution_charge_equal_steps(execute):
    contexts = []
    for optimized in (True, False):
        context = Context()
        execute("let total = { ([]) 0; (head : tail) head + total(tail) }", context)
        if not optimized:
            object.__setattr__(context.lookup("total"), "optimized", None)
        assert execute("total([1, 2, 3])", context) == 6
        contexts.append(context)
    assert contexts[0].steps == contexts[1].steps


def test_fold_does_not_optimize_a_shadowed_self_binding(execute):
    with pytest.raises(PrototypeError, match="not callable"):
        execute("let total = { ([]) 0; (total : tail) total + total(tail) }; total([1])")
    with pytest.raises(PrototypeError, match="not callable"):
        execute("let total = { ([]) 0; (head : total) head + total(total) }; total([1])")


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_console_wrappers_preserve_numeric_fold_compilation(tmp_path, engine):
    from clang_toolkit.cli.app import dispatch_result
    from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
    from clang_toolkit.client import Client

    client = Client()
    runtime = PrototypeRuntime(client, script_engine=engine, cwd=tmp_path, environment={})
    try:
        result = dispatch_result(client, "let total = { ([]) 0; (head : tail) head + total(tail) }; print total(range(5000))", runtime)
        assert result.success, result.output
        assert result.output == "12497500"
        assert runtime.bindings["total"].optimized is not None
    finally:
        runtime.close()
        client.close()


def test_clause_preflight_and_argument_evaluation(execute):
    effects = []
    context = Context(functions={"items": lambda: effects.append(1) or [10]})
    with pytest.raises(PrototypeError, match="expects"):
        execute("let f = { ([]) 0; ([x]) x }; f(items(), items())", context)
    assert effects == []
    assert execute("let f = { ([]) 0; ([x]) x }; f(items())", context) == 10
    assert effects == [1]


def test_clauses_remain_dormant(execute):
    effects = []
    execute("let f = { ([]) touch(); (head : tail) touch() }; 42", Context(functions={"touch": lambda: effects.append(1)}))
    assert effects == []


def test_discarded_tails_do_not_slice(execute):
    class NoSlice(list):
        def __getitem__(self, index):
            assert not isinstance(index, slice), "discarded tails must not be copied"
            return super().__getitem__(index)

    assert execute("let first(h : _) = h; first(items())", Context(functions={"items": lambda: NoSlice([7, 8])})) == 7


@pytest.mark.parametrize("source", [
    "let [x, x] = [1, 2]",
    "let f(x : x) = x",
    "let f = { ([]) 0; (x, y) 1 }",
    "let f = { (x = 1) x; (_) 0 }",
])
def test_invalid_pattern_declarations_are_rejected(source):
    with pytest.raises(ValueError):
        parse(source)


@pytest.mark.parametrize("source", [
    "let run = { ([]) 0; (h : t) ctk('server status') }; run([1])",
    "let run = { ([]) 0; (h : t) ctk('server status') }; [[1]] | map(run)",
    "let run = { (head : _) head() }; run([() ctk('server status')])",
    "let [run] = [() ctk('server status')]; run()",
    "let head : tail = if unknown then [() ctk('server status')] else [() 0]; head()",
    "let run = { (head : _) head() }; run(if unknown then [() ctk('server status')] else [() 0])",
])
def test_admission_inspects_reachable_clause_and_destructured_callbacks(source):
    from clang_toolkit.cli.runtime.prototype.dependencies import execution_trees

    assert "dynamic_command" in [tree.data for tree in execution_trees(parse(source), {})]


def test_admission_bounds_previously_defined_recursive_group_aliases(execute):
    from clang_toolkit.cli.runtime.prototype.dependencies import execution_trees

    context = Context()
    execute("let funcs = [{ ([]) 0; (h : t) f(t) }]; let f = funcs[0]", context)
    assert list(execution_trees(parse("f([1])"), context.bindings)) == []
    assert list(execution_trees(parse("f([1])()"), context.bindings)) == []


def test_clause_groups_preserve_captures_when_scopes_are_snapshotted(execute):
    from clang_toolkit.cli.runtime.prototype.runnables import snapshot_scopes

    context = Context()
    execute("let factor = 2; let total = { ([]) 0; (h : t) h * factor + total(t) }; let alias = total", context)
    captured = snapshot_scopes([context.bindings])[0]
    context.assign_binding("factor", 9)
    assert captured["total"] is captured["alias"]
    assert execute("alias([1, 2, 3])", Context(bindings=captured)) == 12
