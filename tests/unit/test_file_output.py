import json
from unittest.mock import Mock

import pytest
import yaml
from google.protobuf import descriptor_pool, message_factory

from clang_toolkit.client import Client
from clang_toolkit.cli.runtime import Runtime
from clang_toolkit.cli.runtime.persistence import PersistenceError, load, read_document, save
from clang_toolkit.cli.runtime.references import ReferenceError, index_value, property_value
from clang_toolkit.cli.runtime.semantic import (
    BindingMapView,
    EnumValue,
    MapView,
    MessageView,
    RepeatedView,
    view,
)
from clang_toolkit.cli.runtime.values import MatchSet, MatcherExpr
from clang_toolkit._generated.match.v1 import match_result_pb2, match_service_pb2
from clang_toolkit._generated.ast.v1 import semantic_types_pb2, string_literal_pb2
from clang_toolkit._value_lifecycle import CursorOwner
from clang_toolkit.match_values import MatchValue


@pytest.mark.parametrize("kind", ["json", "yaml", "proto"])
def test_variable_and_environment_paths_roundtrip(tmp_path, kind):
    runtime = Runtime(Mock(spec=Client), cwd=tmp_path, environment={"HOME": str(tmp_path)})
    try:
        runtime.execute('let filename = "$HOME/results"')
        runtime.execute("let x = [1, true, 9007199254740993]")
        runtime.execute(f"save $x to $filename as {kind}")
        if kind == "json":
            assert json.loads((tmp_path / "results.json").read_text()) == [
                1, True, 9007199254740993
            ]
        elif kind == "yaml":
            assert yaml.safe_load((tmp_path / "results.yaml").read_text()) == [
                1, True, 9007199254740993
            ]
        runtime.execute(f'load "$HOME/results.{kind}" into $restored')
        assert runtime.bindings["restored"] == runtime.bindings["x"]
    finally:
        runtime.close()


def test_per_print_replace_append_and_persistent_sink(tmp_path):
    runtime = Runtime(Mock(spec=Client), cwd=tmp_path, environment={"HOME": str(tmp_path)})
    try:
        runtime.execute('let filename = "$HOME/log.txt"')
        runtime.execute('print "old" to $filename')
        runtime.execute('print "new" to $filename mode replace')
        runtime.execute('print "added" to $filename mode append')
        assert (tmp_path / "log.txt").read_text() == "new\nadded\n"
        assert runtime.execute('print "terminal"') == "terminal"
        runtime.execute('set output to $filename mode append')
        runtime.execute('print "persistent"')
        assert (tmp_path / "log.txt").read_text().endswith("persistent\n")
    finally:
        runtime.close()


def test_proto_nested_types_and_invalid_save_preserve_file(tmp_path):
    path = tmp_path / "values.proto"
    value = [2**128, -2**128, [], {}, None, 1.25, "λ", MatcherExpr("functionDecl"),
             MatchSet(({"name": "f", "count": 3},))]
    assert load(save(value, path)) == value
    before = path.read_bytes()
    with pytest.raises(PersistenceError):
        save(object(), path)
    assert path.read_bytes() == before
    assert list(tmp_path.iterdir()) == [path]
    path.write_bytes(b"broken")
    with pytest.raises(PersistenceError):
        load(path)


def _semantic_collection():
    binding = match_result_pb2.MatchBinding(is_complete=False)
    binding.node.string_literal.value = b"quoted\x00\xff"
    binding.supported_scopes.append(999)
    binding.availability.add(
        field_path="node.string_literal.value",
        state=3,
        reason="field is deliberately marked unrequested",
    )
    result = match_result_pb2.MatchResult()
    result.source_match_index = 23
    result.bindings["root"].CopyFrom(binding)
    response = match_service_pb2.MatchResponse()
    response.results.add().CopyFrom(result)
    owner = CursorOwner(object(), "session", 17, lambda _session: None)
    return MatchValue._from_response(response, owner, source_file="sample.cc"), owner


