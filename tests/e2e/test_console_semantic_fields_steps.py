"""Semantic field access through real console input and a private native server."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

from tests.e2e.test_network_steps import _launch_server

pytestmark = pytest.mark.e2e
scenarios("console_semantic_fields.feature")


@given("a private native server and functions for field inspection", target_fixture="field_console")
def field_console(tmp_path, request):
    server = _launch_server("unix", tmp_path, request)
    source = tmp_path / "functions.cc"
    source.write_text("int alpha(int x) { return 7; }\nint beta() { return 9; }\n")
    return server, source, tmp_path


def run_console(field_console, commands):
    server, source, tmp_path = field_console
    prefix = [
        f'let tree = parse "{source}"',
        'let functions = match functionDecl(isDefinition()).bind("f") in $tree',
    ]
    result = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server", server.endpoint],
        input="\n".join([*prefix, *commands, "quit", ""]),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=dict(os.environ, XDG_STATE_HOME=str(tmp_path / "field-state")),
        timeout=45,
        check=False,
    )
    assert result.returncode == 0, result.stdout
    assert server.process.poll() is None
    return result.stdout


@when("I extract names and continue matching through the real console", target_fixture="field_output")
def extract_fields(field_console):
    return run_console(field_console, [
        'let first = $functions[0].f.value.node.function_decl',
        'print $first.function.declarator.value.named.qualified_name',
        'print $first.hasField("is_deleted")',
        'print $first.is_deleted',
        'print $first.hasField("parameters")',
        'print $first.return_type.description.spelling',
        'print $first.parameters.length',
        'let names = foreach $row in $functions do $row.f.value.node.function_decl.function.declarator.value.named.qualified_name done',
        'print $names.joinWith("|")',
        'let calls = match integerLiteral().bind("n") in $functions.f',
        'print $calls.length',
        'let numbers = foreach $row in $calls do $row.n.value.node.integer_literal.value.unsigned_decimal done',
        'print $numbers.joinWith("|")',
        'let all = match functionDecl(hasName("alpha")).bind("length") in $tree',
        'print $all[0].bindings["length"].value.node.function_decl.function.declarator.value.named.qualified_name',
        'inspect $first',
        'inspect $functions[0].f',
        'inspect $functions[0]',
        'inspect $functions',
        'inspect $tree',
        'print "FIELDS_OK"',
    ])


@then("the console prints function names and both continued literal values")
def verify_fields(field_output):
    assert "syntax error" not in field_output, field_output
    assert "error: field was not requested" in field_output
    assert "alpha|beta" in field_output
    assert "7|9" in field_output
    assert "false" in field_output
    assert "FIELDS_OK" in field_output
    assert "is_deleted" in field_output
    assert '"type": "BindingSelection"' in field_output
    assert '"type": "MatchRow"' in field_output
    assert '"type": "MatchValue"' in field_output
    assert '"type": "ParsedTree"' in field_output
    assert "FunctionDeclInfo.parameters" in field_output
    assert "owned child expansion is not part of the shallow projection" in field_output
    assert "int" in field_output
    assert "2" in field_output


@when("I read an inactive payload after assigning a previous value", target_fixture="field_failure_output")
def read_absent_field(field_console):
    return run_console(field_console, [
        'let retained = "PREVIOUS_VALUE"',
        'let retained = $functions[0].f.value.node.integer_literal',
        'print $retained',
        'print $functions[0].f.value.node.function_decl.function.declarator.value.named.qualified_name',
    ])


@then("the console explains the unavailable field and preserves the previous value")
def verify_failed_fields(field_failure_output):
    assert "integer_literal" in field_failure_output
    assert "error: inactive oneof field" in field_failure_output
    assert "ctk> PREVIOUS_VALUE" in field_failure_output
    assert "alpha" in field_failure_output
