"""Real-console acceptance for native multi-file reasoning values."""

from __future__ import annotations

import os
import asyncio
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

from tests.e2e.test_network_steps import _launch_server

pytestmark = pytest.mark.e2e
scenarios("reasoning_values.feature")


@given("a private server and two source files for reasoning values", target_fixture="values_fixture")
def values_fixture(tmp_path: Path, request):
    server = _launch_server("unix", tmp_path, request)
    (tmp_path / "alpha.cc").write_text(
        "int alpha(int value) { return value; }\n", encoding="utf-8"
    )
    (tmp_path / "beta.cc").write_text(
        "struct Widget { Widget(); };\n"
        "int beta(double value) { return static_cast<int>(value); }\n", encoding="utf-8"
    )
    return server, tmp_path


@when("I define and call parameterized matchers through the console and SDKs", target_fixture="routine_run")
def query_matcher_routines(values_fixture):
    from clang_toolkit import Client, AsyncClient

    server, root = values_fixture
    declarations = [
        'let matcher(name) = functionDecl(hasName($name))',
        'let named(name) = hasName($name)',
        'let definitions() = isDefinition()',
        'let selected(name, predicate) = functionDecl(named($name), $predicate)',
    ]
    script = '\n'.join([
        'let name = "outside"', *declarations,
        'let m = match matcher("alpha").bind("fn") in "alpha.cc"',
        'print "ROUTINE_NAME=${m[0].fn.decl_name}"',
        'let nested = match selected("beta", definitions()).bind("fn") in "*.cc"',
        'print "NESTED_NAME=${nested[0].fn.decl_name}"',
        'match matcher("alpha").bind("func") in "alpha.cc" do {',
        '  let params(name) = parmVarDecl(hasName($name))',
        '  let rows = match params("value").bind("p") in $func.source_file',
        '  print "PARAMETER_NAME=${rows[0].p.decl_name}"',
        '}',
        'print "OUTER_NAME=${name}"',
    ])
    console = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server", server.endpoint, "-e", script],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=root,
        env=dict(os.environ, XDG_STATE_HOME=str(root / "routine-state")),
        timeout=30, check=False,
    )
    with Client(server.endpoint) as client:
        for statement in declarations:
            client.execute(statement, working_directory=root)
        rows = client.execute('match matcher("alpha").bind("fn") in "alpha.cc"')
        synchronous = rows[0].bindings["fn"].node.function_decl.function.declarator.value.named.qualified_name
        assert not client._expression_runtime._scopes

    async def run():
        async with AsyncClient(server.endpoint) as client:
            for statement in declarations:
                await client.execute(statement, working_directory=root)
            rows = await client.execute('match selected("beta", definitions()).bind("fn") in "*.cc"')
            assert not client._expression_runtime._scopes
            return rows[0].bindings["fn"].node.function_decl.function.declarator.value.named.qualified_name

    return console, synchronous, asyncio.run(run())


@then("arguments, binding labels and local routine scopes retain typed matches")
def verify_matcher_routines(routine_run):
    console, synchronous, asynchronous = routine_run
    assert console.returncode == 0, console.stdout
    for text in ("ROUTINE_NAME=alpha", "NESTED_NAME=beta",
                 "PARAMETER_NAME=value", "OUTER_NAME=outside"):
        assert text in console.stdout
    assert "error:" not in console.stdout.lower()
    assert synchronous == "alpha"
    assert asynchronous == "beta"


