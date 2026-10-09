"""Execute the bundled agent recipes against a real native analysis server."""

from __future__ import annotations

import functools
import re
from pathlib import Path

import pytest

import clang_toolkit
from test_network_steps import _launch_server

pytestmark = pytest.mark.e2e


def test_skill_recipes_use_executable_public_sdk_examples(tmp_path: Path, request,
                                                         monkeypatch, capsys) -> None:
    server = _launch_server("unix", tmp_path, request)
    source = tmp_path / "reasoning.cc"
    source.write_text(
        "struct Base { virtual int value() { return 1; } };\n"
        "struct Derived : Base { int value() override { return 2; } };\n"
        "namespace ns {\n"
        "int target(int value) { return value; }\n"
        "struct Widget { int run(int value); };\n"
        "int Widget::run(int value) { return target(value); }\n"
        "int exercise(Base &base, int (*indirect)(int)) {\n"
        "  return target(3) + indirect(4) + base.value();\n"
        "}\n"
        "}\n",
        encoding="utf-8",
    )
    real_client = clang_toolkit.Client
    real_async_client = clang_toolkit.AsyncClient
    monkeypatch.setattr(clang_toolkit, "Client", functools.partial(real_client, server.endpoint))
    monkeypatch.setattr(clang_toolkit, "AsyncClient", functools.partial(real_async_client, server.endpoint))
    references = Path(__file__).parents[2] / "skills/ctk-cpp-reasoning/references"
    for name in ("recipes.md", "matchers-and-values.md", "launch-and-api.md"):
        reference = references / name
        blocks = re.findall(r"```python\n(.*?)\n```", reference.read_text(encoding="utf-8"), re.DOTALL)
        assert blocks
        for index, block in enumerate(blocks):
            with real_client(server.endpoint) as client:
                namespace = {
                    "Client": clang_toolkit.Client,
                    "client": client,
                    "source": source,
                    "source_files": [source],
                    "project_root": tmp_path,
                }
                exec("from clang_toolkit.matchers import *", namespace)
                exec(compile(block, f"{reference}:example-{index + 1}", "exec"), namespace)
    output = capsys.readouterr().out
    assert "definitions:" in output
    assert "ns::target" in output
    assert "DIRECT" in output and "INDIRECT" in output and "VIRTUAL" in output
    assert "Derived" in output and "Base" in output
