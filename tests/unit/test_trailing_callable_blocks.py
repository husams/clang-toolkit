"""Trailing callable blocks share ordinary call binding and evaluation."""

from __future__ import annotations

import pytest

from clang_toolkit.cli.app import dispatch_result
from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
from clang_toolkit.cli.runtime.prototype.dependencies import execution_trees
from clang_toolkit.cli.runtime.prototype.repl_language import parse
from clang_toolkit.cli.runtime.prototype.syntax import parse as parse_standalone
from clang_toolkit.client import Client


@pytest.fixture(params=["tree", "compiled"])
def runtime(request, tmp_path):
    instance = PrototypeRuntime(Client(), script_engine=request.param, cwd=tmp_path, environment={})
    yield instance
    instance.close()
    instance.client.close()


def submit(runtime, source):
    outcome = dispatch_result(runtime.client, source, runtime)
    assert outcome.success, outcome.output
    return outcome


@pytest.mark.parametrize("parser", [parse, parse_standalone])
def test_trailing_blocks_lower_to_ordinary_calls(parser):
    calls = parser(
        "map(items) { (item) item * 2 }; "
        "items | filter { (item) item > 2 } | map { (item) item * 10 }"
    ).children
    call = calls[0]
    assert (call.kind, call.value) == ("call", "map")
    assert [child.kind for child in call.children] == ["ref", "clause_runnable"]
    assert calls[1].kind == "pipe"
    for stage in calls[1].children[1:]:
        assert stage.kind == "call"
        assert stage.children[0].kind == "clause_runnable"


def test_collections_pipelines_and_normal_calls_agree(runtime):
    submit(runtime, """let items = [1, 2, 3, 4]
let mapped = map(items) { (item) item * 2 }
let normal = map(items, { (item) item * 2 })
let result = items
    | filter { (item) item > 2 }
    | map { (item) item * 10 }
let equivalent = map(filter(items, { (item) item > 2 }), { (item) item * 10 })
let old_pipe = items | map({ (item) item * 2 })
""")
    assert runtime.bindings["mapped"] == runtime.bindings["normal"] == runtime.bindings["old_pipe"] == [2, 4, 6, 8]
    assert runtime.bindings["result"] == runtime.bindings["equivalent"] == [30, 40]


def test_tuple_callbacks_statement_bodies_and_lexical_captures(runtime):
    submit(runtime, """let factor = 10
let pairs = [("Ada", 3), ("Lin", 5)]
let result = pairs | map {
    (name, count) {
        let scaled = count * factor
        "{name}: {scaled}"
    }
}
""")
    assert runtime.bindings["result"] == ["Ada: 30", "Lin: 50"]
    assert "scaled" not in runtime.bindings


def test_labels_keyword_options_and_shorthand_compose(runtime):
    submit(runtime, """let transform(value, using: operation) = operation(value)
let adjust(value, using: operation, by: = 2) = operation(value) * by
let a = transform(5) { (item) item + 1 }
let b = 5 | transform { (item) item + 1 }
let c = adjust(5, by = 3) { (item) item + 1 }
let d = 5 | adjust by 3 { (item) item + 1 }
let e = transform 5 using { (item) item + 1 }
let sorted = [1, 3, 2] | sort_by(reverse = true) { (item) item }
""")
    assert [runtime.bindings[name] for name in "abcde"] == [6, 6, 18, 18, 6]
    assert runtime.bindings["sorted"] == [3, 2, 1]


def test_callable_aliases_indexed_and_returned_values(runtime):
    submit(runtime, """let transform(value, operation) = operation(value)
let alias = transform
let functions = [transform]
let get_transform() = transform
let a = alias(3) { (item) item + 1 }
let b = functions[0](3) { (item) item + 1 }
let c = get_transform()(3) { (item) item + 1 }
""")
    assert [runtime.bindings[name] for name in "abc"] == [4, 4, 4]


def test_preflight_rejects_invalid_trailing_call_before_argument_effects(runtime):
    submit(runtime, "let count = 0; let side() = { count += 1; count }; let one(value) = value")
    outcome = dispatch_result(runtime.client, "one(side()) { (item) item }", runtime)
    assert not outcome.success
    assert "expects 1 argument(s), got 2" in outcome.output
    assert runtime.bindings["count"] == 0


def test_control_bodies_dictionaries_and_newline_boundaries_keep_their_meaning(runtime):
    submit(runtime, """let count = 0
let yes() = true
if yes() { count += 1 }
while count < 2 { count += 1 }
foreach item in [1, 2] { count += item }
let value = {number: count}
let saved = upper
let callback = { (item) item + 1 }
let answer = callback(2)
""")
    assert runtime.bindings["count"] == 5
    assert runtime.bindings["value"] == {"number": 5}
    assert runtime.bindings["answer"] == 3


@pytest.mark.parametrize("parser", [parse, parse_standalone])
def test_newline_ends_a_call_before_a_separate_callable_value(parser):
    program = parser("let result = f(1)\n{ (item) item + 1 }")
    assert len(program.children) == 2
    assert len(program.children[0].children[0].children) == 1
    assert program.children[1].kind == "clause_runnable"
    pipeline, callback = parser("[1, 2] | map\n{ (item) item + 1 }").children
    assert pipeline.kind == "pipe"
    assert pipeline.children[-1].kind == "ref"
    assert callback.kind == "clause_runnable"


@pytest.mark.parametrize("source", [
    "[1] | map { (item) ctk('server status') }",
    "let transform(value, using: operation) = operation(value); "
    "transform(1) { (item) ctk('server status') }",
    "let transform(value, operation) = operation(value); let fs = [transform]; "
    "fs[0](1) { (item) ctk('server status') }",
])
def test_admission_inspects_reachable_trailing_callbacks(source):
    assert "dynamic_command" in [tree.data for tree in execution_trees(parse(source), {})]


def test_uninvoked_trailing_callback_stays_dormant(runtime):
    submit(runtime, "let ignore(operation) = 42; let answer = ignore { () unknown() }")
    assert runtime.bindings["answer"] == 42


def test_grouped_pattern_clauses_work_as_trailing_callback(runtime):
    submit(runtime, """let result = [[], [1, 2], [3]] | map {
    ([]) 0
    ((head: tail)) head
}
""")
    assert runtime.bindings["result"] == [0, 1, 3]