def test_save_binding_selection_exact_console_syntax_is_detached_and_preserves_semantics(tmp_path):
    runtime = Runtime(Mock(spec=Client), cwd=tmp_path, environment={})
    collection, owner = _semantic_collection()
    runtime.bindings["lst"] = collection
    original_row = next(collection.iter_rows())
    original_data = original_row._data
    try:
        target = tmp_path / "data.yaml"
        target.write_text("keep this file\n")
        with pytest.raises(PersistenceError, match="explicit row index"):
            runtime.execute('save $lst.root to "data.yaml" as yaml')
        assert target.read_text() == "keep this file\n"
        runtime.execute('save $lst[0].root to "data.yaml" as yaml')
        assert runtime.execute("print $lst[0].root.is_complete") == "false"
        plain = yaml.safe_load(target.read_text())
        assert plain == {"string_literal": {}}
        runtime.execute('load "data.yaml" into $restored')
        snapshot = runtime.bindings["restored"]
        assert snapshot == plain
        runtime.execute('save $lst[0] to "row.json" as json')
        runtime.execute('load "row.json" into $row_snapshot')
        row_snapshot = runtime.bindings["row_snapshot"]
        assert row_snapshot == {"bindings": {"root": {"string_literal": {}}}}
        assert runtime.execute(
            'print $row_snapshot.bindings["root"].string_literal.isEmpty'
        ) == "true"
        row_text = (tmp_path / "row.json").read_text()
        assert "schema_version" not in row_text
        assert "cursor-" not in row_text and "session_id" not in row_text
        assert len(collection) == 1
        assert next(collection.iter_rows())._data == original_data
        assert owner.revision == 17 and not owner.closed
        assert runtime.client.mock_calls == []
    finally:
        runtime.close()
        owner.close()


@pytest.mark.parametrize("kind", ["json", "yaml"])
def test_plain_binding_exports_ast_facts_but_no_operational_metadata(tmp_path, kind):
    binding = match_result_pb2.MatchBinding(is_complete=False)
    binding.node.string_literal.value = b"literal"
    binding.location.file = "sample.cc"
    binding.location.line = 7
    binding.location.column = 3
    binding.location.valid = True
    binding.location.offset = 0
    binding.range.expansion_begin.file = "sample.cc"
    binding.range.expansion_begin.line = 7
    binding.range.expansion_begin.valid = True
    binding.range.expansion_begin.offset = 0
    binding.range.expansion_end_exclusive.file = "sample.cc"
    binding.range.expansion_end_exclusive.valid = True
    binding.range.expansion_end_exclusive.offset = 9
    binding.symbol_identity = "c:@N@sample"
    binding.documentation = "A declaration."
    binding.call_site.caller_name = "caller"
    binding.call_site.dispatch = match_result_pb2.CALL_DISPATCH_DIRECT
    binding.availability.add(field_path="node.string_literal.other_field", state=3)
    binding.supported_scopes.append(match_result_pb2.BINDING_MATCH_SCOPE_SUBTREE)
    path = save(view(binding), tmp_path / f"binding.{kind}", format_name=kind)
    raw = json.loads(path.read_text()) if kind == "json" else yaml.safe_load(path.read_text())
    assert raw == {
        "string_literal": {"value": "literal"},
        "location": {
            "file": "sample.cc", "line": 7, "column": 3, "valid": True,
            "offset": 0,
        },
        "range": {
            "expansion_begin": {
                "file": "sample.cc", "line": 7, "valid": True, "offset": 0
            },
            "expansion_end_exclusive": {
                "file": "sample.cc", "valid": True, "offset": 9
            },
        },
        "symbol_identity": "c:@N@sample",
        "documentation": "A declaration.",
        "call_site": {
            "caller_name": "caller",
            "dispatch": "CALL_DISPATCH_DIRECT",
        },
    }
    assert not {"availability", "is_complete", "supported_scopes", "node"} & raw.keys()


@pytest.mark.parametrize("kind", ["json", "yaml"])
def test_plain_semantic_result_omits_status_bookkeeping(tmp_path, kind):
    descriptor = descriptor_pool.Default().FindMessageTypeByName(
        "ctk.ast.v1.SemanticResult"
    )
    semantic_result_type = message_factory.GetMessageClass(descriptor)
    semantic_result = semantic_result_type(is_complete=False)
    semantic_result.values.add().string_literal.value = b"node text"
    semantic_result.unsupported_values.add(clang_kind="UnsupportedDecl")
    path = save(view(semantic_result), tmp_path / f"result.{kind}", format_name=kind)
    raw = json.loads(path.read_text()) if kind == "json" else yaml.safe_load(path.read_text())
    assert raw == {"values": [{"string_literal": {"value": "node text"}}]}