@when("I read JSON and YAML documents through the console and SDKs", target_fixture="document_run")
def read_documents(values_fixture):
    from clang_toolkit import Client, AsyncClient

    server, root = values_fixture
    (root / "project.json").write_text(
        '{"project": {"name": "demo"}, "sources": ["alpha.cc", "beta.cc"], "enabled": true}',
        encoding="utf-8",
    )
    (root / "project.yaml").write_text(
        "project:\n  name: demo\nsources: [alpha.cc, beta.cc]\nenabled: true\n",
        encoding="utf-8",
    )
    (root / "broken.json").write_text("{broken}", encoding="utf-8")
    script = '\n'.join([
        'let json = read "project.json"',
        'let yaml = read "project.yaml"',
        'print "JSON_NAME=${json.project.name}"',
        'print "YAML_NAME=${yaml.project.name}"',
        'let sources = foreach $source in $yaml.sources do $source done',
        'print "SOURCE_COUNT=${sources.length}"',
        'print "FIRST_SOURCE=${sources[0]}"',
        'print "ENABLED=${json.enabled}"',
        'let filename = "project.yaml"',
        'let indirect = read $filename',
        'print "VARIABLE_NAME=${indirect.project.name}"',
    ])
    console = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server", server.endpoint, "-e", script],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=root,
        env=dict(os.environ, XDG_STATE_HOME=str(root / "read-state")),
        timeout=30, check=False,
    )
    with Client(server.endpoint) as client:
        sync_value = client.execute('read "project.json"', working_directory=root)

    async def run():
        async with AsyncClient(server.endpoint) as client:
            return await client.execute('read "project.yaml"', working_directory=root)

    async_value = asyncio.run(run())
    from clang_toolkit.cli.app import dispatch
    from clang_toolkit.cli.runtime import Runtime

    with Client(server.endpoint) as client:
        runtime = Runtime(client, cwd=root, environment={})
        try:
            runtime.execute('let data = read "project.json"')
            error = dispatch(client, 'let data = read "broken.json"', runtime)
            preserved = runtime.execute("print $data.project.name")
        finally:
            runtime.close()
    return console, sync_value, async_value, error, preserved


@then("document fields, lists and failed reads preserve their expected values")
def verify_documents(document_run):
    console, sync_value, async_value, error, preserved = document_run
    assert console.returncode == 0, console.stdout
    for text in ("JSON_NAME=demo", "YAML_NAME=demo", "SOURCE_COUNT=2",
                 "FIRST_SOURCE=alpha.cc", "ENABLED=true", "VARIABLE_NAME=demo"):
        assert text in console.stdout
    assert sync_value == async_value == {
        "project": {"name": "demo"}, "sources": ["alpha.cc", "beta.cc"], "enabled": True,
    }
    assert "cannot read" in error
    assert preserved == "demo"


@when("I query native multi-file values through the console", target_fixture="values_run")
def query_native_values(values_fixture):
    server, root = values_fixture
    script = "\n".join(
        [
            'set traversal IgnoreUnlessSpelledInSource',
            'let path_rows = match functionDecl(isDefinition()).bind("f") in "alpha.cc"',
            'let one_file = match functionDecl(isDefinition()).bind("f") in ["alpha.cc"]',
            'let rows = match functionDecl(isDefinition()).bind("f") in ["alpha.cc", "beta.cc"]',
            'print "PATH_COUNT=${path_rows.length}"',
            'print $path_rows[0].source_file',
            'print "LIST_COUNT=${one_file.length}"',
            'print "TWO_FILE_COUNT=${rows.length}"',
            'print $rows[0].source_file',
            'print $rows[1].source_file',
            'print $rows[0].f.decl_name',
            'print $rows[1].f.parameter_name',
            'let continued = match parmVarDecl().bind("p") in $rows[1].f',
            'print "CONTINUED_COUNT=${continued.length}"',
            'print "PARENT_ROW=${continued[0].source_match_index}"',
            'let joined_parent = $rows.filter("source_file", $continued[0].source_file)[$continued[0].source_match_index]',
            'print "JOINED_FILE=${joined_parent.source_file}"',
            'let grouped_count = (match parmVarDecl().bind("p") in $rows[0].f).length',
            'print "GROUPED_COUNT=${grouped_count}"',
            'let grouped_rows = foreach $param in (match parmVarDecl().bind("p") in $rows[1].f) do $param.source_file done',
            'print "GROUPED_FOREACH_COUNT=${grouped_rows.length}"',
            'let parsed = parse "alpha.cc"',
            'let parsed_rows = match functionDecl().bind("f") in $parsed',
            'print $parsed_rows[0].source_file',
            'let all_continued = match parmVarDecl().bind("p") in $rows.f',
            'print "AGGREGATE_CONTINUED_COUNT=${all_continued.length}"',
            'let aggregate_bindings = $rows.f',
            'let aggregate_names = foreach $binding in $aggregate_bindings do $binding.decl_name done',
            'print "AGGREGATE_BINDING_COUNT=${aggregate_bindings.length}"',
            'print "AGGREGATE_ITERATION_COUNT=${aggregate_names.length}"',
            'print $all_continued[0].source_file',
            'print $all_continued[1].source_file',
            'let unique_names = $rows.unique("f.decl_name")',
            'let sorted_names = $unique_names.sort("f.decl_name")',
            'let selected = $sorted_names.filter("f.decl_name", "alpha")',
            'print "UNIQUE_COUNT=${unique_names.length}"',
            'print "SORT_FIRST=${sorted_names[0].f.decl_name}"',
            'print "FILTER_COUNT=${selected.length}"',
            'print $rows[0].f.value.node.function_decl.function.fieldState("parameters")',
            'let constructors = match cxxConstructorDecl().bind("ctor") in "beta.cc"',
            'let constructor_names = foreach $row in $constructors do $row.ctor.value.node.name.fieldOr("identifier", "<nonidentifier>") done',
            'print "CONSTRUCTOR_NAME=${constructor_names[0]}"',
            'save $rows to "values-snapshot.yaml"',
            'load "values-snapshot.yaml" into $snapshot',
            'print "DETACHED_COUNT=${snapshot.length}"',
            'print $snapshot[0].source_file',
            'print "DETACHED_FIRST=${snapshot[0].bindings.f.node.function_decl.function.declarator.value.named.qualified_name}"',
            'let detached_names = foreach $row in $snapshot do $row.bindings.f.node.function_decl.function.declarator.value.named.qualified_name done',
            'print "DETACHED_ITERATION=${detached_names.length}"',
        ]
    )
    return subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server", server.endpoint, "-e", script],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=root,
        env=dict(os.environ, XDG_STATE_HOME=str(root / "values-state")),
        timeout=60,
        check=False,
    )


