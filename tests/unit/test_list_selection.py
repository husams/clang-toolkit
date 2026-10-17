from __future__ import annotations

import pytest

from clang_toolkit.cli.runtime.prototype import run_source
from clang_toolkit.cli.runtime.prototype.semantics import Context, ExecutionLimitError
from clang_toolkit.cli.runtime.prototype.filters import make_filters


@pytest.mark.parametrize("engine", ["tree", "compiled"])
@pytest.mark.parametrize(("expression", "expected"), [
    ("xs[-1]", 50), ("xs[-5]", 10), ("xs[1:4]", [20, 30, 40]),
    ("xs[:3]", [10, 20, 30]), ("xs[3:]", [40, 50]),
    ("xs[-3:]", [30, 40, 50]), ("xs[:-1]", [10, 20, 30, 40]),
    ("xs[::2]", [10, 30, 50]), ("xs[::-1]", [50, 40, 30, 20, 10]),
    ("xs[4:0:-2]", [50, 30]), ("xs[:]", [10, 20, 30, 40, 50]),
    ("xs[1:99]", [20, 30, 40, 50]), ("xs[-99:2]", [10, 20]),
    ("xs[99:]", []), ("xs[3:1]", []), ("xs[2:2]", []),
    ("xs[-4:-1]", [20, 30, 40]), ("xs[1:5:2]", [20, 40]),
    ("xs[3:0:-1]", [40, 30, 20]), ("xs[3::-1]", [40, 30, 20, 10]),
    ("xs[:-1:-1]", []), ("xs[-1:0:-1]", [50, 40, 30, 20]),
    ("xs[1:4:-1]", []), ("xs[99::-1]", [50, 40, 30, 20, 10]),
    ("xs[::-2]", [50, 30, 10]), ("xs[::9223372036854775807]", [10]),
    ("xs[::-9223372036854775808]", [50]),
    ("[][:]", []), ("[][::-1]", []), ("[10][-1]", 10),
    ("[10][::-1]", [10]), ("xs[-3:][::-1]", [50, 40, 30]),
    ("[[1, 2], [3]][::-1][1][-1]", 2), ("[1, 1, 2][::-1]", [2, 1, 1]),
    ("xs | first", 10), ("xs | last", 50), ("xs | first()", 10),
    ("xs | last()", 50), ("xs | first(2)", [10, 20]),
    ("xs | last(2)", [40, 50]), ("xs | first(1)", [10]),
    ("xs | last(1)", [50]), ("xs | first(0)", []), ("xs | last(0)", []),
    ("xs | first(99)", [10, 20, 30, 40, 50]),
    ("xs | last(99)", [10, 20, 30, 40, 50]),
    ("[] | first", None), ("[] | last", None), ("[] | first(2)", []),
    ("[] | last(2)", []), ("[null] | first(1)", [None]),
    ("xs | reverse | first(2)", [50, 40]),
    ("(1, 2, 3)[::-1]", [3, 2, 1]),
    ("xs[\n1:\n4:\n2\n]", [20, 40]),
])
def test_selection_contract(engine, expression, expected):
    assert run_source(f"let xs = [10, 20, 30, 40, 50]\n{expression}",
                      engine=engine).value == expected


@pytest.mark.parametrize("engine", ["tree", "compiled"])
@pytest.mark.parametrize(("expression", "message"), [
    ("xs[5]", "index 5.*length 5"), ("xs[-6]", "index -6.*length 5"),
    ("[][-1]", "length 0"), ("xs[::0]", "step.*zero"),
    ("[][::0]", "step.*zero"), ("xs[1.0]", "integer"),
    ("xs[true]", "boolean"), ('xs["1"]', "integer"),
    ("xs[null:3]", "start.*integer"), ("xs[:null]", "stop.*integer"),
    ("xs[::null]", "step.*integer"), ("xs[::false]", "step.*integer"),
    ("xs | first(-1)", "nonnegative"), ("xs | last(1.5)", "integer"),
    ("xs | first(null)", "integer"), ("xs | last(true)", "integer"),
    ("1 | first", "finite"), ("null | last", "finite"),
    ("1 | reverse", "finite"), ("xs[1:3] = [1]", "assignment"),
])
def test_selection_errors(engine, expression, message):
    with pytest.raises(Exception, match=message):
        run_source(f"let xs = [10, 20, 30, 40, 50]\n{expression}", engine=engine)


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_bound_effects_run_once_in_order_and_selection_is_shallow(engine):
    effects = []
    row = {"name": "original"}
    source = "source()[bound(0):bound(2):bound(1)]"
    result = run_source(source, engine=engine, functions={
        "source": lambda: effects.append("source") or [row, row],
        "bound": lambda n: effects.append(n) or n,
    })
    assert effects == ["source", 0, 2, 1]
    assert result.value[0] is row and result.value[1] is row


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_no_mutation_and_syntax_errors(engine):
    result = run_source("let xs = [1, 2, 3]\nlet ys = xs[::-1]\nys[0] = 9\nxs", engine=engine)
    assert result.value == [1, 2, 3]
    with pytest.raises(Exception):
        run_source("[1][1:2:3:4]", engine=engine)
    with pytest.raises(Exception, match="argument"):
        run_source("[1] | first(1, 2)", engine=engine)


def test_selection_never_consumes_a_generator_and_obeys_output_limit():
    def stream():
        pytest.fail("stream was consumed")
        yield 1
    filters = make_filters(Context(max_items=2))
    for name in ("first", "last", "reverse"):
        with pytest.raises(TypeError, match="finite"):
            filters[name](stream())
    with pytest.raises(ExecutionLimitError, match="item limit"):
        filters["reverse"]([1, 2, 3])


@pytest.mark.parametrize("engine", ["tree", "compiled"])
def test_retained_collections_preserve_owner_provenance_and_incomplete_binding(engine):
    from clang_toolkit._generated.match.v1 import match_service_pb2
    from clang_toolkit._value_lifecycle import CursorOwner
    from clang_toolkit.match_values import MatchValue, NativeMatchCollection, NativeBindingCollection

    response = match_service_pb2.MatchResponse()
    for _ in range(3):
        binding = response.results.add().bindings["f"]
        binding.node.translation_unit_decl.SetInParent()
        binding.is_complete = False
    owner = CursorOwner(object(), "selection", 1, lambda _: None)
    matches = MatchValue._from_response(response, owner, source_file="fixture.cc")
    multi = NativeMatchCollection((matches,), ("fixture.cc",))
    bindings = NativeBindingCollection((matches.binding("f"),), ("fixture.cc",), (matches,))
    for collection in (matches, multi, bindings):
        for expression in ("items[-1]", "items[::-1][0]", "items | last"):
            selected = run_source(expression, engine=engine, bindings={"items": collection}).value
            assert selected._owner is owner
            assert selected._index == 2
            assert selected.source_file == "fixture.cc"
            binding = selected if collection is bindings else selected.binding("f")
            assert not binding.value.is_complete
        assert len(collection) == 3
