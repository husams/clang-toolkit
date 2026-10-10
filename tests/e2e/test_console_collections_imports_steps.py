"""Collection and import acceptance through the CLI and native query server."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

from tests.e2e.test_network_steps import _launch_server

pytestmark = pytest.mark.e2e
scenarios("console_collections_imports.feature")


@given("a private server and a collection library fixture", target_fixture="collection_fixture")
def collection_fixture(tmp_path: Path, request):
    server = _launch_server("unix", tmp_path, request)
    source = tmp_path / "collections.cc"
    source.write_text(
        'const char *message = "café/مرحبا";\n'
        "int first() { return 1; }\nint second() { return 2; }\n",
        encoding="utf-8",
    )
    scripts = tmp_path / "scripts"
    parts = scripts / "lib" / "parts"
    parts.mkdir(parents=True)
    (parts / "constants.ctk").write_text('let selected = "first"\n', encoding="utf-8")
    (scripts / "lib" / "matchers.ctk").write_text(
        'import "parts/constants.ctk"\n'
        'let named(name) = functionDecl(hasName($name)).bind("f")\n',
        encoding="utf-8",
    )
    return server, source, scripts, tmp_path


def _run(collection_fixture, *arguments: str):
    server, _, _, directory = collection_fixture
    result = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server", server.endpoint, *arguments],
        cwd=directory,
        env=dict(os.environ, XDG_STATE_HOME=str(directory / "collection-state")),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=45,
        check=False,
    )
    assert result.returncode == 0, result.stdout
    assert server.process.poll() is None
    return result.stdout.splitlines()


@when("I run the collection operations through the CLI", target_fixture="collection_output")
def run_collections(collection_fixture):
    return _run(collection_fixture, "-e", "\n".join([
        "let d1 = {}", "let d2 = {a: 1, b: 2}",
        "let a1 = []", "let a2 = [1, 2, 3]",
        "set d2['a'] = 7", "delete d2['b']", "push a2, 4",
        "let removed = pop a2", "delete a2[0]",
        'let pieces = split "ss/ddd/ddd" by "/"',
        'print join a2 with ","', "print d2['a']", "print removed",
        'print join pieces with "|"', 'print join d2.keys with ","',
        "print d1.isEmpty", "print a1.isEmpty",
    ]))


@then("the collection results preserve the requested values")
def verify_collections(collection_output):
    assert collection_output == ["2,3", "7", "4", "ss|ddd|ddd", "a", "true", "true"]


@when("I run a script importing nested matcher libraries", target_fixture="library_output")
def run_libraries(collection_fixture):
    _, source, scripts, _ = collection_fixture
    script = scripts / "main.ctk"
    script.write_text("\n".join([
        'import "lib/matchers.ctk"',
        f'let rows = match named($selected) in "{source}"',
        'let counts = {found: $rows.length}',
        "print $counts['found']", "print $rows[0].f.value.node.qualified_name",
    ]), encoding="utf-8")
    return _run(collection_fixture, "--script", str(script))


@then("the imported matcher and variables work against native results")
def verify_libraries(library_output):
    assert library_output == ["1", "first"]


@when("I print a native UTF-8 string literal through the CLI", target_fixture="utf8_output")
def run_utf8(collection_fixture):
    _, source, _, _ = collection_fixture
    return _run(collection_fixture, "-e", "\n".join([
        f'let texts = match stringLiteral().bind("s") in "{source}"',
        "print $texts[0].s.value.node.string_literal.value",
    ]))


@then("the console displays the decoded text")
def verify_utf8(utf8_output):
    assert utf8_output == ["café/مرحبا"]


@when("I read keys from the second retained root value", target_fixture="semantic_keys_output")
def run_semantic_keys(collection_fixture):
    _, source, _, _ = collection_fixture
    return _run(collection_fixture, "-e", "\n".join([
        f'let lst = match functionDecl(isDefinition()) in "{source}"',
        "let keys = $lst[1].root.keys",
        'print $keys.joinWith(",")',
        'print $lst[1].root.node.keys.joinWith(",")',
        "print $lst[1].root.qualified_name",
    ]))


@then("the keys list the readable semantic properties")
def verify_semantic_keys(semantic_keys_output):
    assert len(semantic_keys_output) == 3
    binding_keys = set(semantic_keys_output[0].split(","))
    assert {"function", "qualified_name", "decl_name"} <= binding_keys
    assert not {
        "node", "availability", "is_complete", "supported_scopes", "keys",
        "hasField", "fieldState", "fieldOr", "body", "parameters",
    } & binding_keys
    node_keys = set(semantic_keys_output[1].split(","))
    assert "qualified_name" in node_keys
    assert not {"body", "parameters", "hasField", "fieldState", "fieldOr"} & node_keys
    assert semantic_keys_output[2] == "second"


@when("I export a retained binding and its semantic fields", target_fixture="semantic_exports")
def run_semantic_exports(collection_fixture):
    _, source, _, directory = collection_fixture
    output = _run(collection_fixture, "-e", "\n".join([
        f'let lst = match functionDecl(isDefinition()) in "{source}"',
        'print $lst[0].root["is_complete"]',
        'print $lst[0].root.hasField("node")',
        'save $lst[0].root to "binding.yaml" as yaml',
        'save $lst[0].root.value to "binding-value.json" as json',
        'save $lst[0].root.node to "node.proto" as proto',
        'save $lst[0].root.node.qualified_name to "name.json" as json',
        'save $lst[0].root.is_complete to "complete.yaml" as yaml',
        'save $lst[0].root.availability to "availability.json" as json',
        'save $lst[0].bindings to "bindings.yaml" as yaml',
        'save $lst[0] to "row.json" as json',
        f'let texts = match stringLiteral().bind("s") in "{source}"',
        'save $texts[0].s.node.string_literal.value to "bytes.proto" as proto',
        'load "name.json" into $saved_name',
        'print $saved_name',
        'load "binding.yaml" into $saved_binding',
        'print $saved_binding.function_decl.function.declarator.value.named.qualified_name',
        'load "node.proto" into $saved_node',
        'print $saved_node.qualified_name',
        'print $saved_node.fieldState("body")',
        'let again = match integerLiteral() in $lst[0].root',
        'print $again.length',
    ]))
    return directory, source, output


@then("the snapshots preserve the selected data and native matching continues")
def verify_semantic_exports(semantic_exports):
    import json

    import yaml

    from clang_toolkit.cli.runtime.persistence import load
    from clang_toolkit.cli.runtime.semantic import property_value

    directory, _source, output = semantic_exports
    assert output == ["true", "true", "first", "first", "first", "UNREQUESTED", "1"]
    binding = load(directory / "binding.yaml")
    value = load(directory / "binding-value.json")
    assert binding == value
    assert "function_decl" in binding
    assert not {"availability", "is_complete", "supported_scopes", "node"} & binding.keys()
    assert "value" not in binding
    assert yaml.safe_load((directory / "binding.yaml").read_text()) == binding
    assert json.loads((directory / "binding-value.json").read_text()) == binding

    def implicit_values(data):
        if isinstance(data, dict):
            for key, item in data.items():
                if key == "is_implicit":
                    yield item
                yield from implicit_values(item)
        elif isinstance(data, list):
            for item in data:
                yield from implicit_values(item)

    implicit = list(implicit_values(binding))
    assert implicit and all(type(item) is bool for item in implicit)
    node = load(directory / "node.proto")
    assert property_value(node, "qualified_name") == "first"
    assert '"qualified_name": "first"' in (directory / "binding-value.json").read_text()
    assert load(directory / "name.json") == "first"
    assert load(directory / "complete.yaml") is True
    availability = load(directory / "availability.json")
    assert availability
    assert any(item["state"] == "FIELD_STATE_UNREQUESTED" for item in availability)
    bindings = load(directory / "bindings.yaml")
    assert set(bindings) == {"root"}
    assert bindings["root"] == value
    row = load(directory / "row.json")
    assert set(row) == {"bindings"}
    assert row["bindings"]["root"] == binding
    assert row["bindings"]["root"]["function_decl"]["function"]["declarator"]["value"]["named"]["qualified_name"] == "first"
    assert load(directory / "bytes.proto") == "café/مرحبا".encode("utf-8")


@when("I evaluate a class binding directly in the CLI", target_fixture="class_binding_output")
def run_class_binding(collection_fixture):
    _, _, _, directory = collection_fixture
    source = directory / "class_value.cc"
    source.write_text("class Widget { public: int item; };\n", encoding="utf-8")
    return _run(collection_fixture, "-e", "\n".join([
        f'let lst = match cxxRecordDecl(isDefinition(), hasName("Widget")).bind("class") in "{source}"',
        "let selected = $lst[0].class",
        "$lst[0].class",
        "print $lst[0].class",
        "print $lst[0].class.value",
        "print $lst[0].class.node.qualified_name",
        "let fields = match fieldDecl() in $lst[0].class",
        "print $fields.length",
        "session close $lst",
        "$selected",
    ]))


@then("the binding displays its semantic data and remains a native match root")
def verify_class_binding(class_binding_output):
    import json

    assert len(class_binding_output) == 6
    direct, printed, explicit, name, count, closed = class_binding_output
    assert direct == printed == explicit == closed
    assert name == "Widget"
    assert count == "1"
    data = json.loads(direct)
    assert data["is_complete"] is True
    assert "cxx_record_decl" in data["node"]
    assert "value" not in data
    assert "ctk.ast.v1." not in direct
    assert not direct.startswith("binding ")


@when("I save a class binding as JSON YAML and protobuf", target_fixture="ast_exports")
def run_ast_exports(collection_fixture):
    _, _, _, directory = collection_fixture
    source = directory / "class_export.cc"
    source.write_text(
        "struct Base {};\n/// Widget documentation\n"
        "class Widget : public Base { public: int item; };\n",
        encoding="utf-8",
    )
    output = _run(collection_fixture, "-e", "\n".join([
        f'let lst = match cxxRecordDecl(isDefinition(), hasName("Widget")).bind("class") in "{source}"',
        "let selected = $lst[0].class",
        'save $selected to "class.json" as json',
        'save $selected to "class.yaml" as yaml',
        'save $selected.value to "class-value.json" as json',
        'save $selected.node to "class-node.yaml" as yaml',
        'save $lst[0].bindings to "class-bindings.json" as json',
        'save $lst[0] to "class-row.yaml" as yaml',
        'save $lst to "class-rows.json" as json',
        'save $selected to "class.proto" as proto',
        'save $lst[0].root.keys to "class-keys.json" as json',
        'save $lst[0].root.record to "class-record.json" as json',
        'foreach key in $lst[0].root.keys do { let readable = $lst[0].root[$key]; }',
        'print $lst[0].root["decl_name"]',
        'print $lst[0].root.qualified_name',
        'print $lst[0].root.record.tag.type_declaration.named.qualified_name',
        'let own = {availability: [1], is_complete: true, node: "keep", source_file: "custom"}',
        'save $own to "own.json" as json',
        'load "class.proto" into $snapshot',
        'print $snapshot.value.node.qualified_name',
        'print $snapshot.value.is_complete',
        'print $snapshot.value.node.fieldState("definition_bases")',
        'let fields = match fieldDecl() in $selected',
        'print $fields.length',
    ]))
    return directory, output


@then("the text exports contain AST properties and protobuf retains availability")
def verify_ast_exports(ast_exports):
    import json

    import yaml

    directory, output = ast_exports
    assert output == ["Widget", "Widget", "Widget", "Widget", "true", "UNREQUESTED", "1"]
    data = json.loads((directory / "class.json").read_text())
    assert "cxx_record_decl" in data
    keys = set(json.loads((directory / "class-keys.json").read_text()))
    assert {"cxx_record_decl", "record", "qualified_name", "decl_name", "is_implicit"} <= keys
    assert not {
        "node", "availability", "is_complete", "supported_scopes", "members", "definition_bases",
    } & keys
    assert json.loads((directory / "class-record.json").read_text()) == data["cxx_record_decl"]["record"]
    assert data["location"]["valid"] is True
    assert data["location"]["file"].endswith("class_export.cc")
    assert data["symbol_identity"]
    assert "Widget documentation" in data["documentation"]
    assert yaml.safe_load((directory / "class.yaml").read_text()) == data
    assert json.loads((directory / "class-value.json").read_text()) == data
    assert yaml.safe_load((directory / "class-node.yaml").read_text()) == {
        "cxx_record_decl": data["cxx_record_decl"],
    }
    bindings = json.loads((directory / "class-bindings.json").read_text())
    assert set(bindings) == {"class", "root"}
    assert bindings["class"] == bindings["root"] == data
    row = yaml.safe_load((directory / "class-row.yaml").read_text())
    assert row == {"bindings": bindings}
    assert json.loads((directory / "class-rows.json").read_text()) == [row]

    def verify_properties(value):
        if isinstance(value, dict):
            assert not {
                "availability", "is_complete", "supported_scopes", "source_file",
                "source_match_index", "session_id", "cursor_id", "result_revision",
            } & value.keys()
            for item in value.values():
                verify_properties(item)
        elif isinstance(value, list):
            for item in value:
                verify_properties(item)

    verify_properties(row)
    assert '"qualified_name": "Widget"' in (directory / "class.json").read_text()
    assert json.loads((directory / "own.json").read_text()) == {
        "availability": [1], "is_complete": True, "node": "keep", "source_file": "custom",
    }


@when("I run multiline foreach blocks over retained matches", target_fixture="foreach_output")
def run_foreach_blocks(collection_fixture):
    _, source, _, _ = collection_fixture
    return _run(collection_fixture, "-e", "\n".join([
        f'let lst = match functionDecl(isDefinition()) in "{source}"',
        'let m = "outside"',
        "foreach m in $lst do {",
        "  let name = $m.root.decl_name",
        "  print $name",
        "}",
        "foreach m in $lst do",
        "# The brace may follow a comment and a newline.",
        "{",
        "  foreach part in [1, 2] do {",
        '    print "${m.root.decl_name}:${part}"',
        "  }",
        "}",
        "foreach m in $lst do {}",
        "let empty_maps = foreach m in $lst do {} done",
        'print $empty_maps[0].length',
        "print $m",
        "let names = foreach m in $lst do",
        "  $m.root.decl_name",
        "done",
        'print $names.joinWith(",")',
    ]))


@then("foreach prints each name once and restores the outer iterator")
def verify_foreach_blocks(foreach_output):
    assert foreach_output == [
        "first", "second", "first:1", "first:2", "second:1", "second:2",
        "0", "outside", "first,second",
    ]


@when(
    "I enter a foreach statement block with individual Enter presses",
    target_fixture="foreach_prompt_output",
)
def enter_foreach_block(collection_fixture):
    import asyncio

    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput

    from clang_toolkit.cli.app import dispatch
    from clang_toolkit.cli.prompt import PersistentPromptHistory, create_session
    from clang_toolkit.cli.runtime import Runtime
    from clang_toolkit.cli.runtime.history import HistoryStore
    from clang_toolkit.client import Client
    from tests.e2e.test_console_history_steps import _wait_for_text

    server, source, _, directory = collection_fixture
    command = 'foreach m in $lst do {\nprint "${m.root.decl_name}"\n}'
    store = HistoryStore(directory / "foreach-history.jsonl")

    async def submit():
        with create_pipe_input() as pipe:
            session = create_session(
                input=pipe, output=DummyOutput(), history=PersistentPromptHistory(store),
            )
            task = asyncio.create_task(session.prompt_async("ctk> "))
            try:
                expected = ""
                for index, part in enumerate(command.split("\n")):
                    if index:
                        pipe.send_text("\r")
                        expected += "\n"
                        await _wait_for_text(session, expected)
                        assert not task.done()
                    pipe.send_text(part)
                    expected += part
                    await _wait_for_text(session, expected)
                pipe.send_text("\r")
                return await asyncio.wait_for(task, 3)
            finally:
                if not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)

    with Client(server.endpoint) as client:
        runtime = Runtime(client, cwd=directory, environment={}, history=store)
        try:
            assert dispatch(client, f'let lst = match functionDecl(isDefinition()) in "{source}"', runtime) == ""
            assert dispatch(client, 'let m = "outside"', runtime) == ""
            submitted = asyncio.run(submit())
            assert submitted == command
            output = dispatch(client, submitted, runtime)
            outer = dispatch(client, "print $m", runtime)
            assert not runtime._scopes
            assert server.process.poll() is None
            return output, outer
        finally:
            runtime.close()


@then("the closing brace submits the complete native iteration")
def verify_foreach_prompt(foreach_prompt_output):
    assert foreach_prompt_output == ("first\nsecond", "outside")
