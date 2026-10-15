from __future__ import annotations

import json

import pytest

from clang_toolkit.cli.app import dispatch_result
from clang_toolkit.cli.runtime.prototype.repl import PrototypeRuntime
from clang_toolkit.client import Client


@pytest.fixture(params=["tree", "compiled"])
def runtime(request, tmp_path):
    instance = PrototypeRuntime(Client(), script_engine=request.param,
                                cwd=tmp_path, environment={})
    yield instance
    instance.close()
    instance.client.close()


def submit(runtime, source):
    result = dispatch_result(runtime.client, source, runtime)
    assert result.success, result.output
    return result


PIPELINE = """let names = ['Widget', 'Empty', 'Widget', 'Other']
let counts = [2, 0, 5, 2]
let report = (
    names
    | zip(counts)
    | filter((name, count) = count > 0)
    | sort_by((name, count) = count, reverse=true)
    | unique_by((name, count) = name)
    | map((name, count) = {name: name, count: count})
)
print report | json(indent=2)
"""


@pytest.mark.parametrize("capture", [False, True])
def test_complete_page_pipeline_prints_exact_json_once(runtime, capture):
    runtime.capture_display = capture
    outcome = submit(runtime, PIPELINE)
    assert json.loads(outcome.output) == [
        {"name": "Widget", "count": 5}, {"name": "Other", "count": 2}
    ]
    assert runtime.bindings["report"] == json.loads(outcome.output)


def test_parameterized_filter_and_builtin_alias_persist_across_submissions(runtime):
    submit(runtime, "let my_filter(input, arg) = input + arg; let alias = upper")
    assert submit(runtime, "print 10 | my_filter(1)").output == "11"
    assert submit(runtime, "print ['Widget', 'Empty'] | map(alias) | join(', ')").output == "WIDGET, EMPTY"


def test_builtin_alias_uses_the_current_submissions_item_budget(runtime, monkeypatch):
    from clang_toolkit.cli.runtime.prototype.repl import _ReplContext

    submit(runtime, "let saved_map = map")
    runtime.bindings["source"] = ["one", "two", "three"]
    original_init = _ReplContext.__init__

    def limited_context(context, session):
        original_init(context, session)
        context.max_items = 2

    monkeypatch.setattr(_ReplContext, "__init__", limited_context)
    outcome = dispatch_result(runtime.client, "source | saved_map(upper)", runtime)
    assert not outcome.success
    assert "item budget" in outcome.output


def test_tuple_patterns_foreach_and_named_filter_do_not_leak_locals(runtime):
    outcome = submit(runtime, """let pairs = ['Widget', 'Empty'] | zip([2, 0])
foreach (index, (name, _)) in (pairs | enumerate) do {
    print "{index}: {name}"
}
let make_row((name, count), prefix='') = {name: "{prefix}{name}", count: count}
print ('Widget', 2) | make_row(prefix='demo::') | json
""")
    assert outcome.output.splitlines()[:2] == ["0: Widget", "1: Empty"]
    assert json.loads(outcome.output.splitlines()[2]) == {"name": "demo::Widget", "count": 2}
    assert not ({"index", "name", "count", "_"} & runtime.bindings.keys())


def test_failed_pipeline_preserves_assignment_and_reports_callback_item(runtime):
    submit(runtime, "let report = ['previous']")
    outcome = dispatch_result(runtime.client,
        "let report = [(1, 2), (3,)] | map((a, b) = a + b)", runtime)
    assert not outcome.success
    assert "map" in outcome.output and "1" in outcome.output
    assert runtime.bindings["report"] == ["previous"]
    assert runtime._scopes == []
    assert runtime._matcher_call_depth == 0


def test_json_larger_than_legacy_preview_is_complete(runtime):
    runtime.capture_display = True
    payload = [{"number": index, "text": "x" * 200} for index in range(150)]
    runtime.bindings["payload"] = payload
    outcome = submit(runtime, "print payload | json")
    assert len(outcome.output) > 20_000
    assert json.loads(outcome.output) == payload


def test_filter_import_and_local_builtin_shadowing(runtime, tmp_path):
    library = tmp_path / "filters.ctk"
    library.write_text("let labelled(input, prefix='') = prefix + (input | upper)\n")
    submit(runtime, 'import "filters.ctk"')
    assert submit(runtime, "print 'widget' | labelled(prefix='class ')").output == "class WIDGET"
    submit(runtime, "let original = upper; let upper(input) = input + '!' ")
    assert submit(runtime, "print 'widget' | upper").output == "widget!"
    assert submit(runtime, "print 'widget' | original").output == "WIDGET"


def test_failed_import_restores_mutable_values_nested_in_tuples(runtime, tmp_path):
    nested = [1]
    runtime.bindings["pair"] = (nested, "retained")
    (tmp_path / "bad.ctk").write_text(
        "let mutate() = { pair[0].push(2) }\n"
        "let changed = mutate()\nlet invalid = missing\n"
    )
    outcome = dispatch_result(runtime.client, 'import "bad.ctk"', runtime)
    assert not outcome.success
    assert nested == [1]
    assert runtime.bindings["pair"][0] is nested
