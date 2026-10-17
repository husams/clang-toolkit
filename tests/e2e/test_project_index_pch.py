"""Precompiled input tracking through the actual background worker and gRPC."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import time

import pytest

from clang_toolkit import Client
from tests.e2e.test_network_steps import _launch_server

pytestmark = pytest.mark.e2e


def test_project_index_tracks_precompiled_headers_and_their_source_inputs(tmp_path, request, monkeypatch):
    compiler = os.environ.get("CTK_TEST_CLANG")
    assert compiler, "set CTK_TEST_CLANG to the server compiler"
    storage = tmp_path / "storage"
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(storage))
    server = _launch_server("unix", tmp_path, request)
    root = tmp_path / "project"
    root.mkdir()
    header, pch, source = root / "header.hpp", root / "header.pch", root / "source.cc"
    header.write_text("struct BeforePch {};\n", encoding="utf-8")
    source.write_text("int entry(){return 0;}\n", encoding="utf-8")
    c_source = root / "c_source.c"
    c_source.write_text("int c_entry(void){return _Generic(1, int: 2, default: 3);}\n", encoding="utf-8")

    def build_pch():
        subprocess.run([compiler, "-std=c++20", "-x", "c++-header", str(header),
                        "-o", str(pch)], check=True, capture_output=True, text=True, timeout=30)

    build_pch()
    (root / "compile_commands.json").write_text(json.dumps([
        {"directory": str(root), "file": str(source), "arguments": [
            compiler, "-std=c++20", "-include-pch", str(pch), "-c", str(source)]},
        {"directory": str(root), "file": str(c_source), "arguments": [
            str(Path(compiler).with_name("clang")), "-std=c11", "-c", str(c_source)]},
    ]), encoding="utf-8")

    with Client(server.endpoint) as client:
        client.start_project_index(root, poll_interval_seconds=1)

        def wait_for(name):
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                status = client.project_index_status(root)
                if status.translation_units_indexed:
                    result = client.find_symbols(root, name)
                    if result.symbols:
                        return result
                time.sleep(0.05)
            raise AssertionError(f"PCH index did not produce {name}: {status}")

        before = wait_for("BeforePch")
        assert before.symbols[0].is_definition
        assert client.find_symbols(root, "c_entry").symbols
        databases = list(storage.rglob("symbols.sqlite3"))
        assert len(databases) == 1
        with sqlite3.connect(databases[0]) as db:
            manifest = json.loads(db.execute(
                "SELECT dependencies_json FROM translation_unit WHERE main_file=?", (str(source.resolve()),)
            ).fetchone()[0])
        assert str(pch.resolve()) in manifest
        assert str(header.resolve()) in manifest
        header.write_text("struct AfterPch {};\n", encoding="utf-8")
        build_pch()
        after = wait_for("AfterPch")
        assert after.revision == before.revision + 1
        assert client.find_symbols(root, "c_entry").symbols
        assert not client.find_symbols(root, "BeforePch").symbols
