from __future__ import annotations

import json
import os
import subprocess
import sys

from pytest_bdd import given, parsers, scenarios, then, when

from clang_toolkit.cli.app import dispatch
from clang_toolkit.cli.language import parser
from clang_toolkit.client import Client
from clang_toolkit.cli.runtime.persistence import load
from tests.e2e.test_network_steps import _launch_server

scenarios("console_file_batches.feature")


@given(
    "an offline console client for file resource help", target_fixture="offline_client"
)
def offline_client() -> Client:
    return Client("unix:///tmp/ctk-file-resource-help-no-server.sock")


@when(parsers.parse('I request console help for "{topic}"'), target_fixture="help_text")
def request_help(offline_client: Client, topic: str) -> str:
    return dispatch(offline_client, f"help {topic}") or ""


@then(parsers.parse('the help output includes "{expected}"'))
def help_includes(help_text: str, expected: str) -> None:
    assert expected in help_text


@given("the file resource console grammar", target_fixture="grammar")
def resource_grammar():
    return parser()


@when("I parse the supported resource statements", target_fixture="parsed_commands")
def parse_resource_commands(grammar):
    statements = (
        ('let inputs = files "src/"', "assignment"),
        ('file open "src/a.cpp" into $source', "file_open"),
        ("file list", "file_list"),
        ("resource status", "resource_status"),
        ("batch part in $inputs size 10 do { print $part.index; }", "batch_statement"),
    )
    return [
        (grammar.parse(source).children[0].data, expected)
        for source, expected in statements
    ]


@then("each statement has its expected command node")
def resource_command_shapes(parsed_commands) -> None:
    assert all(actual == expected for actual, expected in parsed_commands)


@given("an isolated console batch value server with three sources", target_fixture="batch_value_server")
def batch_value_server(tmp_path, request, monkeypatch):
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "isolated-storage"))
    server = _launch_server("unix", tmp_path, request, max_files=1)
    for index in range(3):
        (tmp_path / f"input-{index}.cc").write_text(
            f"int collected_{index}() {{ return {index}; }}\n", encoding="utf-8"
        )
    return server, tmp_path


@when("I collect native match values through an assigned console batch and save them",
      target_fixture="collected_batch_evidence")
def collect_batch_values(batch_value_server):
    server, root = batch_value_server
    source = '\n'.join([
        'let inputs = files "*.cc"',
        'let report = batch part in $inputs size 1 do {',
        '  print "assignment must be silent";',
        '  match functionDecl().bind("f") in $part.inputs;',
        '}',
        'save $report.results to "collected.proto" as proto',
        'save $report.results to "collected.json" as json',
        'print $report.status',
        'print $report.result_group_indices',
        'print $report.cleanup_acknowledged',
    ])
    result = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server", server.endpoint, "-e", source],
        cwd=root, env=dict(os.environ, XDG_STATE_HOME=str(root / "console-state")),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=90, check=False,
    )
    with Client(server.endpoint) as client:
        status = client.resource_status()
    return result, root, status


@then("the collected values remain readable with no live native resources")
def collected_batch_cleanup(collected_batch_evidence):
    result, root, status = collected_batch_evidence
    assert result.returncode == 0, result.stdout
    assert result.stdout.splitlines() == ["completed", "1", "2", "3", "true"]
    detached = load(root / "collected.proto")
    assert len(detached) == 3
    assert all(len(group.rows) == 1 for group in detached)
    document = json.loads((root / "collected.json").read_text())
    assert len(document) == 3
    encoded = json.dumps(document)
    assert all(f"collected_{index}" in encoded for index in range(3))
    for counter in (
        "result_cursors", "explicit_file_leases", "active_work", "reserved_bytes",
        "accounted_native_bytes", "reusable_snapshots",
    ):
        assert getattr(status, counter) == 0, counter
