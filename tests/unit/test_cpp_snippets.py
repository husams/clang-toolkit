"""Snippet requests preserve raw C++ source and reusable native tree ownership."""

from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace

import pytest

from clang_toolkit import AsyncClient, Client, ParsedTree
from clang_toolkit._generated.match.v1 import parse_response_pb2
from clang_toolkit.cli.input_state import input_state
from clang_toolkit.cli.language import parser
from clang_toolkit.cli.runtime import EvaluationError, Runtime
from clang_toolkit.cli.runtime.cpp_snippet import source_text


def test_async_snippet_request_carries_borrowed_file_overrides_and_scope(monkeypatch, tmp_path):
    client = AsyncClient(compilation_database="/project/compile_commands.json")
    captured = {}

    class Stub:
        def __init__(self, channel):
            pass

        async def Parse(self, request, *, timeout=None):
            captured["request"] = request
            return parse_response_pb2.ParseResponse(
                session_id="snippet-1", result_revision=1,
                source_file="/tmp/ctk-snippet/source.cpp",
            )

    monkeypatch.setattr(client, "_ensure_stub", lambda: None)
    monkeypatch.setattr("clang_toolkit.client.match_service_pb2_grpc.MatchServiceStub", Stub)
    client._channel = object()
    client.config = SimpleNamespace(rpc_timeout=5)
    body = 'const char *s = "${raw}\\n";'
    response = asyncio.run(client._parse_cpp_response(
        body, file=Path("src/example.cpp"), working_directory=tmp_path,
        compile_arguments=["-DMODE=1"], includes=["template.hpp", "test.hpp"],
        translation_unit=True, scope="scope-1",
    ))
    request = captured["request"]
    assert request.HasField("cpp_snippet")
    assert request.cpp_snippet.code == body
    assert request.cpp_snippet.settings_file == "src/example.cpp"
    assert request.cpp_snippet.includes == ["template.hpp", "test.hpp"]
    assert request.cpp_snippet.translation_unit
    assert request.compilation_database == "/project/compile_commands.json"
    assert request.compile_arguments == ["-DMODE=1"]
    assert request.working_directory == str(tmp_path)
    assert request.resource_scope_id == "scope-1"
    assert request.file_path == ""
    assert response.source_file == "/tmp/ctk-snippet/source.cpp"


def test_snippet_defaults_omit_borrowed_file_and_headers(monkeypatch):
    client = AsyncClient()
    captured = {}

    async def call(method, request):
        captured["method"] = method
        captured["request"] = request
        return parse_response_pb2.ParseResponse()

    monkeypatch.setattr(client, "_resource_call", call)
    asyncio.run(client._parse_cpp_response("int value = 42;"))
    assert captured["method"] == "Parse"
    request = captured["request"]
    assert request.HasField("cpp_snippet")
    assert request.cpp_snippet.code == "int value = 42;"
    assert request.cpp_snippet.settings_file == ""
    assert request.cpp_snippet.includes == []
    assert not request.cpp_snippet.translation_unit


def test_sync_snippet_tree_uses_server_source_path_and_retains_owner(monkeypatch):
    client = Client()
    calls = []

    def call(method, *args, **kwargs):
        calls.append((method, args, kwargs))
        return parse_response_pb2.ParseResponse(
            session_id="snippet-1", result_revision=3,
            source_file="/tmp/server-snippet/source.cpp",
        )

    monkeypatch.setattr(client, "_cursor_call", call)
    tree = client.parse_cpp("int x = 1;", file="src/main.cpp")
    assert isinstance(tree, ParsedTree)
    assert tree.path == "/tmp/server-snippet/source.cpp"
    assert tree.source_file == tree.path
    assert tree._owner.session_id == "snippet-1"
    assert calls[0][0] == "_parse_cpp_response"
    assert calls[0][1] == ("int x = 1;",)
    assert calls[0][2]["file"] == "src/main.cpp"
    tree.close()
    client.close()


def test_async_snippet_parse_cleans_operation_count_on_failure(monkeypatch):
    client = AsyncClient()

    async def failure(*args, **kwargs):
        raise ValueError("invalid snippet")

    monkeypatch.setattr(client, "_parse_cpp_response", failure)
    with pytest.raises(ValueError, match="invalid snippet"):
        asyncio.run(client.parse_cpp("broken C++"))
    assert client._value_operation_count == 0