def test_plain_binding_export_respects_inherited_availability(tmp_path):
    binding = match_result_pb2.MatchBinding(is_complete=True)
    binding.node.string_literal.value = b"secret"
    inherited = (("node.string_literal.value", 3, "external restriction"),)
    binding_view = MessageView(
        binding.SerializeToString(),
        type(binding),
        inherited,
        binding.DESCRIPTOR.full_name,
    )
    semantic_node = property_value(binding_view, "node")
    literal = property_value(semantic_node, "string_literal")
    with pytest.raises(ReferenceError, match="not requested"):
        property_value(literal, "value")

    binding_path = save(binding_view, tmp_path / "inherited.json")
    assert json.loads(binding_path.read_text()) == {"string_literal": {}}

    row = match_result_pb2.MatchResult()
    row.bindings["root"].CopyFrom(binding)
    row_view = MessageView(
        row.SerializeToString(),
        type(row),
        inherited,
        row.DESCRIPTOR.full_name,
    )
    row_path = save(row_view, tmp_path / "row.json")
    assert json.loads(row_path.read_text()) == {
        "bindings": {"root": {"string_literal": {}}}
    }

    bindings_view = MapView(
        row.SerializeToString(),
        type(row),
        "bindings",
        inherited,
        f"{row.DESCRIPTOR.full_name}.bindings",
    )
    map_path = save(bindings_view, tmp_path / "bindings.json")
    assert json.loads(map_path.read_text()) == {
        "root": {"string_literal": {}}
    }

    unavailable_node = (("node", 3, "external restriction"),)
    blocked_view = MessageView(
        binding.SerializeToString(),
        type(binding),
        unavailable_node,
        binding.DESCRIPTOR.full_name,
    )
    with pytest.raises(ReferenceError, match="not requested"):
        property_value(blocked_view, "node")
    blocked_path = save(blocked_view, tmp_path / "blocked.json")
    assert json.loads(blocked_path.read_text()) == {}


@pytest.mark.parametrize("kind", ["json", "yaml", "proto"])
def test_semantic_fields_containers_enums_and_bytes_roundtrip(tmp_path, kind):
    collection, owner = _semantic_collection()
    try:
        binding = next(collection.iter_rows()).binding("root")
        semantic = property_value(binding, "value")
        availability = property_value(semantic, "availability")
        row = next(collection.iter_rows())
        binding_map = property_value(view(row._message()), "bindings")
        row_bindings = property_value(row, "bindings")
        assert isinstance(row_bindings, BindingMapView)
        literal = view(string_literal_pb2.StringLiteral(value=b"field\x00\xff"))
        wide_integer = view(
            semantic_types_pb2.OffsetOfComponent(array_index=(1 << 64) - 1)
        )
        exported = {
            "binding": binding,
            "message": semantic,
            "node": property_value(semantic, "node"),
            "repeated": availability,
            "map": binding_map,
            "row_bindings": row_bindings,
            "nested": [semantic, {"availability": availability}],
            "enum": property_value(index_value(availability, 0), "state"),
            "literal": literal,
            "wide_integer": wide_integer,
            "byte_field": property_value(literal, "value"),
            "bytes": b"raw\x00\xfe",
        }
        path = save(exported, tmp_path / f"semantic.{kind}", format_name=kind)
        restored = load(path)
        if kind in {"json", "yaml"}:
            raw = json.loads(path.read_text()) if kind == "json" else yaml.safe_load(path.read_text())
            assert restored == raw
            assert raw["binding"] == {"string_literal": {}}
            assert raw["message"] == {"string_literal": {}}
            assert raw["node"] == raw["binding"]
            assert raw["repeated"][0]["state"] == "FIELD_STATE_UNREQUESTED"
            assert raw["map"]["root"] == {"string_literal": {}}
            assert raw["row_bindings"]["root"] == {"string_literal": {}}
            assert raw["enum"] == "FIELD_STATE_UNREQUESTED"
            assert raw["wide_integer"]["array_index"] == (1 << 64) - 1
            assert raw["byte_field"] == "base64:ZmllbGQA/w=="
            assert raw["literal"]["value"] == "base64:ZmllbGQA/w=="
            assert raw["bytes"] == "base64:cmF3AP4="
            assert "message_type" not in raw["message"]
            assert "schema_version" not in raw
        else:
            assert restored["binding"]["name"] == "root"
            restored_semantic = restored["message"]
            assert isinstance(restored_semantic, MessageView)
            assert property_value(restored_semantic, "is_complete") is False
            assert isinstance(restored["repeated"], RepeatedView)
            assert property_value(index_value(restored["repeated"], 0), "state") == EnumValue(
                "FIELD_STATE_UNREQUESTED", 3
            )
            assert isinstance(restored["map"], MapView)
            assert property_value(index_value(restored["map"], "root"), "is_complete") is False
            assert restored["enum"] == EnumValue("FIELD_STATE_UNREQUESTED", 3)
            assert property_value(restored["wide_integer"], "array_index") == (1 << 64) - 1
            assert restored["bytes"] == b"raw\x00\xfe"
    finally:
        owner.close()


