"""Console coverage for copied source, identity, documentation and call facts."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

from tests.e2e.test_network_steps import _launch_server

pytestmark = pytest.mark.e2e
scenarios("reasoning_facts.feature")


@given("a private server and source with reasoning facts", target_fixture="facts_fixture")
def facts_fixture(tmp_path: Path, request):
    server = _launch_server("unix", tmp_path, request)
    source = tmp_path / "facts.cc"
    source.write_text(
        "#define WRAP(x) documented(x)\n"
        "/// Raw declaration documentation.\n"
        "int documented(int);\n"
        "int overloaded(int);\n"
        "int overloaded(double);\n"
        "struct Base { virtual int run(); };\n"
        "int lambda_owner() { auto lambda = [] { return documented(9); }; "
        "return lambda(); }\n"
        "int call_owner(int (*fp)(int), Base& base) { "
        "int a = WRAP(1); int b = fp(2); int c = base.run(); "
        "return a + b + c; }\n",
        encoding="utf-8",
    )
    return server, source, tmp_path


@when("I query byte offsets and exclusive range ends through the console",
      target_fixture="offset_run")
def query_offsets(facts_fixture):
    server, source, tmp_path = facts_fixture
    with source.open("ab") as output:
        output.write("// caf\u00e9\r\nint offset_owner() { return documented(12345); }\r\n".encode())
    script = "\n".join([
        f'let tree = parse "{source}"',
        'let owner = match functionDecl(hasName("offset_owner")).bind("f") in $tree',
        'let literals = match integerLiteral().bind("n") in $owner.f',
        'print "OFFSET=${literals[0].n.location.offset}"',
        'print "BEGIN=${literals[0].n.range.expansion_begin.offset}"',
        'print "TOKEN_END=${literals[0].n.range.expansion_end.offset}"',
        'print "END=${literals[0].n.range.expansion_end_exclusive.offset}"',
        'print "SPELLING_BEGIN=${literals[0].n.range.spelling_begin.offset}"',
        'print "SPELLING_END=${literals[0].n.range.spelling_end_exclusive.offset}"',
        'let macro_owner = match functionDecl(hasName("call_owner")).bind("f") in $tree',
        'let macros = match callExpr(callee(functionDecl(hasName("documented"))))'
        '.bind("c") in $macro_owner.f',
        'print "MACRO_BEGIN=${macros[0].c.range.expansion_begin.offset}"',
        'print "MACRO_END=${macros[0].c.range.expansion_end_exclusive.offset}"',
    ])
    return subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server",
         server.endpoint, "-e", script],
        capture_output=True, text=True, cwd=tmp_path,
        env=dict(os.environ, XDG_STATE_HOME=str(tmp_path / "offset-state")),
        timeout=45, check=False,
    )


@then("the offsets select complete source bytes including macro invocations")
def verify_offsets(offset_run, facts_fixture):
    assert offset_run.returncode == 0, offset_run.stdout + offset_run.stderr
    values = dict(line.split("=", 1) for line in offset_run.stdout.splitlines()
                  if "=" in line)
    source = facts_fixture[1].read_bytes()
    begin = source.index(b"12345")
    for name in ("OFFSET", "BEGIN", "TOKEN_END", "SPELLING_BEGIN"):
        assert int(values[name]) == begin
    for name in ("END", "SPELLING_END"):
        assert int(values[name]) == begin + 5
    assert source[int(values["BEGIN"]):int(values["END"])] == b"12345"
    assert source[int(values["MACRO_BEGIN"]):int(values["MACRO_END"])] == b"WRAP(1)"
    edited = source[:int(values["BEGIN"])] + b"7" + source[int(values["END"]):]
    assert b"documented(7)" in edited
    assert facts_fixture[0].process.poll() is None


@when("I query lambda and call-site facts through the console", target_fixture="facts_run")
def query_facts(facts_fixture):
    server, source, tmp_path = facts_fixture
    script = "\n".join(
        [
            f'let tree = parse "{source}"',
            'let lambdas = match cxxMethodDecl(ofClass(cxxRecordDecl(isLambda())), '
            'hasName("operator()"), isDefinition()).bind("lam") in $tree',
            'let lambda_calls = match callExpr().bind("c") in $lambdas.lam',
            'print "LAMBDA_CALL_COUNT=${lambda_calls.length}"',
            'print $lambda_calls[0].c.call_site.caller_name',
            'print $lambda_calls[0].c.call_site.static_callee_name',
            'let lambda_owner = match functionDecl(hasName("lambda_owner")).bind("f") in $tree',
            'let whole_lambda_calls = match callExpr().bind("c") in $lambda_owner.f',
            'print "WHOLE_LAMBDA_CALL_COUNT=${whole_lambda_calls.length}"',
            'let owner = match functionDecl(hasName("call_owner")).bind("f") in $tree',
            'let owner_calls = match callExpr().bind("c") in $owner.f',
            'print "STATIC_CALL_COUNT=${owner_calls.length}"',
            'let documented_call = match callExpr(callee(functionDecl(hasName("documented"))))'
            '.bind("c") in $owner.f',
            'print "MACRO_FILE=${documented_call[0].c.location.file}"',
            'print "MACRO_IS_MACRO=${documented_call[0].c.location.is_macro}"',
            'print "MACRO_LINE=${documented_call[0].c.location.line}"',
            'print "SPELLING_LINE=${documented_call[0].c.range.spelling_begin.line}"',
            'print "EXPANSION_LINE=${documented_call[0].c.range.expansion_begin.line}"',
            'let dispatches = foreach $row in $owner_calls do $row.c.call_site.dispatch done',
            'print "DISPATCHES=${dispatches.joinWith(\'|\')}"',
            'let overloads = match functionDecl(hasName("overloaded")).bind("f") in $tree',
            'print "OVERLOAD_COUNT=${overloads.length}"',
            'print $overloads[0].f.symbol_identity',
            'print $overloads[1].f.symbol_identity',
            'let docs = match functionDecl(hasName("documented")).bind("f") in $tree',
            'print $docs[0].f.documentation',
        ]
    )
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "clang_toolkit.cli.app",
            "--server",
            server.endpoint,
            "-e",
            script,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=tmp_path,
        env=dict(os.environ, XDG_STATE_HOME=str(tmp_path / "facts-state")),
        timeout=45,
        check=False,
    )


@then("the console reports complete lambda and static call facts")
def verify_facts(facts_run, facts_fixture):
    output = facts_run.stdout
    assert facts_run.returncode == 0, output
    assert "syntax error" not in output.lower(), output
    assert "error:" not in output.lower(), output
    assert "ctk>" not in output, output
    assert "operator()" in output
    assert "LAMBDA_CALL_COUNT=1" in output
    assert "WHOLE_LAMBDA_CALL_COUNT=2" in output
    assert "STATIC_CALL_COUNT=3" in output
    assert "documented" in output
    assert "MACRO_FILE=" in output and "facts.cc" in output
    assert "macro_is_macro=true" in output.lower()
    assert "MACRO_LINE=8" in output
    assert "SPELLING_LINE=1" in output
    assert "EXPANSION_LINE=8" in output
    assert "OVERLOAD_COUNT=2" in output
    assert "CALL_DISPATCH_DIRECT" in output
    assert "CALL_DISPATCH_INDIRECT" in output
    assert "CALL_DISPATCH_VIRTUAL" in output
    assert "Raw declaration documentation" in output
    # The two overload rows must expose distinct Clang USRs.
    usr_lines = [line.strip() for line in output.splitlines() if "overloaded" in line]
    assert len(usr_lines) >= 2, output
    assert usr_lines[0] != usr_lines[1], usr_lines
    server, _, _ = facts_fixture
    assert server.process.poll() is None
