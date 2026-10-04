#!/usr/bin/env python3
"""Compile and verify the self-contained semantic AST protobuf contract."""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from google.protobuf import descriptor_pb2, descriptor_pool, json_format, message_factory

sys.dont_write_bytecode = True
from generate_nodes import ROOT, field_name, render


EXPECTED_INCLUDED = 251
EXPECTED_FAMILIES = {"decl": 66, "expr": 104, "stmt": 29, "type": 52}
UNIT_VARIANTS = {"BreakStmt", "ContinueStmt", "NullStmt", "SEHLeaveStmt"}
WRAPPER_BY_FAMILY = {
    "decl": "DeclarationValue",
    "expr": "ExpressionValue",
    "stmt": "StatementValue",
    "type": "TypeValue",
}
FORBIDDEN_MESSAGE_NAMES = {
    "NodeId", "NodeRef", "SnapshotRef", "FileId", "SourceLocation", "SourceRange", "TypeLoc",
}
FORBIDDEN_TYPE_NAMES = FORBIDDEN_MESSAGE_NAMES | {"SourceLocationValue", "SourceRangeValue"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def all_messages(files: descriptor_pb2.FileDescriptorSet):
    def visit(file_name, message, prefix=""):
        full_name = f"{prefix}.{message.name}" if prefix else message.name
        yield file_name, full_name, message
        for nested in message.nested_type:
            yield from visit(file_name, nested, full_name)

    for file in files.file:
        for message in file.message_type:
            yield from visit(file.name, message)


def make_pool(files: descriptor_pb2.FileDescriptorSet) -> descriptor_pool.DescriptorPool:
    pool = descriptor_pool.DescriptorPool()
    remaining = list(files.file)
    while remaining:
        pending = []
        for file in remaining:
            try:
                pool.Add(file)
            except TypeError:
                pending.append(file)
        require(len(pending) < len(remaining), "Descriptor dependency cycle or invalid import")
        remaining = pending
    return pool


def assert_no_handles_or_source_locations(files: descriptor_pb2.FileDescriptorSet) -> None:
    handle_field = re.compile(r"(^|_)ids?($|_)", re.IGNORECASE)
    for file_name, full_name, message in all_messages(files):
        require(full_name.rsplit(".", 1)[-1] not in FORBIDDEN_MESSAGE_NAMES,
                f"Forbidden handle/location message remains: {file_name}:{full_name}")
        require(not message.options.map_entry, "Property maps are not typed semantic contracts")
        for field in message.field:
            type_leaf = field.type_name.rsplit(".", 1)[-1] if field.type_name else ""
            require(type_leaf not in FORBIDDEN_TYPE_NAMES,
                    f"Forbidden field type remains: {full_name}.{field.name}: {type_leaf}")
            require(not handle_field.search(field.name),
                    f"Opaque identity field remains: {full_name}.{field.name}")
            require(field.type_name not in (".google.protobuf.Struct", ".google.protobuf.Any"),
                    f"Generic field replaces a typed semantic value: {full_name}.{field.name}")
            require(not field.type_name.endswith("NodeId") and not field.type_name.endswith("NodeRef"),
                    f"Opaque AST edge remains: {full_name}.{field.name}")
    for file in files.file:
        for enum in file.enum_type:
            require(enum.value and enum.value[0].number == 0 and
                    enum.value[0].name.endswith("UNSPECIFIED"),
                    f"{enum.name} lacks an unspecified zero value")


def check_catalog_and_wrappers(
    files: descriptor_pb2.FileDescriptorSet,
    included: dict[str, dict],
    registry: dict[str, dict],
) -> None:
    messages = {message.name: (file, message)
                for file in files.file for message in file.message_type}
    expected_names = set(included)
    require(len(included) == EXPECTED_INCLUDED,
            f"Expected {EXPECTED_INCLUDED} included catalog kinds, got {len(included)}")
    family_counts = Counter(entry["family"] for entry in included.values())
    require(dict(family_counts) == EXPECTED_FAMILIES,
            f"Included family counts changed: {dict(family_counts)}")
    require(set(registry) == expected_names,
            "node_tags.json does not exactly cover the included catalog kinds")

    node_file, node = messages["AstNode"]
    node_payload = node.oneof_decl[0].name
    node_fields = {field.type_name.rsplit(".", 1)[-1]: field for field in node.field
                   if field.HasField("oneof_index") and node.oneof_decl[field.oneof_index].name == node_payload}
    require(set(node_fields) == expected_names, "AstNode union does not exactly cover included catalog kinds")

    for name, entry in included.items():
        require(name in messages, f"Missing concrete message {name}")
        file, message = messages[name]
        require(file.name == entry["protobuf_file"], f"{name} is in the wrong contract file")
        if name not in UNIT_VARIANTS:
            require(bool(message.field), f"{name} is an empty placeholder")
        else:
            require(not message.field, f"Unit semantic variant {name} unexpectedly has fields")
        field = node_fields[name]
        tag = registry[name]["tag"]
        require(field.number == tag, f"AstNode tag changed for {name}: expected {tag}, got {field.number}")
        require(field.name == field_name(name), f"AstNode payload name changed for {name}")
        require(registry[name]["family"] == entry["family"], f"Registry family disagrees for {name}")

    excluded = {entry["name"] for entry in json.loads((ROOT / "catalog.json").read_text())["classes"]
                if entry["status"] != "included"}
    require(not excluded.intersection(messages), "Excluded/deferred core class is exposed")

    for family, wrapper_name in WRAPPER_BY_FAMILY.items():
        wrapper = messages[wrapper_name][1]
        require(wrapper.oneof_decl, f"{wrapper_name} has no payload oneof")
        oneof_name = wrapper.oneof_decl[0].name
        actual = {field.type_name.rsplit(".", 1)[-1]: field for field in wrapper.field
                  if field.HasField("oneof_index") and wrapper.oneof_decl[field.oneof_index].name == oneof_name}
        expected = {name for name, entry in included.items() if entry["family"] == family}
        if family == "stmt":
            # Expressions are valid StatementValue alternatives by design.
            expression_field = actual.pop("ExpressionValue", None)
            require(expression_field is not None and expression_field.name == "expression" and
                    expression_field.number == 10,
                    "StatementValue must retain its inline ExpressionValue alternative")
        require(set(actual) == expected,
                f"{wrapper_name} coverage mismatch: missing={sorted(expected - set(actual))}, "
                f"extra={sorted(set(actual) - expected)}")
        for name in expected:
            field = actual[name]
            require(field.number == registry[name]["tag"],
                    f"{wrapper_name} tag changed for {name}")
            require(field.name == field_name(name), f"{wrapper_name} payload name changed for {name}")


def assert_finite_symbol_contract(pool: descriptor_pool.DescriptorPool) -> None:
    symbol = pool.FindMessageTypeByName("ctk.ast.v1.DeclarationSymbol")
    expected = {
        "type": "TypeDescription",
        "function": "FunctionSignature",
        "template_arguments": "TemplateArgumentDescription",
    }
    enum_fields = {"kind": "SymbolKind", "overloaded_operator": "OverloadedOperatorKind"}
    scalar_types = {
        "name": symbol.fields_by_name["name"].TYPE_STRING,
        "kind": "SymbolKind",
        "qualified_name": symbol.fields_by_name["qualified_name"].TYPE_STRING,
        "clang_class": symbol.fields_by_name["clang_class"].TYPE_STRING,
        "is_parameter_pack": symbol.fields_by_name["is_parameter_pack"].TYPE_BOOL,
    }
    del scalar_types["kind"]
    actual = {field.name: field for field in symbol.fields}
    require(set(actual) == set(expected) | set(enum_fields) | set(scalar_types),
            "DeclarationSymbol is not the finite typed contract")
    for name, type_name in expected.items():
        field = actual[name]
        require(field.message_type or field.enum_type, f"DeclarationSymbol.{name} is untyped")
        require((field.message_type or field.enum_type).name == type_name,
                f"DeclarationSymbol.{name} has wrong type")
        require(field.type not in (field.TYPE_MESSAGE,) or field.message_type is not None,
                f"DeclarationSymbol.{name} is an untyped message")
    for name, type_name in enum_fields.items():
        require(actual[name].enum_type and actual[name].enum_type.name == type_name,
                f"DeclarationSymbol.{name} has wrong enum type")
    for name, scalar_type in scalar_types.items():
        require(actual[name].type == scalar_type,
                f"DeclarationSymbol.{name} has wrong scalar type")
    require(actual["template_arguments"].is_repeated,
            "DeclarationSymbol.template_arguments must be a typed repeated field")

    forbidden_reachable = {"ExpressionValue", "DeclarationValue", "TypeValue"}
    pending = [symbol]
    visited = set()
    while pending:
        message = pending.pop()
        if message.full_name in visited:
            continue
        visited.add(message.full_name)
        require(message.name not in forbidden_reachable,
                f"DeclarationSymbol can expand into owned AST payload {message.full_name}")
        pending.extend(field.message_type for field in message.fields if field.message_type)


def check_wire(pool: descriptor_pool.DescriptorPool, files: descriptor_pb2.FileDescriptorSet) -> None:
    def cls(name: str):
        return message_factory.GetMessageClass(pool.FindMessageTypeByName("ctk.ast.v1." + name))

    def roundtrip(message):
        return type(message).FromString(message.SerializeToString())

    # Explicit false remains distinguishable from an absent optional flag.
    variable = cls("VarDeclInfo")()
    require(not variable.HasField("is_constexpr"), "Missing flag has lost absence")
    variable.is_constexpr = False
    require(roundtrip(variable).HasField("is_constexpr"), "Explicit false has lost presence")

    # Constant precision exceeds protobuf numeric scalar widths.
    integer = (1 << 126) + (1 << 65) + 19
    bits = cls("APIntBits")(bit_width=127, little_endian_bits=integer.to_bytes(16, "little"))
    result = roundtrip(bits)
    require(result.bit_width == 127 and int.from_bytes(result.little_endian_bits, "little") == integer,
            "Wide integer bit pattern changed")
    signed = cls("APSIntBits")(value=bits, is_unsigned=False)
    signed_result = roundtrip(signed)
    require(signed_result.HasField("is_unsigned") and not signed_result.is_unsigned,
            "Integer signedness changed")

    # IEEE double negative zero and a NaN payload survive as raw exact bits.
    for pattern in (0x8000000000000000, 0x7FF800000000007B):
        floating = cls("APFloatBits")(
            semantics=4,
            bit_pattern=cls("APIntBits")(
                bit_width=64, little_endian_bits=pattern.to_bytes(8, "little")
            ),
        )
        require(roundtrip(floating) == floating, "Floating bits/semantics changed")

    # Arguments are owned expression values; order and literal content survive.
    call = cls("CallExprInfo")()
    for value in (9, 2, 7):
        arg = call.arguments.add()
        arg.integer_literal.info.type.CopyFrom(builtin_qual_type(cls))
        arg.integer_literal.value.bit_width = 32
        arg.integer_literal.value.little_endian_bits = value.to_bytes(4, "little")
    call_result = roundtrip(call)
    actual_args = [int.from_bytes(arg.integer_literal.value.little_endian_bits, "little")
                   for arg in call_result.arguments]
    require(actual_args == [9, 2, 7], "Inline expression argument order or values changed")
    require(call_result.arguments[0].WhichOneof("payload") == "integer_literal",
            "Call argument is not an inline typed expression")

    argument = cls("TemplateArgument")()
    argument.pack.elements.add().null_argument.SetInParent()
    argument.pack.elements.add().integral.value.CopyFrom(signed)
    require(roundtrip(argument).WhichOneof("value") == "pack", "Template pack discriminator changed")

    # A qualified builtin is a real TypeValue payload, not a numeric node key.
    qualified = cls("QualType")()
    qualified.type.CopyFrom(make_builtin_type(cls, "BUILTIN_KIND_INT"))
    qualified.qualifiers.is_const = True
    qualified_result = roundtrip(qualified)
    require(qualified_result.qualifiers.is_const, "Qualified type lost qualifiers")
    require(qualified_result.type.WhichOneof("payload") == "builtin_type" and
            qualified_result.type.builtin_type.kind ==
            cls("BuiltinType")().DESCRIPTOR.fields_by_name["kind"].enum_type.values_by_name[
                "BUILTIN_KIND_INT"].number,
            "QualType no longer embeds the expected builtin TypeValue")

    check_semantic_function_fixture(cls, roundtrip)

    # Older clients see no known payload for a newly added oneof case. Binary
    # forwarding must retain that unknown case without an identity envelope.
    newer = cls("AstNode")()
    newer.dependent_decltype_type.info.spelling = "decltype(value)"
    old_files = descriptor_pb2.FileDescriptorSet()
    old_files.CopyFrom(files)
    for file in old_files.file:
        for message in file.message_type:
            if message.name == "AstNode":
                retained = [field for field in message.field if field.name != "dependent_decltype_type"]
                del message.field[:]
                message.field.extend(retained)
    old_pool = make_pool(old_files)
    old_class = message_factory.GetMessageClass(old_pool.FindMessageTypeByName("ctk.ast.v1.AstNode"))
    older = old_class.FromString(newer.SerializeToString())
    require(older.WhichOneof("payload") is None, "Unknown oneof case was incorrectly interpreted")
    recovered = cls("AstNode").FromString(older.SerializeToString())
    require(recovered.WhichOneof("payload") == "dependent_decltype_type",
            "Unknown binary case was not preserved through an older client")


def make_builtin_type(cls, kind_name: str):
    value = cls("TypeValue")()
    builtin = value.builtin_type
    builtin.info.spelling = "int"
    kind = builtin.DESCRIPTOR.fields_by_name["kind"].enum_type.values_by_name[kind_name].number
    builtin.kind = kind
    return value


def make_type_description(cls, spelling: str):
    value = cls("TypeDescription")()
    value.spelling = spelling
    value.canonical_spelling = spelling
    value.is_dependent = False
    return value


def builtin_qual_type(cls, kind_name: str = "BUILTIN_KIND_INT"):
    result = cls("QualType")()
    result.type.CopyFrom(make_builtin_type(cls, kind_name))
    return result


def function_qual_type(cls):
    result = cls("QualType")()
    function = result.type.function_proto_type
    function.info.spelling = "int (int, int)"
    function.return_type.CopyFrom(builtin_qual_type(cls))
    function.parameter_types.add().CopyFrom(builtin_qual_type(cls))
    function.parameter_types.add().CopyFrom(builtin_qual_type(cls))
    function.is_variadic = False
    return result


def function_pointer_qual_type(cls):
    result = cls("QualType")()
    pointer = result.type.pointer_type
    pointer.info.spelling = "int (*)(int, int)"
    pointer.pointee_type.CopyFrom(function_qual_type(cls))
    return result


def enum_number(message, field_name: str, value_name: str) -> int:
    return message.DESCRIPTOR.fields_by_name[field_name].enum_type.values_by_name[value_name].number


def make_integer_expression(cls, value: int):
    expression = cls("ExpressionValue")()
    literal = expression.integer_literal
    literal.info.type.CopyFrom(builtin_qual_type(cls))
    literal.info.value_category = 1  # VALUE_CATEGORY_PRVALUE
    literal.value.bit_width = 32
    literal.value.little_endian_bits = value.to_bytes(4, "little")
    return expression


def make_parameter_symbol(cls):
    parameter = cls("DeclarationSymbol")()
    set_symbol_name(parameter, "input")
    parameter.qualified_name = "demo::score::input"
    parameter.kind = 11  # SYMBOL_KIND_PARAMETER
    parameter.type.CopyFrom(make_type_description(cls, "int"))
    return parameter


def set_symbol_name(symbol, value: str) -> None:
    name_field = symbol.DESCRIPTOR.fields_by_name["name"]
    if name_field.message_type:
        symbol.name.identifier = value
    else:
        symbol.name = value


def get_symbol_name(symbol) -> str:
    name_field = symbol.DESCRIPTOR.fields_by_name["name"]
    return symbol.name.identifier if name_field.message_type else symbol.name


def make_parameter_reference(cls, parameter):
    expression = cls("ExpressionValue")()
    reference = expression.decl_ref_expr
    reference.info.type.CopyFrom(builtin_qual_type(cls))
    reference.info.value_category = 2  # VALUE_CATEGORY_LVALUE
    reference.declaration.CopyFrom(parameter)
    reference.name.identifier = "input"
    return expression


def build_semantic_function(cls):
    result = cls("SemanticResult")()
    result.is_complete = True
    function_node = result.values.add()
    function = function_node.function_decl
    info = function.function
    named = info.declarator.value.named
    named.name.identifier = "score"
    named.qualified_name = "demo::score"
    set_symbol_name(named.declaration.containing_scope, "demo")
    named.declaration.containing_scope.qualified_name = "demo"
    named.declaration.containing_scope.kind = 1  # SYMBOL_KIND_NAMESPACE
    info.return_type.CopyFrom(builtin_qual_type(cls))
    info.is_this_declaration_a_definition = True
    info.is_variadic = False

    parameter_symbol = make_parameter_symbol(cls)
    parameter = info.parameters.add().parm_var_decl
    parameter.variable.declarator.value.named.name.identifier = "input"
    parameter.variable.declarator.value.named.qualified_name = "demo::score::input"
    set_symbol_name(parameter.variable.declarator.value.named.declaration.containing_scope, "demo")
    parameter.variable.declarator.value.named.declaration.containing_scope.qualified_name = "demo"
    parameter.variable.declarator.value.named.declaration.containing_scope.kind = 1
    parameter.variable.declarator.value.type.CopyFrom(builtin_qual_type(cls))
    parameter.variable.declarator.declared_type.CopyFrom(builtin_qual_type(cls))
    parameter.is_parameter_pack = False

    body = info.body.compound_stmt
    body.is_statement_expression = False

    # Keep the overload's complete signature and both actual argument values inline.
    call_statement = body.body.add().expression.call_expr.call
    call_statement.expression.type.CopyFrom(builtin_qual_type(cls))
    call_statement.expression.value_category = 1
    callee_cast = call_statement.callee_expression.implicit_cast_expr.cast
    callee_cast.expression.type.CopyFrom(function_pointer_qual_type(cls))
    callee_cast.expression.value_category = 1
    callee_cast.kind = enum_number(callee_cast, "kind", "CAST_KIND_FUNCTION_TO_POINTER_DECAY")
    callee_reference = callee_cast.operand.decl_ref_expr
    callee_reference.info.type.CopyFrom(function_qual_type(cls))
    callee_reference.info.value_category = 2
    set_symbol_name(callee_reference.declaration, "choose")
    callee_reference.declaration.qualified_name = "demo::choose"
    callee_reference.declaration.kind = 5  # SYMBOL_KIND_FUNCTION
    callee_reference.name.identifier = "choose"
    callee = call_statement.direct_callee
    set_symbol_name(callee, "choose")
    callee.qualified_name = "demo::choose"
    callee.kind = 5
    callee.clang_class = "FunctionDecl"
    callee.function.return_type.CopyFrom(make_type_description(cls, "int"))
    callee.function.is_variadic = False
    for name in ("value", "adjustment"):
        arg_type = callee.function.parameters.add()
        arg_type.name = name
        arg_type.type.CopyFrom(make_type_description(cls, "int"))
        arg_type.is_parameter_pack = False
    call_statement.arguments.add().CopyFrom(make_parameter_reference(cls, parameter_symbol))
    call_statement.arguments.add().CopyFrom(make_integer_expression(cls, 3))

    return_statement = body.body.add().return_stmt
    binary = return_statement.return_value.binary_operator
    binary.info.type.CopyFrom(builtin_qual_type(cls))
    binary.info.value_category = 1
    binary.opcode = 1  # BINARY_OPCODE_ADD
    binary.left.CopyFrom(make_parameter_reference(cls, parameter_symbol))
    binary.right.CopyFrom(make_integer_expression(cls, 1))
    result.values.add().CopyFrom(make_recursive_record_pointer(cls))
    return result


def make_recursive_record_pointer(cls):
    node = cls("AstNode")()
    record = node.cxx_record_decl.record
    named = record.tag.type_declaration.named
    named.name.identifier = "Node"
    named.qualified_name = "demo::Node"
    set_symbol_name(named.declaration.containing_scope, "demo")
    named.declaration.containing_scope.qualified_name = "demo"
    named.declaration.containing_scope.kind = 1  # SYMBOL_KIND_NAMESPACE
    record.tag.tag_kind = 1  # TAG_KIND_STRUCT
    record.tag.is_complete_definition = True

    field = record.members.add().field_decl
    field_named = field.declarator.value.named
    field_named.name.identifier = "next"
    field_named.qualified_name = "demo::Node::next"
    set_symbol_name(field_named.declaration.containing_scope, "Node")
    field_named.declaration.containing_scope.qualified_name = "demo::Node"
    field_named.declaration.containing_scope.kind = 2  # SYMBOL_KIND_RECORD

    pointer_type = field.declarator.value.type
    pointer_type.type.pointer_type.info.spelling = "demo::Node *"
    pointer_type.type.pointer_type.pointee_type.type.record_type.info.spelling = "demo::Node"
    record_symbol = pointer_type.type.pointer_type.pointee_type.type.record_type.declaration
    set_symbol_name(record_symbol, "Node")
    record_symbol.qualified_name = "demo::Node"
    record_symbol.kind = 2  # SYMBOL_KIND_RECORD
    record_symbol.clang_class = "CXXRecordDecl"
    field.declarator.declared_type.CopyFrom(pointer_type)
    return node


def check_semantic_function_fixture(cls, roundtrip) -> None:
    expected = roundtrip(build_semantic_function(cls))
    function = expected.values[0].function_decl.function
    require(function.declarator.value.named.qualified_name == "demo::score",
            "Function fixture lost its qualified name")
    require(function.return_type.type.builtin_type.kind == 17,
            "Function fixture lost its builtin return type")
    parameter = function.parameters[0].parm_var_decl
    require(parameter.variable.declarator.value.type.type.builtin_type.kind == 17 and
            parameter.variable.declarator.value.named.name.identifier == "input",
            "Function fixture lost its parameter name or builtin type")

    statements = function.body.compound_stmt.body
    call = statements[0].expression.call_expr.call
    require(call.direct_callee.qualified_name == "demo::choose" and
            len(call.direct_callee.function.parameters) == 2 and
            call.direct_callee.function.return_type.spelling == "int" and
            [p.type.spelling for p in call.direct_callee.function.parameters] == ["int", "int"],
            "Inline direct-callee overload signature is incomplete")
    callee_cast = call.callee_expression.implicit_cast_expr.cast
    require(callee_cast.kind == enum_number(callee_cast, "kind", "CAST_KIND_FUNCTION_TO_POINTER_DECAY") and
            callee_cast.operand.decl_ref_expr.info.type.type.WhichOneof("payload") == "function_proto_type" and
            callee_cast.expression.type.type.WhichOneof("payload") == "pointer_type" and
            callee_cast.expression.type.type.pointer_type.pointee_type.type.WhichOneof("payload") ==
            "function_proto_type" and
            len(callee_cast.expression.type.type.pointer_type.pointee_type.type.function_proto_type
                .parameter_types) == 2,
            "Call callee must be a function designator decayed to a pointer to its overload type")
    require(len(call.arguments) == 2 and call.arguments[0].WhichOneof("payload") == "decl_ref_expr" and
            get_symbol_name(call.arguments[0].decl_ref_expr.declaration) == "input" and
            call.arguments[1].WhichOneof("payload") == "integer_literal" and
            int.from_bytes(call.arguments[1].integer_literal.value.little_endian_bits, "little") == 3,
            "Call arguments do not contain readable semantic expression values")

    returned = statements[1].return_stmt.return_value.binary_operator
    require(get_symbol_name(returned.left.decl_ref_expr.declaration) == "input" and
            int.from_bytes(returned.right.integer_literal.value.little_endian_bits, "little") == 1,
            "Return binary expression does not inline the named parameter and integer literal")

    require(len(expected.values) == 2 and
            expected.values[1].WhichOneof("payload") == "cxx_record_decl",
            "Recursive record pointer fixture is missing")
    field_type = expected.values[1].cxx_record_decl.record.members[0].field_decl.declarator.value.type
    pointer = field_type.type.pointer_type
    record_symbol = pointer.pointee_type.type.record_type.declaration
    require(pointer.info.spelling == "demo::Node *" and
            record_symbol.qualified_name == "demo::Node" and
            record_symbol.kind == 2 and
            get_symbol_name(record_symbol) == "Node",
            "Recursive record pointer does not carry its finite named record symbol")

    example_path = ROOT / "examples" / "semantic_function.json"
    example_path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json_format.MessageToJson(expected, preserving_proto_field_name=True, indent=2)
    example_path.write_text(encoded + "\n")
    loaded = cls("SemanticResult")()
    json_format.Parse(example_path.read_text(), loaded)
    require(loaded == expected, "Exported semantic function JSON does not round-trip to its validated message")
    # Re-read the public artifact as an independent consumer with no AST lookup service.
    consumer_function = loaded.values[0].function_decl.function
    require(consumer_function.declarator.value.named.qualified_name == "demo::score" and
            consumer_function.body.compound_stmt.body[0].expression.call_expr.call.direct_callee.function
            .parameters[1].name == "adjustment",
            "JSON consumer cannot read function identity/signature without lookup")
    consumer_pointer = loaded.values[1].cxx_record_decl.record.members[0].field_decl.declarator.value.type
    require(consumer_pointer.type.pointer_type.pointee_type.type.record_type.declaration.qualified_name ==
            "demo::Node", "JSON consumer cannot read the recursive record pointer without lookup")


def main() -> None:
    require(shutil.which("protoc") is not None, "protoc is required")
    require((ROOT / "ast/v1/node.proto").read_text() == render(), "node.proto is stale")
    protos = sorted(ROOT.glob("ast/v1/*.proto"))
    with tempfile.TemporaryDirectory(prefix="ctk-api-check-") as temp:
        descriptor = Path(temp) / "ast.pb"
        subprocess.run(
            ["protoc", "-I", str(ROOT), "--include_imports", f"--descriptor_set_out={descriptor}",
             *map(str, protos)],
            check=True,
        )
        files = descriptor_pb2.FileDescriptorSet.FromString(descriptor.read_bytes())

    catalog = json.loads((ROOT / "catalog.json").read_text())
    registry = json.loads((ROOT / "node_tags.json").read_text())["tags"]
    included = {entry["name"]: entry for entry in catalog["classes"] if entry["status"] == "included"}
    decisions = [entry["name"] for entry in catalog["classes"]]
    require(len(decisions) == len(set(decisions)), "Duplicate catalog classes")
    assert_no_handles_or_source_locations(files)
    check_catalog_and_wrappers(files, included, registry)
    pool = make_pool(files)
    assert_finite_symbol_contract(pool)
    check_wire(pool, files)
    family_counts = Counter(entry["family"] for entry in included.values())
    print(f"PASS: {len(protos)} protos compile; {len(included)} self-contained node payloads "
          f"{dict(family_counts)}")
    print("PASS: four wrapper coverages, stable tags, no handles/source locations, finite typed symbols")
    print("PASS: presence, exact bits, inline arguments, template packs, QualType values and unknown variants")
    print("PASS: semantic function JSON round-trips and is readable without AST lookup")


if __name__ == "__main__":
    main()
