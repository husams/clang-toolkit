from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from clang_toolkit._generated.match.v1 import match_result_pb2
from clang_toolkit._row_store import RowStore
from clang_toolkit._value_lifecycle import CursorOwner
from clang_toolkit.cli.runtime import Runtime
from clang_toolkit.cli.runtime.evaluator import EvaluationError
from clang_toolkit.cli.runtime.persistence import load, save
from clang_toolkit.cli.runtime.references import call_method, index_value, inspect_value, property_value
from clang_toolkit.cli.runtime.semantic import view
from clang_toolkit.cli.runtime.values import MatchSet
from clang_toolkit.client import Client
from clang_toolkit.configuration import NetworkConfig
from clang_toolkit.match_values import (
    BindingSelection, MatchValue, NativeBindingCollection, NativeMatchCollection,
)


def _match_value(*, binding_names: tuple[str, ...] = ("f",),
                 source_indices: tuple[int, ...] = (None,),
                 source_file: str | None = None) -> MatchValue:
    rows = RowStore()
    for index, source_index in enumerate(source_indices):
        row = match_result_pb2.MatchResult()
        if source_index is not None:
            row.source_match_index = source_index
        for name in binding_names:
            row.bindings[name].unsupported.detail = f"row-{index}"
        rows.append(row.SerializeToString(), binding_names=binding_names)
    owner_client = Mock()
    owner_client._close_value_cleanup = Mock()
    owner = CursorOwner(owner_client, "test-session", 1, lambda _: None)
    return MatchValue._from_store(rows, owner, source_file=source_file)


def _runtime(tmp_path: Path) -> tuple[Mock, Runtime]:
    client = Mock(spec=Client)
    config = NetworkConfig(
        "unix:///tmp/test.sock", "unix", (), (), None, None, 3, 100, 4,
        1024 * 1024,
    )
    client._configuration.return_value = config
    return client, Runtime(client, cwd=tmp_path, environment={})


def test_file_list_uses_native_matches_with_traversal_and_source_rows(tmp_path):
    client, runtime = _runtime(tmp_path)
    runtime.config_store.effective["traversal"] = "IgnoreUnlessSpelledInSource"
    first = _match_value(binding_names=("f", "source_match_index"), source_indices=(None, 11))
    second = _match_value(source_indices=(None,))
    client.match_in.side_effect = [first, second]

    result = runtime.evaluate('let rows = match functionDecl().bind("f") in ["a.cpp", "b.cpp"]')

    assert isinstance(result, NativeMatchCollection)
    assert len(result) == 3
    assert result[2].source_file == str((tmp_path / "b.cpp").resolve())
    assert result[1].source_match_index == 11
    assert client.match_in.call_args_list[0].kwargs["traversal_mode"] != 0
    assert client.match_in.call_args_list[1].kwargs["traversal_mode"] == client.match_in.call_args_list[0].kwargs["traversal_mode"]
    assert runtime.evaluate("$rows[1].source_match_index") == 11
    assert result[1].binding("source_match_index").name == "source_match_index"
    assert runtime.evaluate('$rows[1].bindings["source_match_index"].name') == "source_match_index"
    continued = _match_value(source_indices=(2,))
    client.match_in.side_effect = None
    client.match_in.return_value = continued
    child = runtime.evaluate('match callExpr() in $rows[2].f')
    assert child is continued
    assert client.match_in.call_args.args[1].source_file == str((tmp_path / "b.cpp").resolve())


def test_file_list_failure_closes_prior_native_results_and_limit_is_enforced(tmp_path):
    client, runtime = _runtime(tmp_path)
    first = _match_value()
    client.match_in.side_effect = [first, RuntimeError("second file failed")]
    with pytest.raises(RuntimeError, match="second file failed"):
        runtime.evaluate('match functionDecl() in ["a.cpp", "b.cpp"]')
    assert first._owner.closed

    runtime.config_store.effective["files"] = ["a.cpp", "b.cpp", "c.cpp", "d.cpp", "e.cpp"]
    client.match_in.reset_mock()
    with pytest.raises(EvaluationError, match="configured limit of 4"):
        runtime.evaluate("match functionDecl()")
    client.match_in.assert_not_called()


def test_native_aggregate_close_attempts_every_member_after_failure():
    first = _match_value()
    second = _match_value()
    first._owner.client._close_value_cleanup.side_effect = RuntimeError("first close failed")
    aggregate = NativeMatchCollection((first, second), ("a.cpp", "b.cpp"))

    with pytest.raises(RuntimeError, match="first close failed"):
        aggregate.close()

    assert first._owner.closed
    assert second._owner.closed
    second._owner.client._close_value_cleanup.assert_called_once_with(second._owner.session_id)


