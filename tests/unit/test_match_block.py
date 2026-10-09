"""Statement blocks execute while match rows are still streaming."""

from __future__ import annotations

import asyncio

import pytest
from lark.exceptions import UnexpectedInput

from clang_toolkit import AsyncClient, Client
from clang_toolkit._generated.match.v1 import match_result_pb2, match_stream_pb2
from clang_toolkit.cli.language import batch_parser, lex, parser
from clang_toolkit.cli.runtime import Runtime
from clang_toolkit.cli.runtime.evaluator import EvaluationError

from test_match_stream import Stream, completed, patch_stream


def function_row(index=0, names=("func",)):
    row = match_result_pb2.MatchResult()
    for name in names:
        row.bindings[name].node.function_decl.function.declarator.value.named.qualified_name = f"function_{index}"
    return match_stream_pb2.MatchStreamEvent(row=row)


@pytest.mark.parametrize("separator", [";", "\n"])
def test_match_statement_block_parses_comments_and_ordinary_statements(separator):
    source = 'match functionDecl().bind("func") in $file do { ' + separator.join([
        'let name = $func.value.node.qualified_name', 'print $name',
        'match varDecl() in "other.cpp" do { print $root.value.node.clang_kind; }',
    ]) + ' }'
    for language in (parser(), batch_parser()):
        node = language.parse(source).children[0]
        assert node.data == "match"
        assert node.children[-1].data == "statement_block"
    with_comment = source.replace("{ ", "{ # row bindings\n", 1)
    assert parser().parse(with_comment)
    assert batch_parser().parse(with_comment)
    assert "".join(map(str, lex(with_comment))) == with_comment


def test_match_blocks_keep_newline_statement_boundaries_and_multiline_expressions():
    source = '''match functionDecl(
        isDefinition()
    ).bind("func") in "file.cpp" do {
        help match
        let names = [
            $func.value.node.qualified_name,
            "other"
        ]
        print $names[0]
    }'''
    for language in (parser(), batch_parser()):
        node = language.parse(source).children[0]
        statements = [child.data for child in node.children[-1].children
                      if hasattr(child, "data")]
        assert statements == ["help", "assignment", "print"]


@pytest.mark.parametrize("source", [
    'match functionDecl() in "file.cpp" do print "bad"',
    'match functionDecl() in "file.cpp" do { let name = }',
    'match functionDecl() in "file.cpp" do { print "bad"',
])
def test_match_block_rejects_invalid_statements_before_requests(source):
    for language in (parser(), batch_parser()):
        with pytest.raises(UnexpectedInput):
            language.parse(source)


def test_streamed_bindings_and_locals_are_row_scoped_before_completion(monkeypatch, tmp_path):
    output_file = tmp_path / "names.txt"
    stream = Stream(
        [function_row(0, ("func", "other")), function_row(1, ("func", "other")), completed("rows", 2)],
        before_terminal=lambda: assert_before_completion(),
    )

    def assert_before_completion():
        assert output_file.read_text() == "function_0\nfunction_1\n"

    patch_stream(monkeypatch, stream)
    with Client("unix:///tmp/test.sock") as client:
        runtime = Runtime(client, cwd=tmp_path)
        runtime.bindings["func"] = "outer"
        output = runtime.execute('''match functionDecl().bind("func") in "file.cpp" do {
            # The binding label is the local variable name.
            let name = $func.value.node.qualified_name
            print $name to "names.txt" mode append
            print $other.value.node.qualified_name
        }''')
        assert output == "function_0\nfunction_1"
        assert runtime.bindings == {"func": "outer"}
        assert runtime._scopes == []
        assert runtime._block_owners == []
        assert not client._values


