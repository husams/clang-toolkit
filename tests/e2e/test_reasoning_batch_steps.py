"""Real RPC coverage for noninteractive multiline console batches."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

from tests.e2e.test_network_steps import _launch_server

pytestmark = pytest.mark.e2e
scenarios("reasoning_batch.feature")


@given("a private server and a tiny batch fixture", target_fixture="batch_fixture")
def batch_fixture(tmp_path: Path, request):
    server = _launch_server("unix", tmp_path, request)
    source = tmp_path / "batch.cc"
    source.write_text(
        "int batch_one() { return 1; }\n"
        "int batch_two() { return 2; }\n",
        encoding="utf-8",
    )
    return server, source, tmp_path


@when("I execute the fixture through the CLI batch path", target_fixture="batch_run")
def execute_batch(batch_fixture):
    server, source, tmp_path = batch_fixture
    script = (
        f'let fns = match functionDecl(isDefinition()).bind("f") in "{source}"\n'
        'foreach $fn in $fns do\n'
        '"${fn.f.value.node.qualified_name}"\n'
        "done"
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
        env=dict(os.environ, XDG_STATE_HOME=str(tmp_path / "batch-state")),
        timeout=30,
        check=False,
    )


@then("the batch prints both function names without a prompt")
def batch_has_names(batch_run):
    assert batch_run.returncode == 0, batch_run.stdout
    assert "batch_one" in batch_run.stdout
    assert "batch_two" in batch_run.stdout
    assert "ctk>" not in batch_run.stdout
