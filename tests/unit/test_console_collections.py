"""User-authored list and dictionary behavior in the console runtime."""

from __future__ import annotations

from types import MappingProxyType
from unittest.mock import Mock

import pytest

from clang_toolkit._generated.match.v1 import match_result_pb2
from clang_toolkit.client import Client
from clang_toolkit.cli.app import dispatch
from clang_toolkit.cli.runtime import EvaluationError, Runtime
from clang_toolkit.cli.runtime.references import property_value
from clang_toolkit.cli.runtime.semantic import view
from clang_toolkit.cli.runtime.values import render


def make_runtime(tmp_path):
    client = Mock(spec=Client)
    return client, Runtime(client, cwd=tmp_path, environment={})


def test_list_dictionary_literals_access_and_collection_commands(tmp_path):
    client, runtime = make_runtime(tmp_path)

    runtime.evaluate("let options = {}")
    runtime.evaluate("let values = [1, 2, 3]")
    runtime.evaluate('let options = {a: 1, b: 2, clear: 3}')
    runtime.evaluate('let literal_key = "resolved"')
    runtime.evaluate('let literal_map = {literal_key: 9}')
    runtime.evaluate("let nested = {outer: {answer: 42}}")
    runtime.evaluate("let alias = values")
    assert dispatch(client, "$options['a']", runtime) == "1"
    assert dispatch(client, "options['clear']", runtime) == "3"
    assert dispatch(client, "$nested['outer']['answer']", runtime) == "42"
    assert dispatch(client, "$options.keys", runtime) == "a\nb\nclear"
    assert runtime.bindings["literal_map"] == {"literal_key": 9}

    dispatch(client, "set options['three'] = 3", runtime)
    dispatch(client, "push values, 4", runtime)
    runtime.evaluate("let last = pop values")
    dispatch(client, "$alias.push(5)", runtime)
    dispatch(client, "delete values[0]", runtime)

    assert runtime.bindings["options"] == {"a": 1, "b": 2, "clear": 3, "three": 3}
    assert runtime.bindings["values"] == [2, 3, 5]
    assert runtime.bindings["last"] == 4
    client.assert_not_called()


def test_split_join_and_list_dictionary_methods(tmp_path):
    client, runtime = make_runtime(tmp_path)

    assert dispatch(client, 'split "a/b" by "/"', runtime) == "a\nb"
    runtime.evaluate('let parts = split "a/b" by "/"')
    assert dispatch(client, 'join parts with ","', runtime) == "a,b"
    assert dispatch(client, "$parts.push(\"c\")", runtime) == "a\nb\nc"
    assert dispatch(client, "$parts.pop()", runtime) == "c"

    dispatch(client, "$parts.insert(1, \"inserted\")", runtime)
    dispatch(client, "$parts.remove(\"inserted\")", runtime)
    assert runtime.bindings["parts"] == ["a", "b"]

    runtime.evaluate('let options = {"active": true}')
    assert dispatch(client, '$options.hasKey("active")', runtime) == "true"
    assert dispatch(client, '$options.get("missing", 7)', runtime) == "7"
    assert dispatch(client, '$options.set("count", 2)', runtime) == "2"
    assert dispatch(client, "$options.values", runtime) == "true\n2"
    assert dispatch(client, '$options.delete("active")', runtime) == "true"
    dispatch(client, "$options.clear()", runtime)
    assert runtime.bindings["options"] == {}
    client.assert_not_called()


def test_collection_commands_accept_dollar_references_and_nested_targets(tmp_path):
    client, runtime = make_runtime(tmp_path)
    runtime.evaluate('let a2 = {items: ["a"]}')

    dispatch(client, 'push $a2["items"], "b"', runtime)
    assert dispatch(client, 'join $a2["items"] with ","', runtime) == "a,b"
    runtime.evaluate('let removed = pop $a2["items"]')
    runtime.execute('set $a2["items"][0] = "updated"')
    runtime.execute('delete $a2["items"][0]')

    assert runtime.bindings["removed"] == "b"
    assert runtime.bindings["a2"] == {"items": []}
    client.assert_not_called()


