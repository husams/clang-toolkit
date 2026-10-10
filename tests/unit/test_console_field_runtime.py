"""Runtime integration for schema references and inspect syntax."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from clang_toolkit.cli.app import dispatch
from clang_toolkit.cli.runtime import EvaluationError, Runtime
from clang_toolkit.cli.runtime.references import property_value
from clang_toolkit.client import Client
from clang_toolkit._generated.match.v1 import match_result_pb2
from clang_toolkit._generated.match.v1 import match_service_pb2
from clang_toolkit.cli.runtime.semantic import view
from clang_toolkit.cli.runtime.values import render
from clang_toolkit.match_values import MatchRow
from clang_toolkit.match_values import MatchValue
from clang_toolkit._row_store import RowStore
from clang_toolkit._value_lifecycle import CursorOwner


def make_runtime(tmp_path):
    client = Mock(spec=Client)
    return client, Runtime(client, cwd=tmp_path, environment={})


def test_reference_supports_numeric_and_string_indices(tmp_path):
    client, runtime = make_runtime(tmp_path)
    runtime.bindings["items"] = ["zero", "one"]
    runtime.bindings["mapping"] = {"field": "value"}

    assert dispatch(client, "$items[1]", runtime) == "one"
    assert dispatch(client, '$mapping["field"]', runtime) == "value"
    client.assert_not_called()


def test_reference_errors_identify_the_failed_segment_and_position(tmp_path):
    client, runtime = make_runtime(tmp_path)
    runtime.bindings["mapping"] = {"present": 1}

    with pytest.raises(EvaluationError, match=r'\["missing"\].*line 1, column'):
        runtime.evaluate('$mapping["missing"]')


def test_inspect_accepts_a_reference_and_displays_scalar(tmp_path):
    client, runtime = make_runtime(tmp_path)
    runtime.bindings["answer"] = 42

    assert dispatch(client, "inspect $answer", runtime) == "42"
    client.assert_not_called()


def test_completion_fields_fails_safely_for_invalid_or_scalar_reference(tmp_path):
    _, runtime = make_runtime(tmp_path)
    runtime.bindings["answer"] = 42

    assert runtime.completion_fields("$answer") == ()
    assert runtime.completion_fields("$missing.field") == ()
    assert runtime.completion_fields("not a reference") == ()


def test_semantic_reference_inspection_and_presence_are_local(tmp_path):
    client, runtime = make_runtime(tmp_path)
    runtime.bindings["binding"] = view(match_result_pb2.MatchBinding(is_complete=False))

    assert dispatch(client, '$binding.hasField("is_complete")', runtime) == "true"
    assert dispatch(client, "$binding.is_complete", runtime) == "false"
    assert "ctk.match.v1.MatchBinding" in dispatch(client, "inspect $binding", runtime)
    assert "is_complete" in runtime.completion_fields("$binding")
    client.assert_not_called()


def test_keys_property_works_through_match_rows_and_nested_semantic_values(tmp_path):
    client, runtime = make_runtime(tmp_path)
    response = match_service_pb2.MatchResponse()
    for is_complete in (False, True):
        binding = match_result_pb2.MatchBinding(is_complete=is_complete)
        binding.node.translation_unit_decl.SetInParent()
        response.results.add().bindings["root"].CopyFrom(binding)
    owner = CursorOwner(object(), "session", 1, lambda _session: None)
    runtime.bindings["lst"] = MatchValue._from_response(response, owner)

    aggregate_display = dispatch(client, "$lst.root", runtime)
    assert aggregate_display == "binding root"
    aggregate_field = dispatch(client, "$lst.root.is_complete", runtime)
    assert aggregate_field.startswith("error:")
    assert "binding value requires an explicit row index" in aggregate_field
    keys = dispatch(client, "$lst[1].root.value.keys", runtime)
    assert {"node", "is_complete", "supported_scopes", "availability"} <= set(keys.splitlines())
    assert {"symbol_identity", "documentation"} <= set(keys.splitlines())
    assert dispatch(client, "$lst[1].root.value.keys[0]", runtime) == "node"
    node_keys = dispatch(client, "$lst[1].root.value.node.keys", runtime).splitlines()
    assert "translation_unit_decl" in node_keys
    assert "declarations" in node_keys
    assert "keys" in runtime.completion_fields("$lst[1].root.value")
    assert "keys" in runtime.completion_fields("$lst[1].root.value.node")
    assert dispatch(client, "$lst[1].root.name", runtime) == "root"
    assert dispatch(client, "$lst[1].root.is_complete", runtime) == "true"
    direct_display = dispatch(client, "$lst[1].root", runtime)
    assert direct_display == dispatch(client, "$lst[1].root.value", runtime)
    assert '"is_complete": true' in direct_display
    assert dispatch(client, "print $lst[1].root", runtime) == direct_display
    assert dispatch(client, '$lst[1].root["is_complete"]', runtime) == "true"
    direct_keys = dispatch(client, '$lst[1].root.keys', runtime).splitlines()
    assert {"translation_unit_decl", "declarations"} <= set(direct_keys)
    assert not {"node", "availability", "is_complete", "supported_scopes"} & set(direct_keys)
    assert dispatch(client, '$lst[1].root.keys[0]', runtime) == "translation_unit_decl"
    assert dispatch(client, '$lst[1].root["node"].keys[0]', runtime) == "translation_unit_decl"
    assert dispatch(client, '$lst[1].root.hasField("is_complete")', runtime) == "true"
    assert dispatch(client, '$lst[1].root.fieldState("is_complete")', runtime) == "PRESENT"
    assert dispatch(client, "$lst[1].root.value.is_complete", runtime) == "true"
    assert "node" in runtime.completion_fields("$lst[1].root")
    assert "is_complete" in runtime.completion_fields("$lst[1].root")
    assert "value" in runtime.completion_fields("$lst[1].root")
    owner.close()
    assert dispatch(client, "$lst[1].root", runtime) == direct_display
    assert "translation_unit_decl" in dispatch(client, "$lst[1].root.value.node.keys", runtime)
    client.assert_not_called()


def test_foreach_lazily_reads_semantic_repeated_fields(tmp_path):
    client, runtime = make_runtime(tmp_path)
    binding = match_result_pb2.MatchBinding(
        availability=[{"field_path": "node"}, {"field_path": "qualified_type"}]
    )
    runtime.bindings["items"] = property_value(view(binding), "availability")

    assert (
        dispatch(client, "foreach $item in $items do $item.field_path done", runtime)
        == "node\nqualified_type"
    )
    client.assert_not_called()


def _record_row():
    row = match_result_pb2.MatchResult()
    binding = row.bindings["root"]
    record = binding.node.cxx_record_decl.record
    named = record.tag.type_declaration.named
    named.qualified_name = "demo::Widget"
    named.name.identifier = "Widget"
    named.declaration.is_implicit = False
    record.tag.is_complete_definition = True
    for field_path in ("RecordDeclInfo.members", "CXXRecordDecl.definition_bases"):
        binding.availability.add(field_path=field_path, state=3)
    return row


def test_binding_keys_expose_readable_record_fields_and_conveniences(tmp_path):
    client, runtime = make_runtime(tmp_path)
    row = _record_row()
    runtime.bindings["lst"] = [MatchRow(row.SerializeToString(), None, 0)]
    keys = dispatch(client, "$lst[0].root.keys", runtime).splitlines()

    assert {
        "cxx_record_decl", "record", "tag", "type_declaration", "named",
        "qualified_name", "decl_name", "record_name", "is_implicit",
        "is_complete_definition",
    } <= set(keys)
    assert not {
        "node", "availability", "is_complete", "supported_scopes", "members",
        "definition_bases", "hasField", "fieldState", "fieldOr",
    } & set(keys)
    assert dispatch(client, "$lst[0].root.decl_name", runtime) == "demo::Widget"
    assert dispatch(client, '$lst[0].root["decl_name"]', runtime) == "demo::Widget"
    assert dispatch(client, "$lst[0].root.qualified_name", runtime) == "demo::Widget"
    assert dispatch(client, '$lst[0].root["record"].tag.is_complete_definition', runtime) == "true"
    assert dispatch(client, "$lst[0].root.record.tag.is_complete_definition", runtime) == "true"
    assert dispatch(client, '$lst[0].root.hasField("record")', runtime) == "true"
    assert dispatch(client, '$lst[0].root.fieldState("members")', runtime) == "UNREQUESTED"
    assert {"record", "decl_name", "qualified_name"} <= set(runtime.completion_fields("$lst[0].root"))
    for key in keys:
        assert not dispatch(client, f'$lst[0].root["{key}"]', runtime).startswith("error:")
    client.assert_not_called()


@pytest.mark.parametrize("blocked", ["node", "AstNode.cxx_record_decl", "NamedDeclInfo.qualified_name"])
def test_binding_keys_respect_unrequested_payloads_and_names(tmp_path, blocked):
    client, runtime = make_runtime(tmp_path)
    row = _record_row()
    row.bindings["root"].availability.add(field_path=blocked, state=3)
    if blocked == "NamedDeclInfo.qualified_name":
        row.bindings["root"].availability.add(field_path="NamedDeclInfo.name", state=3)
    runtime.bindings["lst"] = [MatchRow(row.SerializeToString(), None, 0)]

    keys = set(dispatch(client, "$lst[0].root.keys", runtime).splitlines())
    assert not {"qualified_name", "decl_name", "parameter_name", "record_name"} & keys
    if blocked != "NamedDeclInfo.qualified_name":
        assert not {"record", "tag", "is_implicit", "cxx_record_decl"} & keys
    client.assert_not_called()


def test_foreach_output_is_bounded_and_assignment_remains_atomic(tmp_path):
    client, runtime = make_runtime(tmp_path)
    runtime.bindings["result"] = "old"
    runtime.bindings["items"] = ["x" * 120_000] * 10

    with pytest.raises(EvaluationError, match="foreach output exceeds"):
        runtime.evaluate('let result = foreach $item in $items do $item done')
    assert runtime.bindings["result"] == "old"
    client.assert_not_called()


def test_match_row_preview_bounds_large_protobuf_scalars_without_to_dict(monkeypatch):
    data = match_result_pb2.MatchResult()
    data.bindings["large"].unsupported.detail = "needle-" + "x" * 100_000
    row = MatchRow(data.SerializeToString(), None, 0)

    def reject_full_conversion(self):
        raise AssertionError("render must not convert the complete row to a dict")

    monkeypatch.setattr(MatchRow, "to_dict", reject_full_conversion)
    rendered = render(row)

    assert len(rendered) <= 20_000
    assert '"large"' in rendered
    assert "needle-" in rendered
    assert "truncated" in rendered


def test_inspect_selected_binding_from_match_value_is_json_safe(tmp_path):
    client, runtime = make_runtime(tmp_path)
    row = match_result_pb2.MatchResult()
    row.bindings["f"].unsupported.detail = "semantic payload"
    store = RowStore()
    store.append(row.SerializeToString(), binding_names=row.bindings)
    matches = MatchValue._from_store(store, None)
    runtime.bindings["functions"] = matches

    try:
        output = dispatch(client, "inspect $functions[0].f", runtime)
    finally:
        store.close()

    assert '"type": "BindingSelection"' in output
    assert '"has_semantic_value": true' in output
    assert '"detail": "semantic payload"' in output
    client.assert_not_called()
