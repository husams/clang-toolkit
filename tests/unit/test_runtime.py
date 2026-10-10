"""Runtime behavior, including the matcher composition requested for the REPL."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import Mock

from clang_toolkit.cli.app import dispatch, dispatch_result
from clang_toolkit.cli.batch import execute_batch
from clang_toolkit.cli.runtime import Directory, File, MatchSet, MatcherExpr, Runtime
from clang_toolkit.client import Client
from clang_toolkit._row_store import RowStore
from clang_toolkit._value_lifecycle import CursorOwner
from clang_toolkit.match_values import MatchValue
from clang_toolkit._generated.match.v1 import match_service_pb2


def runtime(tmp_path, *, environment=None, config_vars=None):
    client = Mock(spec=Client)
    client.match.return_value = ["matched"]
    return client, Runtime(
        client,
        cwd=tmp_path,
        environment=environment or {},
        config_vars=config_vars or {},
    )


def test_matcher_composition_is_typed_and_assignment_is_quiet(tmp_path):
    client, session = runtime(tmp_path)
    assert dispatch(client, "let m = hasType(pointerType())", session) == ""
    assert dispatch(client, "let f = varDecl($m)", session) == ""
    assert isinstance(session.bindings["m"], MatcherExpr)
    assert dispatch(client, "let r = match $f", session) == ""
    client.match.assert_called_once_with(
        "varDecl(hasType(pointerType()))", files=None,
        working_directory=session.cwd, compile_arguments=[],
    )
    assert isinstance(session.bindings["r"], MatchSet)
    assert dispatch(client, "$r", session) == "matched"


def test_rebinding_does_not_mutate_composed_matcher(tmp_path):
    client, session = runtime(tmp_path)
    dispatch(client, "let m = hasType(pointerType())", session)
    dispatch(client, "let f = varDecl($m)", session)
    dispatch(client, 'let m = hasName("other")', session)
    assert dispatch(client, "$f", session) == "varDecl(hasType(pointerType()))"


def test_non_root_match_and_wrong_reference_do_not_send_request(tmp_path):
    client, session = runtime(tmp_path)
    dispatch(client, "let m = hasType(pointerType())", session)
    assert "top-level matcher" in dispatch(client, "match $m", session)
    dispatch(client, "let count = 3", session)
    assert "requires a matcher" in dispatch(client, "match $count", session)
    assert "unknown variable" in dispatch(client, "match $missing", session)
    client.match.assert_not_called()


def test_registry_node_constructor_reaches_server_as_root(tmp_path):
    client, session = runtime(tmp_path)
    assert dispatch(client, "match pointerType()", session) == "matched"
    assert client.match.call_args.args == ("pointerType()",)


def test_completion_catalog_does_not_extend_local_root_rejection(tmp_path):
    client, session = runtime(tmp_path)
    # This previously uncatalogued name remains the server's responsibility
    # to validate when used outside a concrete node matcher.
    assert dispatch(client, "match isExpansionInSystemHeader()", session) == "matched"
    assert client.match.call_args.args == ("isExpansionInSystemHeader()",)


def test_values_env_config_and_scoped_foreach(tmp_path):
    client, session = runtime(
        tmp_path, environment={"item": "environment"}, config_vars={"item": "config"}
    )
    assert dispatch(client, "let b = true", session) == ""
    assert session.bindings["b"] is True
    dispatch(client, 'let item = "runtime"', session)
    dispatch(client, "let xs = [1, 2, 3]", session)
    assert (
        dispatch(
            client, 'let lines = foreach $item in $xs do "item=${item}" done', session
        )
        == ""
    )
    assert dispatch(client, "$lines", session) == "item=1\nitem=2\nitem=3"
    assert dispatch(client, "$item", session) == "runtime"
    assert dispatch(client, "$env.item", session) == "environment"
    assert dispatch(client, "$config.item", session) == "config"
    client.match.assert_not_called()


def test_foreach_statement_blocks_print_in_order_and_restore_scope(tmp_path):
    client, session = runtime(tmp_path)
    dispatch(client, 'let xs = [{root: {decl_name: "alpha"}}, {root: {decl_name: "beta"}}]', session)
    dispatch(client, 'let m = "outer"', session)

    output = dispatch(
        client,
        "foreach m in $xs do {\n"
        "  let current = $m.root.decl_name\n"
        "  print $current\n"
        "  foreach $n in [1, 2] do { print $n }\n"
        "}",
        session,
    )

    assert output == "alpha\n1\n2\nbeta\n1\n2"
    dispatch(
        client,
        "let names = foreach m in $xs do $m.root.decl_name done",
        session,
    )
    assert dispatch(client, "$names", session) == "alpha\nbeta"
    assert dispatch(client, "$m", session) == "outer"
    assert "current" not in session.bindings
    client.match.assert_not_called()


def test_foreach_empty_block_and_legacy_dictionary_expression(tmp_path):
    client, session = runtime(tmp_path)
    dispatch(client, "let xs = [1]", session)

    assert dispatch(client, "foreach x in $xs do {\n}", session) == ""
    assert dispatch(client, "foreach x in $xs do {}", session) == ""
    assert dispatch(
        client, "let empty_maps = foreach x in $xs do {} done", session
    ) == ""
    assert dispatch(client, "$empty_maps[0]", session) == "{}"
    assert dispatch(
        client, 'let values = foreach x in $xs do {"item": $x} done', session
    ) == ""
    assert dispatch(client, "$values[0]", session) == '{"item": 1}'
    assert dispatch(
        client, "let empty = foreach $x in $xs do {} done", session
    ) == ""
    assert dispatch(client, "$empty[0]", session) == "{}"
    assert dispatch(client, "let truths = foreach x in $xs do true done", session) == ""
    assert dispatch(client, "$truths[0]", session) == "true"


def test_foreach_plain_iterator_rejects_dotted_declarations(tmp_path):
    client, session = runtime(tmp_path)
    dispatch(client, "let xs = [1]", session)

    output = dispatch(client, "foreach item.field in $xs do {}", session)

    assert "unexpected `.`" in output
    client.match.assert_not_called()


def test_brace_foreach_blocks_leave_batch_newlines_for_following_commands(tmp_path):
    client, session = runtime(tmp_path)
    source = "\n".join([
        "let xs = [1, 2]",
        "foreach x in $xs do { print $x }",
        "foreach y in $xs do { print $y }",
        "foreach z in $xs do {}",
        "let names = foreach m in $xs do $m",
        "# the expression body ends on the next line",
        "done",
        "let empty_maps = foreach m in $xs do {} done",
        'print "done"',
    ])

    result = execute_batch(
        source,
        lambda command: dispatch_result(client, command, session),
    )

    assert result.exit_code == 0
    assert result.outputs == ("1\n2", "1\n2", "done")
    assert session.bindings["names"] == [1, 2]
    assert session.bindings["empty_maps"] == [{}, {}]


def test_legacy_foreach_multiline_done_leaves_following_batch_command(tmp_path):
    client, session = runtime(tmp_path)
    source = "\n".join([
        "let xs = [1, 2]",
        "foreach $x in $xs do",
        '"$x"',
        "done",
        'print "after"',
    ])

    result = execute_batch(
        source,
        lambda command: dispatch_result(client, command, session),
    )

    assert result.exit_code == 0
    assert result.outputs == ("1\n2", "after")


def test_nested_foreach_block_match_uses_generated_matcher_text(tmp_path):
    client, session = runtime(tmp_path)
    dispatch(client, "let xs = [1]", session)

    dispatch(
        client,
        "let output = foreach x in $xs do { match functionDecl() }",
        session,
    )

    client.match.assert_called_once_with(
        "functionDecl()", files=None, working_directory=session.cwd,
        compile_arguments=[],
    )


def test_foreach_failure_leaves_assignment_unmodified(tmp_path):
    client, session = runtime(tmp_path)
    dispatch(client, 'let result = "old"', session)
    dispatch(client, "let xs = [1, 2]", session)
    assert "foreach element 0" in dispatch(
        client, "let result = foreach $x in $xs do $missing done", session
    )
    assert dispatch(client, "$result", session) == "old"


def test_glob_is_sorted_and_match_receives_absolute_files(tmp_path):
    client, session = runtime(tmp_path)
    (tmp_path / "b.cpp").write_text("")
    (tmp_path / "a.cpp").write_text("")
    (tmp_path / "x.h").write_text("")
    dispatch(client, 'let files = glob("*.cpp")', session)
    assert [type(entry) for entry in session.bindings["files"]] == [File, File]
    assert [str(entry) for entry in session.bindings["files"]] == ["a.cpp", "b.cpp"]
    store = RowStore()
    owner = CursorOwner(client, "empty", 1, lambda _: None)
    client.match_in.return_value = MatchValue._from_store(store, owner)
    assert dispatch(client, "match varDecl() in $files", session) == ""
    assert sorted(call.args[1] for call in client.match_in.call_args_list) == [
        str((tmp_path / "a.cpp").resolve()), str((tmp_path / "b.cpp").resolve())
    ]
    assert all(
        call.kwargs["traversal_mode"] == match_service_pb2.MATCH_TRAVERSAL_MODE_AS_IS
        for call in client.match_in.call_args_list
    )


def test_literal_matcher_preserves_multiline_source(tmp_path):
    client, session = runtime(tmp_path)
    expression = 'functionDecl(\n  hasName("f[()]")\n).bind("fn")'
    assert dispatch(client, "match\n" + expression, session) == "matched"
    client.match.assert_called_once_with(
        expression, files=None, working_directory=session.cwd, compile_arguments=[],
    )


def test_strings_with_brackets_and_interpolation(tmp_path):
    client, session = runtime(tmp_path)
    dispatch(client, 'let name = "foo[()]"', session)
    assert dispatch(client, '"Name: ${name}"', session) == "Name: foo[()]"
    assert dispatch(client, 'let m = varDecl(hasName("${name}"))', session) == ""
    assert dispatch(client, "$m", session) == 'varDecl(hasName("foo[()]"))'


def test_glob_returns_file_and_directory_with_path_metadata(tmp_path):
    client, session = runtime(tmp_path)
    source = tmp_path / "src"
    source.mkdir()
    (source / "unit.cpp").write_text("abc")
    assert dispatch(client, 'let entries = glob("src/*")', session) == ""
    assert dispatch(client, 'let roots = glob("*")', session) == ""
    file = session.bindings["entries"][0]
    directory = session.bindings["roots"][0]
    assert isinstance(file, File)
    assert isinstance(directory, Directory)
    assert file.size == 3
    assert isinstance(file.modified, datetime)
    assert file.modified.tzinfo == timezone.utc
    assert file.basename == "unit.cpp"
    assert file.dirname == "src"
    assert file.absolute == str(source / "unit.cpp")
    assert file.parts == ["src", "unit.cpp"]
    assert dispatch(client, "let file = $entries", session) == ""
    assert dispatch(client, "foreach $x in $entries do $x", session) == "src/unit.cpp"
    assert dispatch(client, "$roots", session) == "src"
    assert directory.basename == "src"
    assert directory.dirname == "."
    assert (
        dispatch(client, 'foreach $x in $entries do "${x.basename}"', session)
        == "unit.cpp"
    )
    assert (
        dispatch(client, 'foreach $x in $entries do "${x.modified}"', session)
        == file.modified.isoformat()
    )


def test_list_properties_and_join_method(tmp_path):
    client, session = runtime(tmp_path)
    dispatch(client, 'let words = ["alpha", "beta"]', session)
    dispatch(client, "let empty = []", session)
    assert dispatch(client, "$words.length", session) == "2"
    assert dispatch(client, "$words.isEmpty", session) == "false"
    assert dispatch(client, "$empty.length", session) == "0"
    assert dispatch(client, "$empty.isEmpty", session) == "true"
    assert dispatch(client, '$words.joinWith(", ")', session) == "alpha, beta"
    dispatch(client, "let separator = ', '", session)
    assert dispatch(client, "$words.joinWith($separator)", session) == "alpha, beta"
    assert dispatch(client, '"${words.joinWith($separator)}"', session) == "alpha, beta"
    assert dispatch(client, "\"${words.joinWith(', ')}\"", session) == "alpha, beta"
    assert "joinWith requires" in dispatch(client, "$words.joinWith(3)", session)


def test_quote_modes_short_interpolation_and_escaped_dollar(tmp_path):
    client, session = runtime(tmp_path)
    dispatch(client, 'let x = "world"', session)
    assert dispatch(client, '"Hello $x / ${x}"', session) == "Hello world / world"
    assert dispatch(client, "'Hello $x / ${x}'", session) == "Hello $x / ${x}"
    assert (
        dispatch(client, r'"literal \$x and \${x}"', session) == "literal $x and ${x}"
    )
    assert dispatch(client, '"Price is $5"', session) == "Price is $5"
    assert "unknown variable" in dispatch(client, '"Hello $missing"', session)


def test_match_rejects_directory_in_explicit_file_list(tmp_path):
    client, session = runtime(tmp_path)
    (tmp_path / "src").mkdir()
    dispatch(client, 'let entries = glob("*")', session)
    assert "directories" in dispatch(client, "match varDecl() in $entries", session)
    client.match.assert_not_called()


def test_direct_match_respects_quote_interpolation_rules(tmp_path):
    client, session = runtime(tmp_path)
    dispatch(client, 'let name = "target"', session)
    assert dispatch(client, 'match varDecl(hasName("$name"))', session) == "matched"
    client.match.assert_called_with(
        'varDecl(hasName("target"))', files=None,
        working_directory=session.cwd, compile_arguments=[],
    )
    assert dispatch(client, "match varDecl(hasName('$name'))", session) == "matched"
    client.match.assert_called_with(
        "varDecl(hasName('$name'))", files=None,
        working_directory=session.cwd, compile_arguments=[],
    )
