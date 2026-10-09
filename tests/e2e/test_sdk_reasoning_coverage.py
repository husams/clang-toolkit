"""Positive native C++ semantic facts through the public Python SDKs."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

from clang_toolkit import AsyncClient, Client, CfgOptions, Matcher
from clang_toolkit._generated.analysis.v1 import cfg_element_pb2
from clang_toolkit._generated.ast.v1 import common_pb2
from test_network_steps import RunningServer, _launch_server

pytestmark = pytest.mark.e2e
scenarios("sdk_reasoning_coverage.feature")


def _field_state(binding, suffix: str) -> int:
    matches = [
        entry.state for entry in binding.availability
        if entry.field_path.endswith(suffix)
    ]
    assert len(matches) == 1, (suffix, [entry.field_path for entry in binding.availability])
    return matches[0]


def _function_binding(nodes, name: str):
    for item in nodes:
        binding = item.value
        if binding.WhichOneof("value") != "node":
            continue
        node = binding.node
        if node.WhichOneof("payload") != "function_decl":
            continue
        function = node.function_decl.function
        declaration_name = function.declarator.value.named.name
        if declaration_name.WhichOneof("value") == "identifier" and declaration_name.identifier == name:
            return binding
    raise AssertionError(f"function declaration not present in traversal: {name}")


@given("a private server and source with SDK reasoning facts", target_fixture="sdk_reasoning")
def sdk_reasoning(tmp_path: Path, request) -> tuple[RunningServer, Path]:
    source = tmp_path / "sdk_reasoning.cc"
    source.write_text(
        "/// Raw docs retained on this declaration.\n"
        "int documented(int);\n"
        "template<class T, int N> struct Box {};\n"
        "Box<int, 7> instantiated;\n"
        "using Count = const int;\n"
        "using CountRef = Count&;\n"
        "struct Base {};\n"
        "struct Derived : public Base {};\n"
        "struct Dtor { ~Dtor() {} };\n"
        "void cfg_target() { Dtor item; }\n"
        "int body_target() { return 7; }\n",
        encoding="utf-8",
    )
    return _launch_server("unix", tmp_path, request), source


def _check_match_facts(client, source: Path):
    compile_arguments = ("-std=c++20",)

    with client.match(
        'functionDecl(hasName("documented")).bind("decl")', file=source,
        compile_arguments=compile_arguments,
    ) as rows:
        assert len(rows) == 1
        documented = rows[0].binding("decl").value
        assert "Raw docs retained on this declaration." in documented.documentation
        function = documented.node.function_decl.function
        assert function.HasField("is_this_declaration_a_definition")
        assert not function.is_this_declaration_a_definition
        assert _field_state(documented, "FunctionDeclInfo.body") == common_pb2.FIELD_STATE_SEMANTICALLY_ABSENT
        assert _field_state(documented, "is_this_declaration_a_definition") == common_pb2.FIELD_STATE_PRESENT
        docs_wire = rows[0].to_dict()

    with client.match(
        'classTemplateSpecializationDecl(hasName("Box")).bind("spec")', file=source,
        compile_arguments=compile_arguments,
    ) as rows:
        assert len(rows) >= 1
        specialization = rows[0].binding("spec").value.node.class_template_specialization_decl
        assert specialization.specialized_template.name == "Box"
        assert specialization.HasField("specialization_kind")
        specialization_wire = rows[0].to_dict()

    # Match bindings are intentionally shallow. Recursive traversal exercises
    # the specialization's template arguments in the complete AST projection.
    traversal = client.traverse(
        source, compile_arguments=compile_arguments,
        visit_template_instantiations=True, projection="recursive",
    )
    cfg_binding = _function_binding(traversal.nodes, "body_target")
    cfg_function = cfg_binding.node.function_decl.function
    assert cfg_function.HasField("body")
    assert cfg_function.body.HasField("is_complete")
    assert not cfg_function.body.is_complete
    assert _field_state(cfg_binding, "FunctionDeclInfo.body") == common_pb2.FIELD_STATE_PRESENT
    body_availability = tuple(
        (entry.field_path, entry.state) for entry in cfg_binding.availability
    )
    traversal_wire = traversal.SerializeToString(deterministic=True)

    tiny_traversal = client.traverse(
        source, compile_arguments=compile_arguments,
        visit_template_instantiations=True, projection="recursive", payload_nodes=2,
    )
    tiny_cfg_binding = _function_binding(tiny_traversal.nodes, "body_target")
    assert tiny_cfg_binding.HasField("is_complete")
    assert not tiny_cfg_binding.is_complete
    assert any(
        entry.state == common_pb2.FIELD_STATE_TRUNCATED
        and entry.field_path == "CompoundStmt"
        for entry in tiny_cfg_binding.availability
    )
    tiny_traversal_wire = tiny_traversal.SerializeToString(deterministic=True)

    specializations = []
    for item in traversal.nodes:
        binding = item.value
        if binding.WhichOneof("value") != "node":
            continue
        node = binding.node
        if node.WhichOneof("payload") != "class_template_specialization_decl":
            continue
        specialization = node.class_template_specialization_decl
        if specialization.specialized_template.name == "Box":
            specializations.append(specialization)
    assert any(len(spec.template_arguments) >= 2 for spec in specializations)
    template_wire = traversal_wire

    with client.match(
        'typeAliasDecl(hasName("CountRef")).bind("alias")', file=source,
        compile_arguments=compile_arguments,
    ) as rows:
        assert len(rows) == 1
        underlying = rows[0].binding("alias").value.node.type_alias_decl.underlying_type
        assert underlying.description.spelling == "Count &"
        assert underlying.description.canonical_spelling == "const int &"
        alias_wire = rows[0].to_dict()

    base_matcher = Matcher(
        "cxxRecordDecl",
        Matcher("hasName", "Derived"),
        Matcher("hasAnyBase", Matcher("cxxBaseSpecifier").bind("base")),
    ).bind("record")
    with client.match(base_matcher, file=source, compile_arguments=compile_arguments) as rows:
        assert len(rows) == 1
        base = rows[0].binding("base").value
        assert base.WhichOneof("value") == "base_specifier"
        assert base.base_specifier.type.description.spelling == "Base"
        assert base.base_specifier.access == common_pb2.ACCESS_SPECIFIER_PUBLIC
        assert not base.base_specifier.is_virtual
        assert not base.base_specifier.is_pack_expansion
        assert not base.supported_scopes
        assert base.location.valid
        assert base.location.file == str(source.resolve())
        assert base.range.expansion_begin.valid
        assert base.range.expansion_begin.file == str(source.resolve())
        assert base.range.spelling_begin.valid
        assert base.range.spelling_begin.file == str(source.resolve())
        base_wire = rows[0].to_dict()

    with client.match(
        'functionDecl(hasName("cfg_target")).bind("decl")', file=source,
        compile_arguments=compile_arguments,
    ) as rows:
        assert len(rows) == 1
        declaration = rows[0].binding("decl").value
        assert not declaration.node.function_decl.function.HasField("body")
        assert _field_state(declaration, "FunctionDeclInfo.body") == common_pb2.FIELD_STATE_UNREQUESTED
        cfg_shallow_wire = rows[0].to_dict()

    with client.match(
        'templateSpecializationType().bind("type")', file=source,
        compile_arguments=compile_arguments,
    ) as rows:
        non_aliases = [
            row.binding("type").value for row in rows
            if row.binding("type").value.WhichOneof("value") == "node"
            and row.binding("type").value.node.WhichOneof("payload") == "template_specialization_type"
            and not row.binding("type").value.node.template_specialization_type.has_alias
        ]
        assert non_aliases
        assert _field_state(non_aliases[0], "TemplateSpecializationType.aliased_type") == common_pb2.FIELD_STATE_INAPPLICABLE
        template_type_wire = rows[0].to_dict()

    enabled = client.cfg(
        "cfg_target", path=source, compile_arguments=compile_arguments,
        options=CfgOptions(add_implicit_dtors=True),
    )
    disabled = client.cfg(
        "cfg_target", path=source, compile_arguments=compile_arguments,
        options=CfgOptions(add_implicit_dtors=False),
    )
    enabled_dtors = [
        element for graph in enabled.graphs for block in graph.blocks
        for element in block.elements
        if element.kind == cfg_element_pb2.CfgElement.AUTOMATIC_OBJECT_DTOR
    ]
    disabled_dtors = [
        element for graph in disabled.graphs for block in graph.blocks
        for element in block.elements
        if element.kind == cfg_element_pb2.CfgElement.AUTOMATIC_OBJECT_DTOR
    ]
    assert any(element.destructor.variable.name == "item" for element in enabled_dtors)
    assert not disabled_dtors
    cfg_wire = (
        enabled.SerializeToString(deterministic=True),
        disabled.SerializeToString(deterministic=True),
    )
    return (docs_wire, specialization_wire, template_wire, tiny_traversal_wire,
            body_availability,
            alias_wire, base_wire, cfg_shallow_wire, template_type_wire, cfg_wire)


async def _check_match_facts_async(client: AsyncClient, source: Path):
    """Async mirror: await each API call and return detached protobuf evidence."""
    compile_arguments = ("-std=c++20",)

    documented = await client.match_in(
        'functionDecl(hasName("documented")).bind("decl")', source,
        compile_arguments=compile_arguments,
    )
    try:
        assert len(documented) == 1
        documented_binding = documented[0].binding("decl").value
        assert "Raw docs retained on this declaration." in documented_binding.documentation
        function = documented_binding.node.function_decl.function
        assert function.HasField("is_this_declaration_a_definition")
        assert not function.is_this_declaration_a_definition
        assert _field_state(documented_binding, "FunctionDeclInfo.body") == common_pb2.FIELD_STATE_SEMANTICALLY_ABSENT
        assert _field_state(documented_binding, "is_this_declaration_a_definition") == common_pb2.FIELD_STATE_PRESENT
        docs_wire = documented[0].to_dict()
    finally:
        await documented.aclose()

    rows = await client.match_in(
        'classTemplateSpecializationDecl(hasName("Box")).bind("spec")', source,
        compile_arguments=compile_arguments,
    )
    try:
        assert len(rows) >= 1
        specialization = rows[0].binding("spec").value.node.class_template_specialization_decl
        assert specialization.specialized_template.name == "Box"
        assert specialization.HasField("specialization_kind")
        specialization_wire = rows[0].to_dict()
    finally:
        await rows.aclose()

    traversal = await client.traverse(
        source, compile_arguments=compile_arguments,
        visit_template_instantiations=True, projection="recursive",
    )
    cfg_binding = _function_binding(traversal.nodes, "body_target")
    cfg_function = cfg_binding.node.function_decl.function
    assert cfg_function.HasField("body")
    assert cfg_function.body.HasField("is_complete")
    assert not cfg_function.body.is_complete
    assert _field_state(cfg_binding, "FunctionDeclInfo.body") == common_pb2.FIELD_STATE_PRESENT
    body_availability = tuple(
        (entry.field_path, entry.state) for entry in cfg_binding.availability
    )
    traversal_wire = traversal.SerializeToString(deterministic=True)

    tiny_traversal = await client.traverse(
        source, compile_arguments=compile_arguments,
        visit_template_instantiations=True, projection="recursive", payload_nodes=2,
    )
    tiny_cfg_binding = _function_binding(tiny_traversal.nodes, "body_target")
    assert tiny_cfg_binding.HasField("is_complete")
    assert not tiny_cfg_binding.is_complete
    assert any(
        entry.state == common_pb2.FIELD_STATE_TRUNCATED
        and entry.field_path == "CompoundStmt"
        for entry in tiny_cfg_binding.availability
    )
    tiny_traversal_wire = tiny_traversal.SerializeToString(deterministic=True)

    specializations = []
    for item in traversal.nodes:
        binding = item.value
        if binding.WhichOneof("value") == "node" and binding.node.WhichOneof("payload") == "class_template_specialization_decl":
            specialization = binding.node.class_template_specialization_decl
            if specialization.specialized_template.name == "Box":
                specializations.append(specialization)
    assert any(len(spec.template_arguments) >= 2 for spec in specializations)
    template_wire = traversal_wire

    rows = await client.match_in(
        'typeAliasDecl(hasName("CountRef")).bind("alias")', source,
        compile_arguments=compile_arguments,
    )
    try:
        assert len(rows) == 1
        underlying = rows[0].binding("alias").value.node.type_alias_decl.underlying_type
        assert underlying.description.spelling == "Count &"
        assert underlying.description.canonical_spelling == "const int &"
        alias_wire = rows[0].to_dict()
    finally:
        await rows.aclose()

    base_matcher = Matcher(
        "cxxRecordDecl",
        Matcher("hasName", "Derived"),
        Matcher("hasAnyBase", Matcher("cxxBaseSpecifier").bind("base")),
    ).bind("record")
    rows = await client.match_in(base_matcher, source, compile_arguments=compile_arguments)
    try:
        assert len(rows) == 1
        base = rows[0].binding("base").value
        assert base.WhichOneof("value") == "base_specifier"
        assert base.base_specifier.type.description.spelling == "Base"
        assert base.base_specifier.access == common_pb2.ACCESS_SPECIFIER_PUBLIC
        assert not base.base_specifier.is_virtual
        assert not base.base_specifier.is_pack_expansion
        assert not base.supported_scopes
        assert base.location.valid
        assert base.location.file == str(source.resolve())
        assert base.range.expansion_begin.valid
        assert base.range.expansion_begin.file == str(source.resolve())
        assert base.range.spelling_begin.valid
        assert base.range.spelling_begin.file == str(source.resolve())
        base_wire = rows[0].to_dict()
    finally:
        await rows.aclose()

    rows = await client.match_in(
        'functionDecl(hasName("cfg_target")).bind("decl")', source,
        compile_arguments=compile_arguments,
    )
    try:
        assert len(rows) == 1
        declaration = rows[0].binding("decl").value
        assert not declaration.node.function_decl.function.HasField("body")
        assert _field_state(declaration, "FunctionDeclInfo.body") == common_pb2.FIELD_STATE_UNREQUESTED
        cfg_shallow_wire = rows[0].to_dict()
    finally:
        await rows.aclose()

    rows = await client.match_in(
        'templateSpecializationType().bind("type")', source,
        compile_arguments=compile_arguments,
    )
    try:
        non_aliases = [
            row.binding("type").value for row in rows
            if row.binding("type").value.WhichOneof("value") == "node"
            and row.binding("type").value.node.WhichOneof("payload") == "template_specialization_type"
            and not row.binding("type").value.node.template_specialization_type.has_alias
        ]
        assert non_aliases
        assert _field_state(non_aliases[0], "TemplateSpecializationType.aliased_type") == common_pb2.FIELD_STATE_INAPPLICABLE
        template_type_wire = rows[0].to_dict()
    finally:
        await rows.aclose()

    enabled = await client.cfg(
        source, "cfg_target", compile_arguments=compile_arguments,
        options=CfgOptions(add_implicit_dtors=True),
    )
    disabled = await client.cfg(
        source, "cfg_target", compile_arguments=compile_arguments,
        options=CfgOptions(add_implicit_dtors=False),
    )
    enabled_dtors = [
        element for graph in enabled.graphs for block in graph.blocks
        for element in block.elements
        if element.kind == cfg_element_pb2.CfgElement.AUTOMATIC_OBJECT_DTOR
    ]
    disabled_dtors = [
        element for graph in disabled.graphs for block in graph.blocks
        for element in block.elements
        if element.kind == cfg_element_pb2.CfgElement.AUTOMATIC_OBJECT_DTOR
    ]
    assert any(element.destructor.variable.name == "item" for element in enabled_dtors)
    assert not disabled_dtors
    cfg_wire = (
        enabled.SerializeToString(deterministic=True),
        disabled.SerializeToString(deterministic=True),
    )
    return (docs_wire, specialization_wire, template_wire, tiny_traversal_wire,
            body_availability,
            alias_wire, base_wire, cfg_shallow_wire, template_type_wire, cfg_wire)


@when("I query the reasoning facts through both SDK clients", target_fixture="sdk_reasoning_results")
def query_reasoning_facts(sdk_reasoning):
    server, source = sdk_reasoning
    with Client(server.endpoint) as client:
        sync = _check_match_facts(client, source)

    async def run_async():
        async with AsyncClient(server.endpoint) as client:
            return await _check_match_facts_async(client, source)

    return sync, asyncio.run(run_async())


@then("both SDK clients return the same positive semantic facts")
def verify_sync_async_equivalence(sdk_reasoning_results) -> None:
    sync, asynchronous = sdk_reasoning_results
    assert sync == asynchronous