def test_async_snippet_tree_uses_temporary_source_and_releases_cursor(monkeypatch):
    client = AsyncClient()
    closed = []

    async def response(*args, **kwargs):
        return parse_response_pb2.ParseResponse(
            session_id="async-snippet", result_revision=2,
            source_file="/tmp/server-async-snippet/source.cpp",
        )

    async def close_match(identifier):
        closed.append(identifier)

    monkeypatch.setattr(client, "_parse_cpp_response", response)
    monkeypatch.setattr(client, "close_match", close_match)

    async def run():
        tree = await client.parse_cpp("int n=1;", file="src/sample.cpp")
        assert tree.path == tree.source_file == "/tmp/server-async-snippet/source.cpp"
        assert tree._owner.revision == 2
        await tree.aclose()

    asyncio.run(run())
    assert client._value_operation_count == 0
    assert closed == ["async-snippet"]


def test_raw_cpp_delimiter_preserves_cpp_escapes_and_ignores_host_strings():
    literal = 'cpp`const char *s = "${raw}\\n \\`"; // } ] )\n`'
    expected = 'const char *s = "${raw}\\n `"; // } ] )\n'
    assert source_text(literal) == expected
    statement = parser().parse("let tree = parse " + literal).children[0]
    assert statement.children[-1].data == "parse_cpp_expression"
    assert not input_state("let tree = parse " + literal).needs_more
    assert input_state("let tree = parse cpp`\\").needs_more


def test_legacy_console_accepts_multiline_options_and_passes_scope(monkeypatch, tmp_path):
    client = Client()
    calls = []
    sentinel = object()

    def parse_cpp(code, **options):
        calls.append((code, options))
        return sentinel

    monkeypatch.setattr(client, "parse_cpp", parse_cpp)
    runtime = Runtime(client, cwd=tmp_path)
    runtime._active_resource_scope = "scope-1"
    try:
        runtime.execute('''let tree = parse cpp`int x=0;` using {
            file: "src/sample.cpp",
            includes: ["sample.hpp"],
            translation_unit: false
        }''')
        assert runtime.bindings["tree"] is sentinel
        assert calls == [("int x=0;", {
            "working_directory": tmp_path, "compile_arguments": [],
            "file": "src/sample.cpp", "includes": ["sample.hpp"],
            "translation_unit": False, "scope": "scope-1",
        })]
    finally:
        runtime._active_resource_scope = None
        runtime.close()
        client.close()


def test_console_appends_explicit_flags_after_configured_overrides(monkeypatch, tmp_path):
    client = Client()
    calls = []

    def parse_cpp(code, **options):
        calls.append(options)
        return object()

    monkeypatch.setattr(client, "parse_cpp", parse_cpp)
    runtime = Runtime(client, cwd=tmp_path)
    runtime.config_store.set("extra_args", ["-DCONFIGURED=1"])
    try:
        runtime.execute('let tree = parse cpp`int x=0;` using {compile_arguments: ["-DCONFIGURED=2"]}')
        assert calls[0]["compile_arguments"] == ["-DCONFIGURED=1", "-DCONFIGURED=2"]
        assert runtime.config_store.effective["extra_args"] == ["-DCONFIGURED=1"]
    finally:
        runtime.close()
        client.close()


@pytest.mark.parametrize("using,error", [
    ('{unknown: true}', "unknown parse cpp option"),
    ('{includes: "header.hpp"}', "includes must be a list"),
    ('{compile_arguments: [1]}', "compile_arguments must be a list"),
    ('{translation_unit: "yes"}', "translation_unit must be a boolean"),
    ('{file: true}', "file must be a string"),
])
def test_console_rejects_invalid_snippet_options_before_rpc(tmp_path, using, error):
    client = Client()
    runtime = Runtime(client, cwd=tmp_path)
    try:
        with pytest.raises(EvaluationError, match=error):
            runtime.execute(f"let tree = parse cpp`int x=0;` using {using}")
    finally:
        runtime.close()
        client.close()
