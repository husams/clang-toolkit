"""One-level flattening composes local collections without native queries."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from lark.exceptions import UnexpectedInput

from clang_toolkit._generated.match.v1 import match_result_pb2, match_service_pb2
from clang_toolkit._value_lifecycle import CursorOwner
from clang_toolkit.cli.runtime import EvaluationError, Runtime
from clang_toolkit.cli.runtime.semantic import view
from clang_toolkit.cli.runtime.values import MatchSet
from clang_toolkit.client import Client
from clang_toolkit.match_values import MatchValue


@pytest.fixture
def flatten_runtime(tmp_path):
    client = Mock(spec=Client)
    client.compilation_database = None
    config = SimpleNamespace(effective={
        "compile_commands": None, "vars": {}, "output": "stdout", "extra_args": [],
    })
    runtime = Runtime(client, cwd=tmp_path, environment={}, config_store=config)
    yield runtime, client
    runtime.close()


def _row(name):
    row = match_result_pb2.MatchResult()
    row.bindings["f"].node.function_decl.function.declarator.value.named.qualified_name = name
    return row


def test_flatten_preserves_order_identity_and_nested_values_without_mutation(flatten_runtime):
    runtime, client = flatten_runtime
    nested = ["nested"]
    record = {"name": "record"}
    groups = [[], [1, nested, record], (), (2, 3), []]
    runtime.bindings["groups"] = groups
    result = runtime.evaluate("flatten($groups)")
    assert type(result) is list
    assert result == [1, nested, record, 2, 3]
    assert result[1] is nested and result[2] is record
    assert groups == [[], [1, nested, record], (), (2, 3), []]
    assert runtime.evaluate("flatten([])") == []
    assert runtime.evaluate("flatten([[], []])") == []
    assert runtime.evaluate("flatten([[1, [2]], [3]])") == [1, [2], 3]
    assert client.mock_calls == []


def test_flatten_detached_matchsets_preserves_row_type_identity_and_names(flatten_runtime):
    runtime, client = flatten_runtime
    first, second = view(_row("first")), view(_row("second"))
    groups = [MatchSet((first,)), MatchSet(()), [second]]
    runtime.bindings["run"] = {"results": groups}
    assert runtime.execute("let all_matches = flatten($run.results)") == ""
    assert runtime.bindings["all_matches"] == [first, second]
    assert runtime.bindings["all_matches"][0] is first
    assert runtime.bindings["all_matches"][1] is second
    assert runtime.evaluate('$all_matches[0].bindings["f"].node.qualified_name') == "first"
    assert runtime.evaluate('$all_matches[1].bindings["f"].node.qualified_name') == "second"
    assert runtime.bindings["run"]["results"] is groups
    assert client.mock_calls == []


def test_flatten_live_query_collection_reads_rows_without_requery_or_closing_owner(flatten_runtime):
    runtime, client = flatten_runtime
    response = match_service_pb2.MatchResponse()
    response.results.add().CopyFrom(_row("live"))
    owner = CursorOwner(client, "flatten-cursor", 1, lambda _session: None)
    matches = MatchValue._from_response(response, owner)
    runtime.bindings["groups"] = [matches]
    try:
        rows = runtime.evaluate("flatten($groups)")
        assert len(rows) == 1
        assert rows[0]._owner is owner
        assert not owner.closed
        assert len(matches) == 1
        assert client.mock_calls == []
    finally:
        owner.close()


def test_flatten_evaluates_operand_once_and_keeps_string_join_distinct(flatten_runtime):
    runtime, _ = flatten_runtime
    runtime.bindings["queued"] = [[1, 2], [3]]
    assert runtime.evaluate("flatten([pop $queued])") == [3]
    assert runtime.bindings["queued"] == [[1, 2]]
    runtime.bindings["words"] = ["a", "b"]
    assert runtime.evaluate('join $words with ","') == "a,b"


@pytest.mark.parametrize("invalid", ["abc", {"record": 1}, 42, True, None])
def test_flatten_rejects_scalar_or_record_outer_values(flatten_runtime, invalid):
    runtime, _ = flatten_runtime
    runtime.bindings["invalid"] = invalid
    with pytest.raises(EvaluationError, match="flatten requires"):
        runtime.evaluate("flatten($invalid)")


@pytest.mark.parametrize("invalid", ["abc", {"record": 1}, 42, True, None])
def test_flatten_reports_the_invalid_child_index_without_replacing_prior_assignment(flatten_runtime, invalid):
    runtime, _ = flatten_runtime
    runtime.bindings["groups"] = [[1], invalid]
    runtime.bindings["flattened"] = "prior"
    with pytest.raises(EvaluationError, match="index 1"):
        runtime.execute("let flattened = flatten($groups)")
    assert runtime.bindings["flattened"] == "prior"
    assert runtime.bindings["groups"] == [[1], invalid]


def test_flatten_accepts_ten_thousand_items_and_rejects_overflow(flatten_runtime):
    runtime, _ = flatten_runtime
    values = list(range(10_000))
    runtime.bindings["groups"] = [[], values, []]
    assert runtime.evaluate("flatten($groups)") == values
    runtime.bindings["groups"] = [values, [10_000]]
    with pytest.raises(EvaluationError, match="10000 items"):
        runtime.evaluate("flatten($groups)")
    assert len(values) == 10_000
    assert runtime.bindings["groups"][1] == [10_000]


@pytest.mark.parametrize("source", ["flatten()", "flatten([], [])"])
def test_flatten_rejects_invalid_arity(flatten_runtime, source):
    runtime, _ = flatten_runtime
    with pytest.raises((EvaluationError, UnexpectedInput)):
        runtime.evaluate(source)
