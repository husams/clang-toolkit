"""Run the portable skill scripts through the actual console and native server."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from tests.e2e.test_network_steps import RunningServer, _launch_server

pytestmark = pytest.mark.e2e
scenarios("ctk_flow_scripts.feature")


@dataclass
class FlowFixture:
    server: RunningServer
    skill: Path
    source: Path
    work: Path
    engine: str


@given(
    parsers.parse("an isolated flow-script fixture with the {engine} engine"),
    target_fixture="flow_fixture",
)
def flow_fixture(
    engine: str,
    tmp_path: Path,
    request: pytest.FixtureRequest,
    monkeypatch: pytest.MonkeyPatch,
) -> FlowFixture:
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "native-storage"))
    server = _launch_server("unix", tmp_path, request, max_send_bytes=4096)
    original = Path(__file__).resolve().parents[2] / "skills" / "ctk-script"
    skill = tmp_path / "installed skill"
    shutil.copytree(original, skill)
    work = tmp_path / "agent work"
    work.mkdir()
    (work / "empty-lib").mkdir()
    source = work / "loop score.cc"
    shutil.copyfile(skill / "assets" / "flow_fixture.cc", source)
    return FlowFixture(server, skill, source, work, engine)


def _run(
    fixture: FlowFixture,
    script: str,
    case: str,
    *,
    function: str = "score",
    variable: str = "total",
) -> tuple[subprocess.CompletedProcess[str], Path]:
    output = fixture.work / f"{case} report.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "clang_toolkit.cli.app",
            "--server",
            fixture.server.endpoint,
            "--lib-dir",
            str(fixture.work / "empty-lib"),
            "--script-engine",
            fixture.engine,
            "--script",
            str(fixture.skill / "scripts" / script),
            f"path={fixture.source}",
            f"function={function}",
            f"variable={variable}",
            f"output={output}",
        ],
        cwd=fixture.work,
        env=dict(os.environ, XDG_STATE_HOME=str(fixture.work / "state")),
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert fixture.server.process.poll() is None
    return result, output


@when(
    "I run the bundled CFG, usage and value-range scripts with named arguments",
    target_fixture="flow_evidence",
)
def run_recipes(flow_fixture: FlowFixture) -> dict[str, Any]:
    evidence: dict[str, Any] = {}
    for name in ("cfg_stream", "local_usage", "value_ranges"):
        result, output = _run(flow_fixture, f"{name}.ctk", name)
        assert result.returncode == 0, result.stdout + result.stderr
        assert result.stderr == ""
        evidence[f"{name}_stdout"] = result.stdout
        if name == "cfg_stream":
            assert not output.exists()
        else:
            evidence[name] = json.loads(output.read_text(encoding="utf-8"))
    return evidence


@then("the stream, exported facts and loop ranges describe the supplied fixture")
def verify_recipes(flow_evidence: dict[str, Any]) -> None:
    remaining = flow_evidence["cfg_stream_stdout"].lstrip()
    events = []
    decoder = json.JSONDecoder()
    while remaining:
        event, offset = decoder.raw_decode(remaining)
        events.append(event)
        remaining = remaining[offset:].lstrip()
    kinds = [next(iter(event)) for event in events]
    assert kinds[0] == "graph_started" and kinds[-1] == "completed"
    assert kinds.count("graph_started") == kinds.count("graph_completed") == 1
    assert kinds.count("block") > 0
    assert int(events[-1]["completed"]["graph_count"]) == 1

    plain, numeric = flow_evidence["local_usage"], flow_evidence["value_ranges"]
    for report in (plain, numeric):
        assert report["analysis"]["variable"] == "total"
        assert report["completed"]["is_complete"]
        assert not report.get("findings", [])
        assert len(report["usages"]) == len(report["facts"]) == 6
    assert all("value_before" not in fact for fact in plain["facts"])
    assert all("value_after" not in fact for fact in plain["facts"])
    assert numeric["analysis"]["value_domain"] == "INTERVAL"
    usages = {usage["id"]: usage for usage in numeric["usages"]}
    facts = {
        usages[fact["usage_id"]]["location"]["line"]: fact for fact in numeric["facts"]
    }
    expected = {
        2: (None, ("0", "0")),
        5: (("0", "10"), ("2", "12")),
        7: (("0", "10"), ("1", "11")),
        9: (("1", "12"), ("1", "12")),
        10: (("11", "12"), ("10", "10")),
        13: (("0", "10"), ("0", "10")),
    }
    assert facts.keys() == expected.keys()
    for line, bounds in expected.items():
        for field, interval in zip(("value_before", "value_after"), bounds):
            value = facts[line][field]
            if interval is None:
                assert value["kind"] == "UNINITIALIZED"
            else:
                assert value["kind"] == "INTERVAL"
                assert (value["lower"], value["upper"]) == interval
    original = Path(__file__).resolve().parents[2]
    assert flow_evidence["value_ranges_stdout"] == (
        original / "examples" / "value_ranges.output.txt"
    ).read_text(encoding="utf-8")
    assert "Complete: true" in flow_evidence["local_usage_stdout"]


@when(
    "I run the recipes with missing or ambiguous selections and unsupported arithmetic",
    target_fixture="failure_evidence",
)
def run_failures(flow_fixture: FlowFixture) -> dict[str, Any]:
    for script, case, options, context in (
        (
            "cfg_stream.ctk",
            "missing-function",
            {"function": "absent"},
            "function definition",
        ),
        (
            "value_ranges.ctk",
            "missing-variable",
            {"variable": "absent"},
            "local declaration",
        ),
    ):
        result, output = _run(flow_fixture, script, case, **options)
        assert result.returncode != 0
        assert context in result.stdout + result.stderr
        assert not output.exists()

    for script, case, source, context in (
        (
            "cfg_stream.ctk",
            "overloads",
            "int score(int n){return n;} int score(double n){return int(n);}",
            "function definition",
        ),
        (
            "local_usage.ctk",
            "shadowed-locals",
            "int score(int n){int total=0;if(n){int total=1;}return total;}",
            "local declaration",
        ),
    ):
        flow_fixture.source.write_text(source, encoding="utf-8")
        result, output = _run(flow_fixture, script, case)
        assert result.returncode != 0
        assert context in result.stdout + result.stderr
        assert not output.exists()

    flow_fixture.source.write_text(
        "int score(){int total=1;total*=2;return total;}", encoding="utf-8"
    )
    result, output = _run(flow_fixture, "value_ranges.ctk", "unsupported")
    assert result.returncode == 0, result.stdout + result.stderr
    return {
        "report": json.loads(output.read_text(encoding="utf-8")),
        "stdout": result.stdout,
    }


@then("failed selections export no report and unsupported ranges remain incomplete")
def verify_failures(failure_evidence: dict[str, Any]) -> None:
    report = failure_evidence["report"]
    assert not report["completed"].get("is_complete", False)
    assert any(
        finding["kind"] == "UNSUPPORTED_EFFECT" for finding in report["findings"]
    )
    assert all(
        fact[field]["kind"] == "UNKNOWN"
        for fact in report["facts"]
        for field in ("value_before", "value_after")
    )
    assert "Complete: false" in failure_evidence["stdout"]