@then("the console reports per-file rows, continuation, and explicit field availability")
def verify_native_values(values_run, values_fixture):
    output = values_run.stdout
    assert values_run.returncode == 0, output
    assert "PATH_COUNT=1" in output
    assert "LIST_COUNT=1" in output
    assert "TWO_FILE_COUNT=2" in output
    assert "alpha.cc" in output and "beta.cc" in output
    assert "alpha" in output and "beta" in output
    assert "CONTINUED_COUNT=1" in output
    assert "PARENT_ROW=0" in output
    assert "JOINED_FILE=" in output and "beta.cc" in output
    assert "GROUPED_COUNT=1" in output
    assert "GROUPED_FOREACH_COUNT=1" in output
    assert "AGGREGATE_CONTINUED_COUNT=2" in output
    assert "AGGREGATE_BINDING_COUNT=2" in output
    assert "AGGREGATE_ITERATION_COUNT=2" in output
    assert "UNIQUE_COUNT=2" in output
    assert "SORT_FIRST=alpha" in output
    assert "FILTER_COUNT=1" in output
    assert "UNREQUESTED" in output
    assert "CONSTRUCTOR_NAME=<nonidentifier>" in output
    assert "DETACHED_COUNT=2" in output
    assert str((values_fixture[1] / "alpha.cc").resolve()) in output
    assert "DETACHED_FIRST=alpha" in output
    assert "DETACHED_ITERATION=2" in output
    assert "error:" not in output.lower(), output
    server, _ = values_fixture
    assert server.process.poll() is None


@when("I match directory and glob inputs through the console and async SDK", target_fixture="path_values_run")
def query_path_values(values_fixture):
    from clang_toolkit import AsyncClient, Client

    server, root = values_fixture
    nested = root / "nested"
    nested.mkdir()
    (nested / "gamma.cpp").write_text("int gamma() { return 3; }\n", encoding="utf-8")
    (root / "ignored.h").write_text("#error Headers are not directory targets\n", encoding="utf-8")
    script = "\n".join([
        f"let directory = match functionDecl(isDefinition()).bind('f') in '{root}'",
        f'let pattern = match functionDecl(isDefinition()).bind("f") in "{root}/*.cc"',
        'let recursive = match functionDecl(isDefinition()).bind("f") in "**/*.cpp"',
        'let file = match functionDecl(isDefinition()).bind("f") in "alpha.cc"',
        'let files = glob("alpha.cc")',
        'let reference = match functionDecl(isDefinition()).bind("f") in $files[0]',
        'let continued = match parmVarDecl().bind("p") in $pattern.f',
        'let empty = match functionDecl() in "missing/*.cpp"',
        'print "DIRECTORY_COUNT=${directory.length}"',
        'print "GLOB_COUNT=${pattern.length}"',
        'print "RECURSIVE_COUNT=${recursive.length}"',
        'print "FILE_COUNT=${file.length}"',
        'print "REFERENCE_COUNT=${reference.length}"',
        'print "CONTINUATION_COUNT=${continued.length}"',
        'print "EMPTY_COUNT=${empty.length}"',
        'print "FIRST_NAME=${pattern[0].f.decl_name}"',
        'print "SECOND_NAME=${pattern[1].f.decl_name}"',
        'print $recursive[0].source_file',
    ])
    console = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server", server.endpoint, "-e", script],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=root,
        env=dict(os.environ, XDG_STATE_HOME=str(root / "path-values-state")),
        timeout=60, check=False,
    )

    async def run_sdk():
        async with AsyncClient(server.endpoint) as client:
            rows = await client.execute(
                'let rows = match functionDecl(isDefinition()).bind("f") in "*.cc"',
                working_directory=root,
            )
            continued = await client.execute('match parmVarDecl().bind("p") in $rows.f')
            return len(rows), len(continued), [row.source_file for row in rows]

    with Client(server.endpoint) as client:
        sync_rows = client.execute(
            'let rows = match functionDecl(isDefinition()).bind("f") in "*.cc"',
            working_directory=root,
        )
        sync_continued = client.execute('match parmVarDecl().bind("p") in $rows.f')
        sync_counts = len(sync_rows), len(sync_continued)
    return console, asyncio.run(run_sdk()), sync_counts