def test_empty_stream_skips_block_and_failure_cancels_before_completion(monkeypatch, tmp_path):
    stream = Stream([completed("empty", 0)])
    patch_stream(monkeypatch, stream)
    with Client("unix:///tmp/test.sock") as client:
        runtime = Runtime(client, cwd=tmp_path)
        assert runtime.execute('match functionDecl() in "file.cpp" do { print $unknown; }') == ""

    stream = Stream([function_row(), function_row(1), completed("failed", 2)])
    patch_stream(monkeypatch, stream)
    with Client("unix:///tmp/test.sock") as client:
        runtime = Runtime(client, cwd=tmp_path)
        with pytest.raises(EvaluationError, match=r"match row 0:.*unknown variable.*line 1"):
            runtime.execute('match functionDecl() in "file.cpp" do { let local = 1; print $unknown; }')
        assert stream.cancelled
        assert stream.index == 1
        assert runtime.bindings == {}
        assert runtime._scopes == []
        assert runtime._block_owners == []
        assert not client._values


def test_implicit_root_binding_and_reserved_labels_are_available(monkeypatch, tmp_path):
    stream = Stream([function_row(names=("root", "env", "config")), completed("rows", 1)])
    patch_stream(monkeypatch, stream)
    with Client("unix:///tmp/test.sock") as client:
        runtime = Runtime(client, cwd=tmp_path)
        assert runtime.execute('''match functionDecl() in "file.cpp" do {
            print $root.value.node.qualified_name;
            print $env.value.node.qualified_name;
            print $config.value.node.qualified_name;
        }''') == "function_0\nfunction_0\nfunction_0"


def test_save_and_load_statements_keep_loaded_variables_local(monkeypatch, tmp_path):
    stream = Stream([function_row(), completed("rows", 1)])
    patch_stream(monkeypatch, stream)
    with Client("unix:///tmp/test.sock") as client:
        runtime = Runtime(client, cwd=tmp_path)
        runtime.bindings["loaded"] = "outer"
        output = runtime.execute('''match functionDecl() in "file.cpp" do {
            let name = $func.value.node.qualified_name;
            save $name to "name.json";
            load "name.json" into $loaded;
            print $loaded;
        }''')
        assert output == "function_0"
        assert runtime.bindings == {"loaded": "outer"}


def test_async_execute_streams_block_without_blocking_rpc_loop(monkeypatch, tmp_path):
    stream = Stream([function_row(), completed("async-rows", 1)])
    patch_stream(monkeypatch, stream)

    async def run():
        async with AsyncClient("unix:///tmp/test.sock") as client:
            output = await client.execute('''match functionDecl().bind("func") in "file.cpp" do {
                let name = $func.value.node.qualified_name;
                print $name;
            }''', working_directory=tmp_path)
            assert output == "function_0"
            assert not client._expression_runtime._scopes
            assert not client._values

    asyncio.run(run())


def test_provisional_binding_cannot_be_used_as_native_cursor(monkeypatch, tmp_path):
    stream = Stream([function_row(), completed("rows", 1)])
    patch_stream(monkeypatch, stream)
    with Client("unix:///tmp/test.sock") as client:
        runtime = Runtime(client, cwd=tmp_path)
        with pytest.raises(EvaluationError, match="native continuation requires a completed match result"):
            runtime.execute('match functionDecl() in "file.cpp" do { match parmVarDecl() in $func; }')
        assert stream.cancelled


def test_async_cancellation_waits_for_row_scope_cleanup(monkeypatch, tmp_path):
    from threading import Event

    stream = Stream([function_row(), completed("rows", 1)])
    patch_stream(monkeypatch, stream)
    entered, release = Event(), Event()
    dispatch = Runtime._execute_statement

    def statement(runtime, node, source):
        if node.data == "print":
            entered.set()
            assert release.wait(timeout=5)
        return dispatch(runtime, node, source)

    monkeypatch.setattr(Runtime, "_execute_statement", statement)

    async def run():
        async with AsyncClient("unix:///tmp/test.sock") as client:
            operation = asyncio.create_task(client.execute(
                'match functionDecl() in "file.cpp" do { print $func.value.node.qualified_name; }',
                working_directory=tmp_path,
            ))
            try:
                assert await asyncio.to_thread(entered.wait, 5)
                operation.cancel()
                await asyncio.sleep(0)
                assert not operation.done()
            finally:
                release.set()
            with pytest.raises(asyncio.CancelledError):
                await operation
            assert not client._expression_runtime._scopes
            assert not client._expression_runtime._block_owners
            assert not client._values
            assert client._value_operation_count == 0
            assert stream.cancelled

    asyncio.run(run())
