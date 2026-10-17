"""Acceptance of the actual server index through the UI-facing gRPC API."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import time

import grpc
import pytest
from pytest_bdd import given, scenarios, then, when

from clang_toolkit import Client
from clang_toolkit._generated.index.v1 import index_service_pb2 as pb
from clang_toolkit._generated.index.v1 import index_service_pb2_grpc as rpc
from tests.e2e.test_network_steps import _launch_server

pytestmark = pytest.mark.e2e
scenarios("project_index.feature")


def _until(check, timeout=30):
    end = time.monotonic() + timeout
    last = None
    while time.monotonic() < end:
        last = check()
        if last:
            return last
        time.sleep(0.05)
    raise AssertionError(f"index did not reach expected state: {last}")


@given("an isolated server and three translation units with a shared header", target_fixture="indexed_project")
def project(tmp_path, request, monkeypatch):
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "storage"))
    server = _launch_server("unix", tmp_path, request)
    root = tmp_path / "project"
    root.mkdir()
    (root / "shared.hpp").write_text(
        "#include <vector>\nstruct SharedBefore { std::vector<int> values; };\n",
        encoding="utf-8")
    for name in ("one", "two"):
        (root / f"{name}.cc").write_text(
            f'#include "shared.hpp"\nint {name}() {{return 1;}}\n', encoding="utf-8")
    (root / "unrelated.cc").write_text("int unrelated() {return 0;}\n", encoding="utf-8")
    compiler = os.environ.get("CTK_TEST_CLANG", "clang++")
    (root / "compile_commands.json").write_text(json.dumps([
        {"directory": str(root), "file": str(root / f"{name}.cc"),
         "arguments": [compiler, "-std=c++20", "-c", str(root / f"{name}.cc")]}
        for name in ("one", "two", "unrelated")
    ]), encoding="utf-8")
    return {"server": server, "root": root, "storage": tmp_path / "storage"}


@when("I index the project and pause background refresh through gRPC")
def index_and_pause(indexed_project):
    root = indexed_project["root"]
    with grpc.insecure_channel(indexed_project["server"].endpoint) as channel:
        stub = rpc.IndexServiceStub(channel)
        request = pb.ProjectIndexRequest(project_root=str(root))
        start = time.monotonic()
        stub.StartProjectIndex(pb.StartProjectIndexRequest(
            project_root=str(root), poll_interval_seconds=1), timeout=2)
        assert time.monotonic() - start < 2
        status = _until(lambda: (
            s if (s := stub.GetProjectIndexStatus(request, timeout=1)).state == pb.INDEX_STATE_COMPLETE
            else None))
        assert status.translation_units_indexed == 3
        assert status.translation_units_failed == 0
        indexed_project["revision"] = status.revision
        paused = stub.PauseProjectIndex(request, timeout=1)
        assert paused.state == pb.INDEX_STATE_PAUSED


@then("symbol lookup remains available and foreground parsing still works")
def foreground_works(indexed_project):
    root = indexed_project["root"]
    with Client(indexed_project["server"].endpoint) as client:
        result = client.find_symbols(root, "SharedBefore")
        assert len(result.symbols) >= 2
        assert {Path(s.translation_unit).name for s in result.symbols} == {"one.cc", "two.cc"}
        assert all(s.usr and s.compile_context for s in result.symbols)
        assert client.lookup_symbol(root, result.symbols[0].usr).symbols
        assert not client.find_symbols(root, "std::", prefix=True).symbols
        with client.parse(root / "unrelated.cc") as tree:
            assert len(tree.match('functionDecl(hasName("unrelated"))')) == 1
    console = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server", indexed_project["server"].endpoint],
        input=f'index status {json.dumps(str(root))}\nprint "INDEX_CONTROLS_OK"\nquit\n',
        text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        cwd=root, timeout=20, check=False,
        env=dict(os.environ, XDG_STATE_HOME=str(root.parent / "console-state")),
    )
    assert console.returncode == 0, console.stdout
    assert "PAUSED" in console.stdout and "INDEX_CONTROLS_OK" in console.stdout
    assert "error:" not in console.stdout.lower(), console.stdout


@when("I edit the shared header and resume background refresh through gRPC")
def edit_and_resume(indexed_project):
    root = indexed_project["root"]
    (root / "shared.hpp").write_text("struct SharedAfter {};\n", encoding="utf-8")
    with Client(indexed_project["server"].endpoint) as client:
        # Allow a reconciliation interval to prove the pause gate prevents publication.
        time.sleep(1.2)
        assert client.project_index_status(root).state == pb.INDEX_STATE_PAUSED
        assert client.find_symbols(root, "SharedBefore").symbols
        assert not client.find_symbols(root, "SharedAfter").symbols
        client.resume_project_index(root)
        _until(lambda: client.find_symbols(root, "SharedAfter").symbols)


@then("only dependent translation units are reindexed and new symbols are found")
def selective_refresh(indexed_project):
    root = indexed_project["root"]
    with Client(indexed_project["server"].endpoint) as client:
        result = _until(lambda: (
            r if len(r := client.find_symbols(root, "SharedAfter").symbols) >= 2 else None))
        assert {Path(s.translation_unit).name for s in result} == {"one.cc", "two.cc"}
        assert not client.find_symbols(root, "SharedBefore").symbols
        status = _until(lambda: (
            s if (s := client.project_index_status(root)).state == pb.INDEX_STATE_COMPLETE else None))
        assert status.translation_units_indexed == 3
        # Exactly the two dependent TU contributions were replaced.
        assert status.revision == indexed_project["revision"] + 2
        assert client.find_symbols(root, "unrelated").symbols


@when("I introduce an invalid header and resume indexing")
def invalidate_header(indexed_project):
    root = indexed_project["root"]
    (root / "shared.hpp").write_text("struct Invalid {\n", encoding="utf-8")
    with Client(indexed_project["server"].endpoint) as client:
        client.resume_project_index(root)
        _until(lambda: client.project_index_status(root).translation_units_failed >= 1)


@then("prior symbols remain available with stale coverage until the header is repaired")
def failed_refresh_preserves_symbols(indexed_project):
    root = indexed_project["root"]
    with Client(indexed_project["server"].endpoint) as client:
        prior = client.find_symbols(root, "SharedBefore")
        assert prior.symbols and prior.stale
        assert client.project_index_status(root).error
        (root / "shared.hpp").write_text("struct Repaired {};\n", encoding="utf-8")
        _until(lambda: len(client.find_symbols(root, "Repaired").symbols) >= 2)
        assert not client.find_symbols(root, "SharedBefore").symbols


@then("status controls and native parsing respond during a large TU refresh")
def foreground_during_indexing(indexed_project):
    root = indexed_project["root"]
    with Client(indexed_project["server"].endpoint) as client:
        # Warm the foreground toolchain/cache separately from the contention check.
        with client.parse(root / "unrelated.cc") as tree:
            assert len(tree.match('functionDecl(hasName("unrelated"))')) == 1
        (root / "one.cc").write_text(
            "\n".join(f"int indexed_symbol_{n};" for n in range(50000)), encoding="utf-8")
        client.resume_project_index(root)
        _until(lambda: client.project_index_status(root).current_translation_unit.endswith("one.cc"))
        with grpc.insecure_channel(indexed_project["server"].endpoint) as channel:
            stub = rpc.IndexServiceStub(channel)
            query = pb.ProjectIndexRequest(project_root=str(root))
            for _ in range(10):
                stub.GetProjectIndexStatus(query, timeout=0.5)
            started = time.monotonic()
            with client.parse(root / "unrelated.cc") as tree:
                assert len(tree.match('functionDecl(hasName("unrelated"))')) == 1
            assert time.monotonic() - started < 3
            stub.PauseProjectIndex(query, timeout=0.5)
            assert stub.GetProjectIndexStatus(query, timeout=0.5).state == pb.INDEX_STATE_PAUSED
            client.cancel_project_index(root)
