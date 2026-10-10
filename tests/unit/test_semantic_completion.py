from prompt_toolkit.document import Document
from prompt_toolkit.formatted_text import to_plain_text

from clang_toolkit.cli.completion import ReplCompleter


def test_field_resolver_receives_complete_nested_indexed_reference():
    received: list[str] = []

    def resolve(reference: str) -> tuple[str, ...]:
        received.append(reference)
        if reference.endswith(".node"):
            return ("function_decl", "hasField")
        if reference.endswith(".function_decl"):
            return ("function",)
        if reference.endswith(".function"):
            return ("declarator",)
        if reference.endswith(".declarator"):
            return ("value",)
        if reference.endswith(".value"):
            return ("named",)
        if reference.endswith(".named"):
            return ("qualified_name",)
        return ()

    completer = ReplCompleter(
        references={"functions": ()}, field_resolver=resolve
    )

    def complete(source: str) -> list[str]:
        return [
            item.text
            for item in completer.get_completions(Document(source), None)
        ]

    prefix = "$functions[0].f.value.node."
    assert "function_decl" in complete(prefix)
    assert "hasField(" in complete(prefix)
    assert received[-1] == "$functions[0].f.value.node"
    assert "function" in complete(prefix + "function_decl.")
    assert received[-1] == "$functions[0].f.value.node.function_decl"
    assert "declarator" in complete(prefix + "function_decl.function.")
    assert "value" in complete(
        prefix + "function_decl.function.declarator."
    )
    assert "named" in complete(
        prefix + "function_decl.function.declarator.value."
    )
    assert "qualified_name" in complete(
        prefix + "function_decl.function.declarator.value.named."
    )


def test_field_resolver_only_runs_for_a_field_access_and_accepts_partial_names():
    received: list[str] = []

    def resolve(reference: str) -> tuple[str, ...]:
        received.append(reference)
        return ("qualified_name", "hasField")

    completer = ReplCompleter(field_resolver=resolve)

    def complete(source: str) -> list[str]:
        return [
            item.text
            for item in completer.get_completions(Document(source), None)
        ]

    assert complete("$") == []
    assert received == []
    assert complete("$functions[0].f.value.node.qualified") == ["qualified_name"]
    assert received[-1] == "$functions[0].f.value.node"


def test_has_field_completes_schema_names_as_only_quoted_arguments(tmp_path):
    received: list[str] = []
    (tmp_path / "unit.cpp").write_text("int main() {}")

    def resolve(reference: str) -> tuple[str, ...]:
        received.append(reference)
        return ("cxx_method_decl", "name", "return_type")

    completer = ReplCompleter(presence_resolver=resolve, cwd=tmp_path)

    def options(source: str, cursor: int | None = None):
        return {
            item.text: item
            for item in completer.get_completions(
                Document(source, cursor_position=cursor), None
            )
        }

    def completed(source: str, item, cursor: int | None = None):
        cursor = len(source) if cursor is None else cursor
        start = cursor + item.start_position
        return source[:start] + item.text + source[cursor:]

    prefix = "$functions[0].f.value.node.hasField("
    unquoted = options(prefix)
    assert set(unquoted) == {
        '"cxx_method_decl"',
        '"name"',
        '"return_type"',
    }
    assert completed(prefix, unquoted['"cxx_method_decl"']) == (
        prefix + '"cxx_method_decl"'
    )
    assert set(received) == {"$functions[0].f.value.node"}
    assert all("field presence" in to_plain_text(item.display_meta) for item in unquoted.values())

    empty_double_quote = options(prefix + '"')
    assert set(empty_double_quote) == {
        'cxx_method_decl"',
        'name"',
        'return_type"',
    }
    assert empty_double_quote['cxx_method_decl"'].start_position == 0
    assert completed(prefix + '"', empty_double_quote['cxx_method_decl"']) == (
        prefix + '"cxx_method_decl"'
    )

    empty_single_quote = options(prefix + "'")
    assert set(empty_single_quote) == {
        "cxx_method_decl'",
        "name'",
        "return_type'",
    }
    assert empty_single_quote["cxx_method_decl'"].start_position == 0
    assert completed(prefix + "'", empty_single_quote["cxx_method_decl'"]) == (
        prefix + "'cxx_method_decl'"
    )

    partial = options(prefix + '"cxx')
    assert list(partial) == ['cxx_method_decl"']
    assert partial['cxx_method_decl"'].start_position == -3
    assert completed(prefix + '"cxx', partial['cxx_method_decl"']) == (
        prefix + '"cxx_method_decl"'
    )

    single_quote = options(prefix + "'na")
    assert list(single_quote) == ["name'"]
    assert single_quote["name'"].start_position == -2

    for quote in ('"', "'"):
        empty_source = prefix + quote + quote
        empty_cursor = len(prefix) + 1
        empty_at_quote = options(empty_source, empty_cursor)
        item = empty_at_quote["name"]
        assert completed(empty_source, item, empty_cursor) == (
            prefix + quote + "name" + quote
        )

        partial_source = prefix + quote + "na" + quote
        partial_cursor = len(prefix) + 3
        partial_at_quote = options(partial_source, partial_cursor)
        item = partial_at_quote["name"]
        assert completed(partial_source, item, partial_cursor) == (
            prefix + quote + "name" + quote
        )

    printable = 'print $node.hasField("na'
    printable_cursor = len(printable)
    printable_options = options(printable, printable_cursor)
    assert list(printable_options) == ['name"']
    assert completed(
        printable, printable_options['name"'], printable_cursor
    ) == 'print $node.hasField("name"'


