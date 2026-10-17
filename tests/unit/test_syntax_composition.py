from __future__ import annotations

import json

import pytest

from clang_toolkit.cli.app import dispatch_result
from clang_toolkit.cli.runtime.prototype.compiler import compile_program
from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
from clang_toolkit.cli.runtime.prototype.repl_language import parse as parse_repl
from clang_toolkit.cli.runtime.prototype.semantics import Context, EvaluationError
from clang_toolkit.cli.runtime.prototype.syntax import parse
from clang_toolkit.cli.runtime.prototype.tree import evaluate
from clang_toolkit.client import Client


@pytest.fixture(
    params=[
        (parse, "tree"),
        (parse, "compiled"),
        (parse_repl, "tree"),
        (parse_repl, "compiled"),
    ]
)
def execute(request):
    parser, engine = request.param

    def run(source, context=None):
        context = context or Context()
        context.source = source
        program = parser(source)
        return (
            evaluate(program, context)
            if engine == "tree"
            else compile_program(program)(context)
        )

    return run


@pytest.mark.parametrize(
    "source, expected",
    [
        ("[(1, 2), (3, 4)] | map((x, y) x + y)", [3, 7]),
        ("[1, 2] | map((x) { let y = x + 1; y * 2 })", [4, 6]),
        ("let f = (x, y = 2) x + y; f(40)", 42),
        ("let f = () 42; f()", 42),
        ("let apply(f, x) = f(x); apply((x) if x > 0 then x else 0, 42)", 42),
        ("let x = 3; (x) + 1", 4),
        ("let x = 3; (x) - 1", 2),
        ("let f(x) = x + 1; (f)(41)", 42),
        ("let make(x) = (y) x + y; make(19)(23)", 42),
        ("let fs = [(x) x + 1]; fs[0](41)", 42),
        ("let fs = {next: (x) x + 1}; fs.next(41)", 42),
        ("let make(x) = (y = 23) x + y; make(19)(y=23)", 42),
        ("[[1, 2], [3]] | map((xs) xs | length)", [2, 1]),
        ("let x = 2; ((x) x + 1)(41)", 42),
        ("let f = (x) { x + 1 } on error 0; f(41)", 42),
        ("let f = (x) = { x + 1 } on error 0; f(41)", 42),
        ("let apply(f, xs) = xs | map(f); (x) { x + 1 } | apply([1, 2])", [2, 3]),
        (
            "let xs = [1, 2, 3]\nlet ys = xs\n | map((x) x * 2)\n | reverse\nys",
            [6, 4, 2],
        ),
        ("let xs = [1, 2]\n// comment\n | map((x) x + 1)\nxs", [2, 3]),
    ],
)
def test_composable_expressions(execute, source, expected):
    assert execute(source) == expected


@pytest.mark.parametrize("name", ["parse", "read", "load", "pop", "delete", "flatten"])
def test_command_names_remain_callable_when_bound(execute, name):
    assert execute(f"let {name}(x) = x + 1; {name}(41)") == 42


def test_indexed_callee_runs_once_and_preflights_before_argument_effects(execute):
    effects = []
    context = Context(functions={"touch": lambda: effects.append("argument")})
    with pytest.raises(EvaluationError, match="not callable"):
        execute("let fs = [7]; fs[0](touch())", context)
    assert effects == []


def test_callee_and_arguments_evaluate_once_in_order(execute):
    effects = []
    context = Context(
        functions={
            "factory": lambda: effects.append("callee") or (lambda x: x),
            "touch": lambda: effects.append("argument") or 42,
        }
    )
    assert execute("factory()(touch())", context) == 42
    assert effects == ["callee", "argument"]


@pytest.mark.parametrize(
    "source",
    [
        "let fs = [() 1]; fs[0](touch())",
        "let make() = () 1; make()(touch())",
    ],
)
def test_expression_callee_arity_is_checked_before_arguments(execute, source):
    effects = []
    with pytest.raises(EvaluationError, match="expects 0 argument"):
        execute(source, Context(functions={"touch": lambda: effects.append(1)}))
    assert effects == []


@pytest.mark.parametrize(
    "source",
    [
        "let fs = [() ctk('server status')]; fs[0]()",
        "let make() = () ctk('server status'); make()()",
        "let make() = { let f = () ctk('server status'); f }; make()()",
        "let fs = {run: () ctk('server status')}; fs.run()",
        "let make(flag) = if flag then () ctk('server status') else () 1; make(true)()",
        "let make(flag) = if flag then () ctk('server status') else () 1; make(unknown)()",
        "let make(flag) = if flag then [() ctk('server status')] else [() 1]; make(1 == 1)[0]()",
        "let make(flag) = if flag then {run: () ctk('server status')} else {run: () 1}; make(1 == 1).run()",
        "let fs = [() ctk('server status')]; fs[unknown]()",
    ],
)
def test_admission_inspects_reachable_expression_callees(source):
    from clang_toolkit.cli.runtime.prototype.dependencies import execution_trees

    assert "dynamic_command" in [
        tree.data for tree in execution_trees(parse(source), {})
    ]