@then("directory and glob results preserve single-file behavior and continuation")
def verify_path_values(path_values_run, values_fixture):
    console, sdk, sync_counts = path_values_run
    assert console.returncode == 0, console.stdout
    for expected in (
        "DIRECTORY_COUNT=3", "GLOB_COUNT=2", "RECURSIVE_COUNT=1",
        "FILE_COUNT=1", "REFERENCE_COUNT=1", "CONTINUATION_COUNT=2",
        "EMPTY_COUNT=0", "FIRST_NAME=alpha", "SECOND_NAME=beta",
    ):
        assert expected in console.stdout
    root = values_fixture[1]
    assert str(root / "nested" / "gamma.cpp") in console.stdout
    assert sdk == (2, 2, [str(root / "alpha.cc"), str(root / "beta.cc")])
    assert sync_counts == (2, 2)


@when("I run streamed match blocks through the console and SDKs", target_fixture="block_values_run")
def query_match_blocks(values_fixture):
    from clang_toolkit import AsyncClient, Client

    server, root = values_fixture
    block = '''match functionDecl(isDefinition()).bind("func") in "*.cc" do {
        # Every label is a local variable for the current streamed row.
        let name = $func.value.node.qualified_name
        let parameters = match parmVarDecl().bind("p") in $func.source_file
        print "BLOCK_NAME=${name};PARAMETERS=${parameters.length}"
        print $name to "streamed-names.txt" mode append
        match parmVarDecl().bind("param") in $func.source_file do {
            print "PARAMETER_NAME=${param.value.node.name.identifier}"
        }
    }'''
    script = '\n'.join([
        'let func = "outside"', block,
        'print "OUTER=${func}"',
        'match functionDecl(isDefinition()) in "alpha.cc" do { print "ROOT=${root.value.node.qualified_name}"; }',
    ])
    console = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server", server.endpoint, "-e", script],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, cwd=root,
        env=dict(os.environ, XDG_STATE_HOME=str(root / "block-values-state")),
        timeout=60, check=False,
    )
    with Client(server.endpoint) as client:
        synchronous = client.execute(block, working_directory=root)
        assert not client._expression_runtime._scopes

    async def run():
        async with AsyncClient(server.endpoint) as client:
            output = await client.execute(block, working_directory=root)
            assert not client._expression_runtime._scopes
            assert not client._values
            return output

    return console, synchronous, asyncio.run(run())


@then("binding fields and nested statements work without leaking row locals")
def verify_match_blocks(block_values_run, values_fixture):
    console, synchronous, asynchronous = block_values_run
    assert console.returncode == 0, console.stdout
    for output in (console.stdout, synchronous, asynchronous):
        assert "BLOCK_NAME=alpha;PARAMETERS=1" in output
        assert "BLOCK_NAME=beta;PARAMETERS=1" in output
        assert output.count("PARAMETER_NAME=value") == 2
        assert "error:" not in output.lower(), output
    assert "OUTER=outside" in console.stdout
    assert "ROOT=alpha" in console.stdout
    lines = (values_fixture[1] / "streamed-names.txt").read_text().splitlines()
    assert sorted(lines) == ["alpha"] * 3 + ["beta"] * 3