def test_semantic_container_exports_include_only_selected_field_and_keep_availability(tmp_path):
    collection, owner = _semantic_collection()
    try:
        row = next(collection.iter_rows())
        binding = property_value(row.binding("root"), "value")
        availability = property_value(binding, "availability")
        availability_path = save(availability, tmp_path / "availability.json")
        availability_doc = json.loads(availability_path.read_text())
        assert isinstance(availability_doc, list)
        assert availability_doc[0]["reason"] == "field is deliberately marked unrequested"
        loaded_availability = load(availability_path)
        assert loaded_availability == availability_doc

        bindings = property_value(view(row._message()), "bindings")
        bindings_path = save(bindings, tmp_path / "bindings.json")
        bindings_doc = json.loads(bindings_path.read_text())
        assert "root" in bindings_doc
        assert bindings_doc["root"] == {"string_literal": {}}
        loaded_bindings = load(bindings_path)
        assert loaded_bindings == bindings_doc
    finally:
        owner.close()


def test_json_export_keeps_deep_repeated_map_and_long_values(tmp_path):
    binding = match_result_pb2.MatchBinding(is_complete=False)
    long_text = "semantic text " * 10_000
    binding.node.string_literal.value = long_text.encode("utf-8")
    for index in range(55):
        binding.availability.add(
            field_path=f"node.string_literal.field_{index}",
            state=3,
            reason=f"reason {index}: " + ("detail " * 200),
        )
    row = match_result_pb2.MatchResult(source_match_index=(1 << 63) + 9)
    for index in range(35):
        row.bindings[f"binding_{index:02d}"].CopyFrom(binding)
    response = match_service_pb2.MatchResponse()
    response.results.add().CopyFrom(row)
    owner = CursorOwner(object(), "session", 17, lambda _session: None)
    collection = MatchValue._from_response(response, owner, source_file="deep.cc")
    requested_availability = property_value(view(binding), "availability")

    deep_type = semantic_types_pb2.QualType()
    current = deep_type.type
    for _ in range(20):
        current = current.pointer_type.pointee_type.type
    current.is_complete = False
    try:
        path = save(
            {
                "matches": collection,
                "deep": view(deep_type),
                "requested_availability": requested_availability,
            },
            tmp_path / "large.json",
        )
        raw = json.loads(path.read_text())
        assert "source_match_index" not in raw["matches"][0]
        assert "source_file" not in raw["matches"][0]
        bindings = raw["matches"][0]["bindings"]
        assert len(bindings) == 35
        assert bindings["binding_34"] == {"string_literal": {"value": long_text}}
        assert len(raw["requested_availability"]) == 55
        assert raw["requested_availability"][-1]["reason"].startswith(
            "reason 54:"
        )
        current = raw["deep"]["type"]
        for _ in range(20):
            current = current["pointer_type"]["pointee_type"]["type"]
        assert "is_complete" not in current
    finally:
        owner.close()