@pytest.mark.parametrize(
    "source, kind",
    [
        ('parse (if true then "x.cc" else "y.cc")', "parse_expression"),
        ('read ("x" + ".json")', "read_expression"),
        ('load ("x" + ".json")', "load_command"),
        ("pop (if true then xs else ys)", "pop_expression"),
        ("delete (xs | reverse)", "delete_command"),
        ("flatten ([1, [2]])", "flatten_expression"),
        ("inspect (xs | reverse)", "inspect"),
    ],
)
def test_parenthesized_operands_keep_host_command_meaning(source, kind):
    command = parse_repl(source).children[0]
    assert command.kind == "host"
    assert command.value[0].data == kind


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_command_expression_operands(engine, tmp_path):
    client = Client()
    runtime = PrototypeRuntime(
        client, script_engine=engine, cwd=tmp_path, environment={}
    )
    try:
        source = """let xs = [1, 2, 3]
let path = "report.json"
save xs | map((x) x * 2) to (if true then path else "unused.json") as json
let result = read (if true then path else "missing.json") as json
print result | json
"""
        outcome = dispatch_result(client, source, runtime)
        assert outcome.success, outcome.output
        assert json.loads((tmp_path / "report.json").read_text()) == [2, 4, 6]
        assert json.loads(outcome.output.splitlines()[-1]) == [2, 4, 6]
        outcome = dispatch_result(
            client,
            """let pieces = split ("alpha" + ",beta") by ("," | trim)
let joined = join (pieces | reverse) with ("-" | upper)
let items = [1]
push items, 1 + 1
items.push(1 + 2)
let named = functionDecl(hasName("demo::" + "run"))
print {joined: joined, items: items, matcher: named}
""",
            runtime,
        )
        assert outcome.success, outcome.output
        assert runtime.bindings["joined"] == "beta-alpha"
        assert runtime.bindings["items"] == [1, 2, 3]
        assert runtime.bindings["named"].arguments[0].arguments == ("demo::run",)
        outcome = dispatch_result(
            client,
            "let taken = pop (items); let flat = flatten ([items, [4]]); "
            'let loaded = read (path + "")',
            runtime,
        )
        assert outcome.success, outcome.output
        assert runtime.bindings["taken"] == 3
        assert runtime.bindings["flat"] == [1, 2, 4]
        outcome = dispatch_result(client, "delete (items)[0 + 1]", runtime)
        assert outcome.success, outcome.output
        assert runtime.bindings["items"] == [1]
        outcome = dispatch_result(client, "delete (items | reverse)", runtime)
        assert not outcome.success
        assert "requires a final" in outcome.output
        outcome = dispatch_result(
            client,
            "let calls = [0]; let choose() = { calls[0] += 1; items }; "
            "push (choose()), 9; delete (choose())[0]",
            runtime,
        )
        assert outcome.success, outcome.output
        assert runtime.bindings["calls"] == [2]
        assert runtime.bindings["items"] == [9]
    finally:
        runtime.close()
        client.close()


@pytest.mark.parametrize(
    "source, message",
    [
        ('save (if true then quit) to "unused.json"', "quit is only valid"),
        ('save (1 + 9223372036854775808) to "unused.json"', "signed 64-bit range"),
    ],
)
def test_embedded_command_operands_are_validated_before_execution(source, message):
    with pytest.raises(ValueError, match=message):
        parse_repl(source)


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_existing_approved_methods_keep_their_dispatch(engine, tmp_path):
    from tests.unit.test_call_graph_values import graph

    client = Client()
    runtime = PrototypeRuntime(
        client, script_engine=engine, cwd=tmp_path, environment={}
    )
    runtime.bindings["graph"] = graph()
    try:
        outcome = dispatch_result(
            client,
            """let target = graph.function("pkg::A")
let incoming = graph.callers(target, depth=1)
let grouped = graph.grouped_calls()
let values = [42]
let single = values.one()
let record = {a: 7}
let field = record.get("a")
let text = " value "
let trimmed = text.strip()
""",
            runtime,
        )
        assert outcome.success, outcome.output
        assert runtime.bindings["incoming"].nodes
        assert runtime.bindings["grouped"]
        assert runtime.bindings["single"] == 42
        assert runtime.bindings["field"] == 7
        assert runtime.bindings["trimmed"] == "value"
    finally:
        runtime.close()
        client.close()