def test_native_binding_collection_count_index_and_iteration_are_typed():
    first = _match_value(source_indices=(2, 3))
    second = _match_value(source_indices=(4,))
    aggregate = NativeMatchCollection((first, second), ("a.cpp", "b.cpp"))
    bindings = aggregate.binding("f")

    assert isinstance(bindings, NativeBindingCollection)
    assert len(bindings) == 3
    assert bindings[1].decl_name is None
    assert [binding.source_file for binding in bindings] == [
        "a.cpp", "a.cpp", "b.cpp"
    ]


def test_binding_aggregate_skips_members_without_the_label_and_inspects(tmp_path):
    first = _match_value(binding_names=("f",))
    second = _match_value(binding_names=("g",))
    collection = NativeMatchCollection((first, second), ("a.cpp", "b.cpp"))
    bindings = collection.binding("f")

    assert len(bindings) == 1
    assert bindings[0].source_file == "a.cpp"
    assert inspect_value(bindings)["type"] == "NativeBindingCollection"
    assert inspect_value(bindings)["length"] == 1
    snapshot_path = tmp_path / "rows.yaml"
    save(collection, snapshot_path)
    detached = load(snapshot_path)
    assert detached.rows[0]["source_file"] == "a.cpp"


def test_collection_sort_orders_numbers_numerically_and_mixed_types_deterministically():
    rows = MatchSet((
        {"value": 10}, {"value": 2}, {"value": "1"}, {"value": None}, {"value": True},
    ))

    sorted_rows = call_method(rows, "sort", ["value"])

    assert [row["value"] for row in sorted_rows] == [None, True, 2, 10, "1"]


def test_grouped_match_expression_supports_property_index_and_foreach(tmp_path):
    client, runtime = _runtime(tmp_path)
    parent = _match_value(source_indices=(0,))
    runtime.bindings["parent"] = parent[0]
    child = _match_value(source_indices=(3, 4))
    client.match_in.return_value = child

    assert runtime.evaluate('let count = (match parmVarDecl().bind("p") in $parent.f).length') == 2
    assert runtime.evaluate('let empty = (match parmVarDecl().bind("p") in $parent.f).isEmpty') is False
    assert runtime.evaluate('let index = (match parmVarDecl().bind("p") in $parent.f)[1].source_match_index') == 4
    assert runtime.evaluate(
        'let indices = foreach $row in (match parmVarDecl().bind("p") in $parent.f) do $row.source_match_index done'
    ) == [3, 4]


def test_dynamic_zero_based_indices_support_parent_join_and_validate_types(tmp_path):
    _, runtime = _runtime(tmp_path)
    parents = _match_value(source_indices=(0, 1, 2), source_file="/src/unit.cc")
    child = _match_value(source_indices=(1,), source_file="/src/unit.cc")
    runtime.bindings["parents"] = NativeMatchCollection((parents,), ("/src/unit.cc",))
    runtime.bindings["child"] = child[0]
    runtime.bindings["flag"] = True

    parent = runtime.evaluate('let parent = $parents[$child.source_match_index]')
    assert parent.source_match_index == 1
    joined = runtime.evaluate(
        'let joined_parent = $parents.filter("source_file", $child.source_file)[$child.source_match_index]'
    )
    assert joined.source_file == "/src/unit.cc"
    assert joined.source_match_index == 1

    for source in (
        "let invalid = $parents[-1]",
        "let invalid = $parents[1.5]",
        "let invalid = $parents[$flag]",
    ):
        with pytest.raises(EvaluationError, match="index must be a nonnegative"):
            runtime.evaluate(source)
    with pytest.raises(EvaluationError, match="valid zero-based integer"):
        runtime.evaluate("let invalid = $parents[8]")


def test_client_match_in_sets_absolute_source_file_for_path_tree_and_binding(tmp_path):
    client = Client()
    responses = iter(
        SimpleNamespace(session_id=f"s{index}", result_revision=1)
        for index in range(3)
    )
    parse_response = SimpleNamespace(session_id="parsed", result_revision=1)

    def cursor_call(method, *_args, **_kwargs):
        if method == "_parse_response":
            return parse_response
        return next(responses), RowStore()

    client._cursor_call = Mock(side_effect=cursor_call)
    working = tmp_path / "src"
    working.mkdir()

    by_path = client.match_in("functionDecl()", "unit.cc", working_directory=working)
    tree = client.parse("unit.cc", working_directory=working)
    assert tree.path == "unit.cc"
    assert tree.source_file == str((working / "unit.cc").resolve())
    by_tree = client.match_in("functionDecl()", tree, working_directory=working)
    selected = BindingSelection("f", tree._owner, source_file="unit.cc")
    by_binding = client.match_in("parmVarDecl()", selected, working_directory=working)

    expected = str((working / "unit.cc").resolve())
    assert by_path.source_file == expected
    assert by_tree.source_file == expected
    assert by_binding.source_file == expected