@pytest.mark.parametrize(
    "name",
    ["output", "user", "files", "traversal", "extra_args", "compile_commands", "cache_dir"],
)
def test_mutable_variable_names_do_not_conflict_with_settings(tmp_path, name):
    _, runtime = make_runtime(tmp_path)
    runtime.execute(f"let {name} = {{}}")

    runtime.execute(f"set {name}['x'] = 1")

    assert runtime.bindings[name] == {"x": 1}


def test_dictionary_keyword_keys_are_properties_and_methods_remain_callable(tmp_path):
    _, runtime = make_runtime(tmp_path)
    runtime.execute('let d = {push: "property", delete: 3, import: 4}')

    assert runtime.execute("$d.push") == 'property'
    assert runtime.execute("$d.import") == "4"
    suggestions = runtime.completion_suggestions("$d")
    delete_suggestions = [item for item in suggestions if item.name == "delete"]
    assert [(item.kind, item.display_meta) for item in delete_suggestions] == [
        ("property", "dictionary key"),
        ("method", "method · delete dictionary entries"),
    ]
    assert runtime.execute('$d.delete("delete")') == "3"


def test_collection_errors_are_clear_and_mutations_reject_cycles(tmp_path):
    client, runtime = make_runtime(tmp_path)
    runtime.evaluate("let values = []")
    runtime.evaluate("let options = {}")

    with pytest.raises(EvaluationError, match="empty list"):
        runtime.evaluate("let removed = pop values")
    with pytest.raises(EvaluationError, match="cannot create a cyclic collection"):
        runtime.execute("set options['self'] = options")
    runtime.evaluate("let outer = []")
    runtime.evaluate("let child = {items: outer}")
    with pytest.raises(EvaluationError, match="cannot create a cyclic collection"):
        runtime.execute("push outer, child")
    runtime.evaluate("let target = {}")
    runtime.evaluate("let nested = [target]")
    with pytest.raises(EvaluationError, match="cannot create a cyclic collection"):
        runtime.execute("set target['nested'] = nested")
    with pytest.raises(EvaluationError, match="keys must be strings"):
        runtime.execute("set options[0] = 1")
    with pytest.raises(EvaluationError, match="separator cannot be empty"):
        runtime.execute('split "abc" by ""')
    with pytest.raises(EvaluationError, match="dictionary key not found"):
        runtime.execute("delete options['missing']")
    with pytest.raises(EvaluationError, match="list index is out of range"):
        runtime.execute("delete values[0]")
    with pytest.raises(EvaluationError, match="duplicate dictionary key"):
        runtime.evaluate('let duplicate = {a: 1, "a": 2}')

    assert runtime.bindings["options"] == {}
    client.assert_not_called()


def test_mutation_does_not_write_through_read_only_mappings_or_semantic_views(tmp_path):
    client, runtime = make_runtime(tmp_path)
    runtime.bindings["readonly"] = MappingProxyType({"key": 1})
    runtime.bindings["semantic"] = view(match_result_pb2.MatchBinding(is_complete=True))

    with pytest.raises(EvaluationError, match="mutable list or dictionary"):
        runtime.execute("set readonly['key'] = 2")
    with pytest.raises(EvaluationError, match="mutable list or dictionary"):
        runtime.execute("set semantic['is_complete'] = false")

    assert runtime.bindings["readonly"]["key"] == 1
    assert property_value(runtime.bindings["semantic"], "is_complete") is True
    client.assert_not_called()


def test_render_decodes_utf8_bytes_and_falls_back_for_invalid_bytes():
    assert render(b"hello \xe2\x9c\x93") == "hello ✓"
    assert render(b"\xff") == "b'\\xff'"
    assert render({"nested": [b"text"]}) == '{"nested": ["text"]}'


def test_render_bounds_deep_dictionary_before_recursing():
    nested = "leaf"
    for _ in range(500):
        nested = {"next": nested}
    rendered = render(nested)
    assert len(rendered) < 20_000
    assert "maximum depth reached" in rendered
