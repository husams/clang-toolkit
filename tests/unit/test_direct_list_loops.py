from __future__ import annotations

import ast
from pathlib import Path

import pytest

from clang_toolkit.cli.runtime.prototype.compiler import compile_program
from clang_toolkit.cli.runtime.prototype.repl_language import parse as parse_repl
from clang_toolkit.cli.runtime.prototype.semantics import Context
from clang_toolkit.cli.runtime.prototype.syntax import parse
from clang_toolkit.cli.runtime.prototype.tree import evaluate

DEFINITIONS = (
    (Path(__file__).resolve().parents[2] / "examples/recursive_lists.ctk")
    .read_text()
    .split("let xs =")[0]
)


@pytest.fixture(params=[(parse, "tree"), (parse, "compiled")])
def execute(request):
    parser, engine = request.param

    def run(source, context):
        context.source = source
        program = parser(source)
        return (
            evaluate(program, context)
            if engine == "tree"
            else compile_program(program)(context)
        )

    return run


@pytest.mark.parametrize(
    "target, expression, expected",
    [
        ("map_into", "map_list(range(1000), (x) x * 2)", list(range(0, 2000, 2))),
        (
            "filter_into",
            "filter_list(range(1000), (x) x % 2 == 0)",
            list(range(0, 1000, 2)),
        ),
        ("reverse_list", "reverse_list(range(1000))", list(range(999, -1, -1))),
    ],
)
def test_recognized_functions_run_without_continuation_objects(
    execute, monkeypatch, target, expression, expected
):
    from clang_toolkit.cli.runtime.prototype import list_recursion

    context = Context()
    execute(DEFINITIONS, context)
    function = context.lookup(target)
    direct = getattr(function, "direct_loop", None)
    assert direct is not None, (
        "recognized recursive list functions need direct Python loops"
    )
    source = direct.__ctk_source__
    assert any(
        isinstance(node, (ast.For, ast.While)) for node in ast.walk(ast.parse(source))
    )
    assert not any(
        isinstance(node, (ast.Yield, ast.YieldFrom))
        for node in ast.walk(ast.parse(source))
    )
    assert "_Request" not in source and "_Frame" not in source and "_leaf" not in source

    def forbidden(*args, **kwargs):
        pytest.fail("recognized function allocated a continuation")

    monkeypatch.setattr(list_recursion, "_Request", forbidden)
    monkeypatch.setattr(list_recursion, "_Frame", forbidden)
    assert execute(expression, context) == expected


@pytest.mark.parametrize("parser", [parse, parse_repl])
def test_map_recognition_uses_structure_and_accepts_renamed_parameters(parser):
    from clang_toolkit.cli.runtime.prototype.list_loops import recognize_loop

    source = (
        DEFINITIONS.replace("map_into", "collect")
        .replace("out", "buffer")
        .replace("h : t", "first : rest")
        .replace("f(h)", "f(first)")
        .replace("(t, f,", "(rest, f,")
    )
    program = parser(source)
    clause = program.children[0].children[0]
    if clause.kind == "consume":
        clause = clause.children[0]
    shape = recognize_loop(clause)
    assert shape is not None and shape.kind == "map"
    assert (shape.head, shape.tail, shape.output) == ("first", "rest", "buffer")