def test_legacy_mapping_completion_still_suggests_methods():
    completer = ReplCompleter(references={"rows": ("length", "joinWith")})
    suggestions = [
        item.text
        for item in completer.get_completions(Document("$rows."), None)
    ]
    assert suggestions == ["joinWith(", "length"]


def test_runtime_metadata_guides_active_node_and_nested_schema_fields(tmp_path):
    from unittest.mock import Mock

    from clang_toolkit._generated.ast.v1 import node_pb2
    from clang_toolkit._generated.match.v1 import match_result_pb2
    from clang_toolkit._row_store import RowStore
    from clang_toolkit.cli.runtime import Runtime
    from clang_toolkit.client import Client
    from clang_toolkit.match_values import MatchValue

    client = Mock(spec=Client)
    runtime = Runtime(client, cwd=tmp_path, environment={})
    ast_node = node_pb2.AstNode()
    method = ast_node.cxx_method_decl.method
    method.function.declarator.value.named.name.identifier = "run"
    method.function.declarator.value.named.qualified_name = "Widget::run"
    method.parent_record.type.spelling = "Widget"
    method.function.return_type.type.builtin_type.info.spelling = "int"

    row = match_result_pb2.MatchResult()
    row.bindings["f"].node.CopyFrom(ast_node)
    store = RowStore()
    store.append(row.SerializeToString(), binding_names=row.bindings)
    runtime.bindings["m"] = MatchValue._from_store(store, None)
    completer = ReplCompleter(
        references=runtime.completion_references,
        field_resolver=runtime.completion_suggestions,
        presence_resolver=runtime.completion_presence_fields,
    )

    def options(source: str):
        return {
            item.text: item
            for item in completer.get_completions(Document(source), None)
        }

    try:
        direct_binding_fields = options("$m[0].f.")
        assert {"node", "is_complete", "keys", "value", "name"} <= set(direct_binding_fields)
        assert "hasField(" in direct_binding_fields
        assert "method" in to_plain_text(direct_binding_fields["hasField("].display_meta)
        assert "field" in to_plain_text(direct_binding_fields["is_complete"].display_meta)
        assert client.mock_calls == []

        node_fields = options("$m[0].f.value.node.")
        assert {
            "cxx_method_decl",
            "hasField(",
            "name",
            "qualified_name",
            "return_type",
            "parameters",
            "body",
        } <= set(node_fields)
        assert "spelling" not in node_fields
        payload_meta = to_plain_text(node_fields["cxx_method_decl"].display_meta)
        assert "active payload" in payload_meta
        assert "continue with ." in payload_meta
        method_meta = to_plain_text(node_fields["hasField("].display_meta)
        assert "method" in method_meta
        assert "presence" in method_meta
        assert client.mock_calls == []

        presence_reference = "$m[0].f.value.node"
        presence_fields = options(presence_reference + ".hasField(")
        completed_presence_fields = {
            text[1:-1] for text in presence_fields
        }
        assert completed_presence_fields == set(
            runtime.completion_presence_fields(presence_reference)
        )
        assert "function_decl" in completed_presence_fields
        assert "cxx_method_decl" in completed_presence_fields
        assert "parameters" not in completed_presence_fields
        assert all(
            "field presence" in to_plain_text(item.display_meta)
            for item in presence_fields.values()
        )
        assert client.mock_calls == []

        named_fields = options(
            "$m[0].f.value.node.cxx_method_decl.method.function."
            "declarator.value.named."
        )
        assert "qualified_name" in named_fields
        assert "field" in to_plain_text(named_fields["qualified_name"].display_meta)
        assert "name" in options(
            "$m[0].f.value.node.cxx_method_decl.method.function."
            "declarator.value.named."
        )
        assert runtime.evaluate(
            "$m[0].f.value.node.cxx_method_decl.method.function."
            "declarator.value.named.qualified_name"
        ) == "Widget::run"

        name_fields = options(
            "$m[0].f.value.node.cxx_method_decl.method.function."
            "declarator.value.named.name."
        )
        assert set(name_fields) == {"identifier", "keys", "hasField(", "fieldState(", "fieldOr("}
        identifier_meta = to_plain_text(name_fields["identifier"].display_meta)
        assert identifier_meta == "active field"
        assert "continue with ." not in identifier_meta
        assert runtime.evaluate(
            "$m[0].f.value.node.cxx_method_decl.method.function."
            "declarator.value.named.name.identifier"
        ) == "run"

        type_fields = options(
            "$m[0].f.value.node.cxx_method_decl.method.parent_record.type."
        )
        assert "spelling" in type_fields
        assert "field" in to_plain_text(type_fields["spelling"].display_meta)
        assert runtime.evaluate(
            "$m[0].f.value.node.cxx_method_decl.method.parent_record.type.spelling"
        ) == "Widget"
        assert client.mock_calls == []
    finally:
        store.close()
        runtime.close()
