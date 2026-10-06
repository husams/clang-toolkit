"""Protect the published wire contract while schemas move between modules."""

from pathlib import Path

from google.protobuf import descriptor_pb2

from clang_toolkit._generated.query.v1 import (
    commands_pb2,
    errors_pb2,
    events_pb2,
    query_pb2,
)
from clang_toolkit._generated.ast.v1 import semantic_types_pb2


def original_contract() -> descriptor_pb2.FileDescriptorProto:
    path = Path(__file__).parent / "fixtures" / "query_v1_wire.pb"
    return descriptor_pb2.FileDescriptorProto.FromString(path.read_bytes())


def test_message_wire_contract_and_legacy_imports_are_preserved():
    original = original_contract()
    modules = (commands_pb2, errors_pb2, events_pb2)
    actual = {
        name: descriptor
        for module in modules
        for name, descriptor in module.DESCRIPTOR.message_types_by_name.items()
    }
    assert set(actual) == {message.name for message in original.message_type}
    for message in original.message_type:
        current = descriptor_pb2.DescriptorProto()
        actual[message.name].CopyToProto(current)
        current_fields = {field.number: field for field in current.field}
        for field in message.field:
            assert current_fields[field.number] == field
        assert actual[message.name].full_name == f"{original.package}.{message.name}"
        assert getattr(query_pb2, message.name).DESCRIPTOR is actual[message.name]


def test_rpc_paths_and_streaming_directions_are_preserved():
    original = original_contract()
    assert set(query_pb2.DESCRIPTOR.services_by_name) == {"QueryService"}
    service = query_pb2.DESCRIPTOR.services_by_name["QueryService"]
    current = descriptor_pb2.ServiceDescriptorProto()
    service.CopyToProto(current)
    assert current == original.service[0]
    assert service.full_name == "ctk.query.v1.QueryService"


def test_legacy_envelope_round_trip_across_modules():
    command = query_pb2.QueryCommand(
        request_id="add-1",
        add_files=query_pb2.AddFiles(files=[query_pb2.FileInput(
            path="source.cpp", working_directory="/project",
            compile_arguments=["-std=c++20"],
        )]),
    )
    assert commands_pb2.QueryCommand.FromString(command.SerializeToString()) == command
    event = query_pb2.QueryEvent(
        request_id="add-1",
        rejected=query_pb2.Rejected(code="LIMIT_REACHED", violations=[
            query_pb2.LimitViolation(limit_name="session.max_files", projected_value=101),
        ]),
    )
    assert events_pb2.QueryEvent.FromString(event.SerializeToString()) == event


def test_type_constraint_preserves_wire_tag_and_json_name():
    field = semantic_types_pb2.TypeConstraint.DESCRIPTOR.fields_by_number[1]
    assert field.name == "concept_reference"
    assert field.json_name == "concept"
