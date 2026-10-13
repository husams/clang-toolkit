"""Real-server acceptance for the experimental runtime host bridge."""

from __future__ import annotations

import gc
import json
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

from tests.e2e.test_network_steps import RunningServer, _launch_server

pytestmark = pytest.mark.e2e
scenarios("prototype_runtime.feature")


_RESOURCE_COUNTERS = (
    "result_cursors",
    "explicit_file_leases",
    "active_work",
    "reserved_bytes",
    "reusable_snapshots",
)


def _resource_counters(status: object) -> tuple[int, ...]:
    return tuple(int(getattr(status, field)) for field in _RESOURCE_COUNTERS)


def _prototype_server(
    tmp_path: Path, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch
) -> RunningServer:
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "prototype-storage"))
    return _launch_server("unix", tmp_path, request)


@given("a prototype query server using unix", target_fixture="prototype_server")
def prototype_server(
    tmp_path: Path,
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> RunningServer:
    return _prototype_server(tmp_path, request, monkeypatch)


@given(
    "a prototype C++ file with a caller and callee", target_fixture="prototype_source"
)
def prototype_source(tmp_path: Path) -> Path:
    source = tmp_path / "prototype_match.cc"
    source.write_text(
        "int callee() { return 7; }\nint caller() { return callee(); }\n",
        encoding="utf-8",
    )
    return source


@when(
    "I run prototype status and lazy host calls through both engines",
    target_fixture="status_evidence",
)
def run_status_evidence(prototype_server: RunningServer, tmp_path: Path):
    from clang_toolkit import Client
    from clang_toolkit.cli.runtime import Runtime
    from clang_toolkit.cli.runtime.prototype import run_source
    from clang_toolkit.cli.runtime.prototype.bridge import ctk_function

    source = (
        'let status = ctk("server status")\n'
        "let ready = $status.cache.memory_available and $status.cache.storage_available\n"
        'let category = if $ready do "ready" else "unavailable"\n'
        'let skipped = false and ctk("file open \\"danger.cc\\"")\n'
        "[$category, $skipped]"
    )
    evidence = []
    for engine in ("tree", "compiled"):
        with Client(prototype_server.endpoint) as client:
            runtime = Runtime(client, cwd=tmp_path, environment={})
            calls: list[str] = []
            adapter = ctk_function(runtime)

            def host(expression: str):
                calls.append(expression)
                return adapter(expression)

            before = _resource_counters(client.resource_status())
            result = run_source(source, engine=engine, functions={"ctk": host})
            during = _resource_counters(client.resource_status())
            result.bindings.clear()
            runtime.close()
            gc.collect()
            client.prune_caches(memory=True, disk=True)
            after = _resource_counters(client.resource_status())
            evidence.append((engine, result.value, calls, before, during, after))
    return evidence


@then("both prototype engines report ready without opening a file")
def verify_status_evidence(status_evidence) -> None:
    assert [item[0] for item in status_evidence] == ["tree", "compiled"]
    for _, value, calls, before, during, after in status_evidence:
        assert value == ["ready", False]
        assert calls == ["server status"]
        assert during == before == after
        assert after == (0, 0, 0, 0, 0)


@when(
    "I run prototype match continuation through both engines",
    target_fixture="match_evidence",
)
def run_match_evidence(
    prototype_server: RunningServer, prototype_source: Path, tmp_path: Path
):
    from clang_toolkit import Client
    from clang_toolkit.cli.runtime import Runtime
    from clang_toolkit.cli.runtime.prototype import run_source
    from clang_toolkit.cli.runtime.prototype.bridge import ctk_function

    first = (
        'let functions = match functionDecl(hasName("caller")).bind("f") '
        f'in "{prototype_source.name}"'
    )
    second = 'let calls = match callExpr().bind("call") in $functions.f'
    source = (
        f"let functions = ctk({json.dumps(first)})\n"
        f"let calls = ctk({json.dumps(second)})\n"
        "[$calls.length, $calls[0].call.decl_name]"
    )
    evidence = []
    for engine in ("tree", "compiled"):
        with Client(prototype_server.endpoint) as client:
            runtime = Runtime(client, cwd=tmp_path, environment={})
            calls: list[str] = []
            adapter = ctk_function(runtime)

            def host(expression: str):
                calls.append(expression)
                return adapter(expression)

            before = _resource_counters(client.resource_status())
            result = run_source(source, engine=engine, functions={"ctk": host})
            during = _resource_counters(client.resource_status())
            runtime_bindings = tuple(sorted(runtime.bindings))
            result.bindings.clear()
            runtime.close()
            gc.collect()
            client.prune_caches(memory=True, disk=True)
            after = _resource_counters(client.resource_status())
            evidence.append(
                (engine, result.value, calls, runtime_bindings, before, during, after)
            )
    return evidence


@then("both prototype engines return the typed callee and clean native resources")
def verify_match_evidence(match_evidence) -> None:
    assert [item[0] for item in match_evidence] == ["tree", "compiled"]
    for _, value, calls, runtime_bindings, before, during, after in match_evidence:
        assert value == [1, "callee"]
        assert calls == [
            'let functions = match functionDecl(hasName("caller")).bind("f") in "prototype_match.cc"',
            'let calls = match callExpr().bind("call") in $functions.f',
        ]
        assert {"functions", "calls"}.issubset(runtime_bindings)
        assert during[0] > before[0]
        assert after == (0, 0, 0, 0, 0)
