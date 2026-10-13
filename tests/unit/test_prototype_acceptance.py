from __future__ import annotations

import pytest

from clang_toolkit.cli.runtime.prototype import Context, compile_program, evaluate, parse, run_source
from clang_toolkit.cli.runtime.prototype.semantics import EvaluationError, ExecutionLimitError


PROGRAMS = [
    ("let count=7; let weighted=$count*2+1; [$weighted, $weighted/2, $weighted%4]", [15, 7.5, 3]),
    ("let total=0; $total=$total+1; $total+=1; $total", 2),
    ("let counts={functions:1}; $counts.functions+=2; $counts.functions", 3),
    ("let counts={}; $counts.functions=3; $counts[\"functions\"]", 3),
    ("let value=12; let x=if $value>10 do 10 else 20; let y=$value==30 ? 10 : 20; [$x,$y]", [10, 20]),
    ("let x = 2; let y = if $x > 0 then $x * 10 else 1; $y", 20),
    ("let x = 0; let y = if $x > 0 then $x * 10 else 1; $y", 1),
    ("let x = 2; if $x > 0 then $x * 10 else if $x < 0 then 9 else 1", 20),
    ("if true then { let hidden = 4; $hidden + 1 } else missing()", 5),
    ("if false then missing() else 8", 8),
    ("if false then if true do 1 else 2", None),
    ("if false then if true then 1 else 2", None),
    ("if false then if true then 1 else {} else 2", 2),
    ("if false then (if true then 1) else 2", 2),
    ("if true then if false then 1 else 2", 2),
    ("if false do if true then 1 else 2", None),
    ("if true then if false do 1 else 2", 2),
    ("if true do if false then 1 else 2", 2),
    ("unless true then if false do 1 else 2", None),
    ("unless false then if false do 1 else 2", 2),
    ("if false then { if true do 1 } else 2", 2),
    ("unless false then { let hidden = 3; $hidden + 2 } else missing()", 5),
    ("let found=false; let details=unless ($found) { let text=\"No matches\"; {message:$text,retry:true} }; $details", {"message": "No matches", "retry": True}),
    ("let x=unless true do 10; let y=unless true do 10 else 20; [$x,$y]", [None, 20]),
    ("let rows=foreach item in range(3) do ({index:$item, scaled:$item*3}); $rows[2].scaled", 6),
    ("let rows=foreach item in [1,2] do foreach other in [3,4] do $item*$other; $rows", [[3, 4], [6, 8]]),
    ("[false and missing(), true or missing(), true ? 7 : missing()]", [False, True, 7]),
    ("[false ? 1 : true ? 2 : 3, true ? false ? 4 : 5 : 6]", [2, 5]),
    ("[-7%3, 7%-3, -7%-3, -9223372036854775808]", [-1, 1, -1, -(1 << 63)]),
    ("let x=1\n-2\nprint $x", 1),
    ("let x=(1+\n2)\n$x", 3),
]


@pytest.mark.parametrize("source,expected", PROGRAMS)
def test_user_programs_have_identical_values_bindings_output_and_steps(source, expected):
    tree = run_source(source, engine="tree")
    compiled = run_source(source, engine="compiled")
    assert tree == compiled
    assert tree.value == expected
    assert "item" not in tree.bindings and "other" not in tree.bindings and "text" not in tree.bindings


@pytest.mark.parametrize("source", ["true + 1", "if 1 do 2", "9007199254740993 + 0.0", "9223372036854775807 + 1", "1/0"])
@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_invalid_primitive_operations_have_source_errors(source, engine):
    with pytest.raises(EvaluationError, match="line 1"):
        run_source(source, engine=engine)


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_excess_collection_items_fail_before_host_effects(engine):
    calls = []
    with pytest.raises(ExecutionLimitError):
        run_source("[touch(),touch(),touch()]", engine=engine, functions={"touch": lambda: calls.append(True)}, max_items=2)
    assert calls == []


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_failed_rhs_preserves_existing_target_and_scopes(engine):
    program = parse("let value=5; $value+=1/0")
    context = Context()
    with pytest.raises(EvaluationError):
        evaluate(program, context) if engine == "tree" else compile_program(program)(context)
    assert context.bindings == {"value": 5}
    assert len(context.scopes) == 1
