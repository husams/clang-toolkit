"""Real-console acceptance for native multi-file reasoning values."""

from __future__ import annotations

import os
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