@pytest.mark.parametrize(
    "message_name",
    ["DeclarationValue", "ExpressionValue", "StatementValue", "TypeValue"],
)
def test_plain_ast_export_omits_wrapper_completeness_but_keeps_semantic_fields(
    tmp_path, message_name
):
    descriptor = descriptor_pool.Default().FindMessageTypeByName(
        f"ctk.ast.v1.{message_name}"
    )
    message_type = message_factory.GetMessageClass(descriptor)
    wrapper = message_type(is_complete=False)
    wrapper_path = save(view(wrapper), tmp_path / f"{message_name}.json")
    assert json.loads(wrapper_path.read_text()) == {}

    descriptor = descriptor_pool.Default().FindMessageTypeByName(
        "ctk.ast.v1.TagDeclInfo"
    )
    declaration_type = message_factory.GetMessageClass(descriptor)
    declaration = declaration_type(is_complete_definition=True)
    declaration_path = save(view(declaration), tmp_path / "record.json")
    assert json.loads(declaration_path.read_text()) == {
        "is_complete_definition": True
    }


@pytest.mark.parametrize("snapshot_kind", ["binding_snapshot", "semantic_bindings"])
def test_invalid_binding_snapshot_load_preserves_existing_variable(tmp_path, snapshot_kind):
    runtime = Runtime(Mock(spec=Client), cwd=tmp_path, environment={})
    _collection, owner = _semantic_collection()
    runtime.bindings["restored"] = "keep"
    try:
        if snapshot_kind == "binding_snapshot":
            envelope = {
                "type": "binding_snapshot",
                "value": {"name": "root", "value": {"type": "int", "value": 7}},
            }
        else:
            envelope = {
                "type": "semantic_bindings",
                "value": {"root": {"type": "int", "value": 7}},
            }
        path = tmp_path / f"invalid-{snapshot_kind}.json"
        path.write_text(json.dumps({"schema_version": 1, **envelope}))
        with pytest.raises(PersistenceError, match="binding"):
            runtime.execute(f'load "{path.name}" into $restored')
        assert runtime.bindings["restored"] == "keep"
    finally:
        runtime.close()
        owner.close()


@pytest.mark.parametrize("kind", ["json", "yaml"])
def test_load_ordinary_documents_and_reserved_key_collisions(tmp_path, kind):
    runtime = Runtime(Mock(spec=Client), cwd=tmp_path, environment={})
    document = {
        "availability": "user field",
        "node": {"type": "custom", "value": False},
        "is_complete": False,
        "source_file": "user data",
        "schema_version": 1,
        "type": "bool",
        "value": True,
        "nested": {"type": "record", "value": [False, 0, ""]},
    }
    path = tmp_path / f"ordinary.{kind}"
    try:
        save(document, path, format_name=kind)
        serialized = json.loads(path.read_text()) if kind == "json" else yaml.safe_load(path.read_text())
        assert serialized == document
        runtime.bindings["previous"] = "keep"
        runtime.execute(f'load "ordinary.{kind}" into $loaded')
        assert runtime.bindings["loaded"] == document
        assert read_document(path) == document

        # Exact legacy shape and known version remains supported.
        legacy = {
            "schema_version": 1,
            "type": "list",
            "value": [
                {"type": "bool", "value": False},
                {"type": "int", "value": 0},
                {"type": "str", "value": ""},
            ],
        }
        path.write_text(
            json.dumps(legacy) if kind == "json" else yaml.safe_dump(legacy)
        )
        runtime.execute(f'load "ordinary.{kind}" into $legacy')
        assert runtime.bindings["legacy"] == [False, 0, ""]

        malformed = {"schema_version": 1, "type": "bool", "value": "false"}
        path.write_text(
            json.dumps(malformed) if kind == "json" else yaml.safe_dump(malformed)
        )
        with pytest.raises(PersistenceError, match="typed value"):
            runtime.execute(f'load "ordinary.{kind}" into $previous')
        assert runtime.bindings["previous"] == "keep"
    finally:
        runtime.close()