def test_native_collection_reshape_is_stable_and_uses_selected_fields():
    first = _match_value(source_indices=(4, 1))
    second = _match_value(source_indices=(4, 3))
    collection = NativeMatchCollection((first, second), ("a.cpp", "b.cpp"))

    assert [row.source_match_index for row in call_method(collection, "unique", ["source_match_index"])] == [4, 1, 3]
    assert [row.source_match_index for row in call_method(collection, "sort", ["source_match_index"])] == [1, 3, 4, 4]
    assert [row.source_match_index for row in call_method(collection, "filter", ["source_match_index", 3])] == [3]
    _, runtime = _runtime(Path.cwd())
    runtime.bindings["rows"] = collection
    assert runtime.evaluate('$rows.unique("source_match_index").length') == 3
    assert runtime.evaluate('$rows.filter("source_match_index", 3).length') == 1


def test_detached_match_snapshots_keep_count_index_iteration_and_field_access(tmp_path):
    path = tmp_path / "snapshot.yaml"
    snapshot = MatchSet((
        {"bindings": {"f": {"node": {"declaration": {"name": "first"}}}}},
        {"bindings": {"f": {"node": {"declaration": {"name": "second"}}}}},
    ))
    save(snapshot, path)
    restored = load(path)

    assert property_value(restored, "length") == 2
    row = index_value(restored, 1)
    assert property_value(property_value(property_value(property_value(row, "bindings"), "f"), "node"), "declaration")["name"] == "second"
    assert len(restored.rows) == 2


def test_field_state_distinguishes_unrequested_and_field_or_only_defaults_absence():
    binding = match_result_pb2.MatchBinding(
        availability=[{"field_path": "node", "state": 3}],
    )
    semantic = view(binding)

    assert call_method(semantic, "fieldState", ["node"]) == "UNREQUESTED"
    with pytest.raises(ValueError, match="field was not requested"):
        call_method(semantic, "hasField", ["node"])
    with pytest.raises(ValueError, match="field was not requested"):
        call_method(semantic, "fieldOr", ["node", "fallback"])
    _, runtime = _runtime(Path.cwd())
    runtime.bindings["binding"] = semantic
    assert runtime.evaluate('$binding.fieldState("node")') == "UNREQUESTED"
    with pytest.raises(EvaluationError, match="field was not requested"):
        runtime.evaluate('$binding.fieldOr("node", "fallback")')


def test_binding_declaration_name_and_type_shortcuts_follow_typed_semantics():
    result = match_result_pb2.MatchResult()
    binding = result.bindings["f"]
    declaration = binding.node.function_decl.function.declarator.value
    declaration.named.qualified_name = "demo::run"
    declaration.type.description.spelling = "int (int)"
    store = RowStore()
    store.append(result.SerializeToString(), binding_names=result.bindings)
    match = MatchValue._from_store(store, CursorOwner(object(), "shortcuts", 1, lambda _: None))
    selection = match[0].binding("f")

    assert property_value(selection, "decl_name") == "demo::run"
    assert property_value(selection, "parameter_name") == "demo::run"
    assert property_value(selection, "record_name") == "demo::run"
    assert property_value(selection, "decl_type") == "int (int)"


def test_ast_node_name_qualified_name_and_declared_type_shortcuts():
    binding = match_result_pb2.MatchBinding()
    parameter = binding.node.parm_var_decl.variable.declarator
    parameter.value.named.name.identifier = "value"
    parameter.value.named.qualified_name = "demo::run::value"
    parameter.declared_type.description.spelling = "int"
    node = property_value(view(binding), "node")

    assert property_value(property_value(node, "name"), "identifier") == "value"
    assert property_value(node, "qualified_name") == "demo::run::value"
    assert property_value(
        property_value(property_value(node, "declared_type"), "description"), "spelling"
    ) == "int"

    record_binding = match_result_pb2.MatchBinding()
    record = record_binding.node.cxx_record_decl.record.tag.type_declaration.named
    record.name.identifier = "Widget"
    record.qualified_name = "demo::Widget"
    record_node = property_value(view(record_binding), "node")
    assert property_value(property_value(record_node, "name"), "identifier") == "Widget"
    assert property_value(record_node, "qualified_name") == "demo::Widget"

    parameter.value.named.name.Clear()
    parameter.value.named.name.empty_name.SetInParent()
    optional_name = property_value(property_value(view(binding), "node"), "name")
    assert call_method(optional_name, "fieldOr", ["identifier", "<nonidentifier>"]) == "<nonidentifier>"
    assert call_method(optional_name, "fieldState", ["identifier"]) == "ABSENT"
