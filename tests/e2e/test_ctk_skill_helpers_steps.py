"""Verify bundled skill utilities through the real compiled console and native server."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, scenarios, then, when

from tests.e2e.test_network_steps import RunningServer, _launch_server

pytestmark = pytest.mark.e2e
scenarios("ctk_skill_helpers.feature")

HelperFixture = tuple[RunningServer, Path, Path, Path]


@given("an isolated server and the bundled CTK helper fixture", target_fixture="helper_fixture")
def helper_fixture(tmp_path: Path, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> HelperFixture:
    monkeypatch.setenv("CTK_STORAGE_ROOT", str(tmp_path / "native-storage"))
    server = _launch_server("unix", tmp_path, request)
    skill = Path(__file__).resolve().parents[2] / "skills" / "ctk-script"
    source = tmp_path / "helpers.cc"
    source.write_text((skill / "assets" / "utility_fixture.cc").read_text(encoding="utf-8"), encoding="utf-8")
    return server, skill, source, tmp_path


def _run(fixture: HelperFixture, source: str, engine: str = "compiled") -> dict[str, Any]:
    server, skill, target, directory = fixture
    script = directory / "verify.ctk"
    output = directory / "output.json"
    script.write_text(f'import {json.dumps(str(skill / "scripts" / "ctk_helpers.ctk"))}\n' + source, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-m", "clang_toolkit.cli.app", "--server", server.endpoint,
         "-c", str(server.config), "--script-engine", engine, "--ui", "prompt",
         "--script", str(script), f"path={target}", f"output={output}"],
        cwd=directory,
        env=dict(os.environ, XDG_STATE_HOME=str(directory / "state")),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=90, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == ["HELPERS_VERIFIED"]
    assert result.stderr == ""
    assert server.process.poll() is None
    return json.loads(output.read_text(encoding="utf-8"))


@when("I query structured classes and inheritance with the imported helpers", target_fixture="class_evidence")
def class_evidence(helper_fixture: HelperFixture) -> dict[str, Any]:
    return _run(helper_fixture, '''
let tree = parse arg.path
let info = classInfo(tree, "demo::Leaf")
let root = classInfo(tree, "demo::Root")
let right = classInfo(tree, "demo::Right")
let implicit = classInfo(tree, "demo::Solo", true)
let hierarchy = ancestors(tree, "demo::Leaf")
let bounded = ancestors(tree, "demo::Leaf", 1)
let zero = ancestors(tree, "demo::Leaf", 0)
let leaf = ancestors(tree, "demo::Solo", 0)
let leafFull = ancestors(tree, "demo::Solo")
let dependent = ancestors(tree, "demo::Dependent")
let ambiguous = classInfo(tree, "Solo")
let missing = ancestors(tree, "demo::Missing")
let missingInfo = classInfo(tree, "demo::Missing")
let invalid = ancestors(tree, "demo::Leaf", -1)
save {info: info, root: root, right: right, implicit: implicit, hierarchy: hierarchy, bounded: bounded, zero: zero, leaf: leaf, leaf_full: leafFull, dependent: dependent, ambiguous: ambiguous, missing: missing, missing_info: missingInfo, invalid: invalid} to arg.output as json
print "HELPERS_VERIFIED"
''')


@then("the summaries preserve members and paths and expose incomplete or ambiguous results")
def verify_classes(class_evidence: dict[str, Any]) -> None:
    v = class_evidence
    info = v["info"]
    assert info["status"] == "ok"
    assert info["class"]["name"] == "demo::Leaf"
    assert [(f["name"], f["access"]) for f in info["fields"]] == [
        ("demo::Leaf::shield", "protected"), ("demo::Leaf::hidden", "private"),
    ]
    assert info["fields"][1]["mutable"] is True
    assert [c["name"] for c in info["nested_classes"]] == ["demo::Leaf::Nested"]
    methods = info["methods"]
    assert len(methods) == 7
    assert {m["access"] for m in methods} == {"public"}
    assert {m["kind"] for m in methods} == {"method", "constructor", "destructor", "conversion"}
    assert not any(m["implicit"] for m in methods)
    overloads = [m for m in methods if m["name"] == "demo::Leaf::run"]
    assert len({m["id"] for m in overloads}) == 2
    assert [m["parameters"][0]["type"] for m in overloads] == ["int", "double"]
    assert all(len(m["parameters"]) == 1 for m in overloads)  # Nested lambda parameters stay out.
    assert overloads[0]["const"] and overloads[0]["virtual"] and overloads[0]["override_written"]
    assert next(m for m in methods if m["name"] == "demo::Leaf::utility")["static"]
    assert next(m for m in methods if m["name"] == "demo::Leaf::identity")["parameters"][0]["type"] == "T"
    root = v["root"]
    assert {f["access"] for f in root["fields"]} == {"public", "protected", "private"}
    assert next(f for f in root["fields"] if f["name"].endswith("::bits"))["bit_field"]
    assert {m["access"] for m in root["methods"]} == {"public", "protected", "private"}
    run = next(m for m in root["methods"] if m["name"].endswith("::run"))
    assert run["pure"] and run["parameters"][0]["has_default"]
    assert v["right"]["static_fields"][0]["name"] == "demo::Right::count"
    assert v["right"]["static_fields"][0]["access"] == "public"
    assert any(m["implicit"] for m in v["implicit"]["methods"])
    hierarchy = v["hierarchy"]
    assert hierarchy["complete"]
    assert [[n["name"] for n in level] for level in hierarchy["levels"]] == [
        ["demo::Left", "demo::Right"], ["demo::Root", "demo::Root"],
    ]
    assert all(n["id"] != hierarchy["tree"]["id"] for level in hierarchy["levels"] for n in level)
    left, right = hierarchy["tree"]["bases"]
    assert left["edge"]["type"] == "LeftAlias" and left["edge"]["access"] == "public"
    assert right["edge"]["access"] == "private"
    assert left["bases"][0]["edge"]["virtual"]
    assert right["bases"][0]["edge"]["access"] == "protected"
    assert left["bases"][0]["id"] == right["bases"][0]["id"]
    assert not v["bounded"]["complete"]
    assert [[n["name"] for n in level] for level in v["bounded"]["levels"]] == [["demo::Left", "demo::Right"]]
    assert all(node["truncated"] for node in v["bounded"]["tree"]["bases"])
    assert v["zero"]["tree"]["truncated"] and v["zero"]["tree"]["bases"] == []
    assert v["leaf"]["complete"] and v["leaf"]["tree"]["bases"] == []
    assert v["zero"]["levels"] == []
    assert v["leaf"]["levels"] == v["leaf_full"]["levels"] == []
    assert v["leaf_full"]["complete"]
    dependent = v["dependent"]
    assert not dependent["complete"]
    assert [[n["name"] for n in level] for level in dependent["levels"]] == [["Base"]]
    assert dependent["tree"]["bases"][0]["unresolved"]
    assert dependent["tree"]["bases"][0]["edge"]["class"] is None
    assert v["ambiguous"]["status"] == "ambiguous" and len(v["ambiguous"]["candidates"]) == 2
    assert v["missing"] == v["missing_info"] == {"status": "not_found", "candidates": []}
    assert v["invalid"] == {"status": "invalid_depth"}


@when("I use the ready-made matchers and named and inline callbacks", target_fixture="callback_evidence")
def callback_evidence(helper_fixture: HelperFixture) -> dict[str, Any]:
    return _run(helper_fixture, '''
let tree = parse arg.path
let classes = match definedClass("demo::Leaf").bind("cls") in tree
let functions = match definedFunction("demo::work").bind("fn") in tree
let methods = match methodsOfClass("demo::Leaf").bind("method") in tree
let publicMethods = match publicMethodsOfClass("demo::Leaf").bind("method") in tree
let fields = match fieldsOfClass("demo::Root").bind("field") in tree
let derived = match derivedFrom("demo::Root").bind("cls") in tree
let calls = match callsTo("demo::sink").bind("call") in tree
let summaries = functionInfo(tree, "demo::work")
let sites = callSites(tree, "demo::sink")
let doubled = mapValues([1, 2, 3], (value) = value * 2)
let selected = filterValues(doubled, (value) = value > 2)
let safe = mapValues([2, 0, 5], (value) = { on error 0; 10 / value })
let events = []
let cleaned = mapValues([2, 0], (value) = { on error 0; on exit { push events, value }; 10 / value })
let add(lhs, rhs = 1) = lhs + rhs
let apply(operation, value) = operation(value)
let makeAdder(base) = (value, extra = base) = value + extra
let addTen = makeAdder(10)
let run(operation) = operation()
let inlineDefault = apply((value, extra = value) = value + extra, 3)
let zero = run(() = 42)
save {counts: [classes.length, functions.length, methods.length, publicMethods.length, fields.length, derived.length, calls.length], functions: summaries, calls: sites, selected: selected, safe: safe, cleaned: cleaned, events: events, defaults: mapValues([1, 2], add), inline_default: inlineDefault, closure: addTen(5), zero: zero} to arg.output as json
print "HELPERS_VERIFIED"
''')


@then("the documented matchers and executable-block examples return the expected values")
def verify_callbacks(callback_evidence: dict[str, Any]) -> None:
    v = callback_evidence
    assert v["counts"] == [1, 1, 7, 7, 3, 3, 1]
    assert v["selected"] == [4, 6]
    assert v["safe"] == [5.0, 0, 2.0]
    assert v["cleaned"] == [5.0, 0] and v["events"] == [2, 0]
    assert v["defaults"] == [2, 3]
    assert v["inline_default"] == 6 and v["closure"] == 15 and v["zero"] == 42
    assert v["functions"][0]["name"] == "demo::work"
    assert v["functions"][0]["parameters"][0]["has_default"]
    assert v["calls"][0]["caller"] == "demo::work"
    assert v["calls"][0]["callee"] == "demo::sink"
    assert v["calls"][0]["dispatch"] == "CALL_DISPATCH_DIRECT"


@given("an isolated server and the bundled CTK template fixture", target_fixture="template_fixture")
def template_fixture(tmp_path: Path, request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch) -> HelperFixture:
    fixture = helper_fixture(tmp_path, request, monkeypatch)
    _, skill, source, _ = fixture
    source.write_text((skill / "assets" / "template_fixture.cc").read_text(encoding="utf-8"), encoding="utf-8")
    return fixture


@when("I select live classes and inspect their template specializations in both engines", target_fixture="template_evidence")
def template_evidence(template_fixture: HelperFixture) -> list[dict[str, Any]]:
    script = '''
let tree = parse arg.path
let leaf = classByName(tree, "demo::Leaf")
let byFile = classByName(arg.path, "demo::Leaf")
let byNode = classByName(leaf, "demo::Leaf")
let primary = classByName(tree, "demo::Box")
let templates = classTemplateInfo(tree, "demo::Box")
let explicit = classByName(tree, "demo::Box<double, 3>")
let instantiated = classByName(tree, "demo::Box<int, 3>")
let partial = classByName(tree, "demo::Box<int *, 3>")
let fullInfo = classInfo(tree, "demo::Box<double, 3>")
let hierarchy = ancestors(tree, "demo::Leaf")
let partialHierarchy = ancestors(tree, "demo::PartialLeaf")
let fullHierarchy = ancestors(tree, "demo::FullLeaf")
let missing() = { on error "missing"; classByName(tree, "demo::Absent") }
let ambiguous() = { on error "ambiguous"; classByName(tree, "Duplicate") }
save {identity: [leaf.symbol_identity, byFile.symbol_identity, byNode.symbol_identity], methods: classMethods(primary), explicit_fields: classFields(explicit), instantiated_fields: classFields(instantiated), partial_fields: classFields(partial), full_info: fullInfo, templates: templates, pack: classTemplateInfo(tree, "demo::Pack"), wrapper: classTemplateInfo(tree, "demo::Wrapper"), ordinary: classTemplateInfo(tree, "demo::Ordinary"), hierarchy: hierarchy, partial_hierarchy: partialHierarchy, full_hierarchy: fullHierarchy, missing: missing(), ambiguous: ambiguous()} to arg.output as json
print "HELPERS_VERIFIED"
'''
    return [_run(template_fixture, script, engine) for engine in ("compiled", "tree")]


@then("the live nodes and template summaries preserve specialization identity and complete ancestors")
def verify_templates(template_evidence: list[dict[str, Any]]) -> None:
    assert template_evidence[0] == template_evidence[1]
    v = template_evidence[0]
    assert len(set(v["identity"])) == 1
    assert [m["name"] for m in v["methods"]] == ["demo::Box::work"]
    assert v["explicit_fields"][0]["type"] == "double"
    assert v["instantiated_fields"][0]["type"] == "int"
    assert v["partial_fields"][0]["type"] == "int *"
    assert v["full_info"]["class"]["template"]["kind"] == "specialization"
    template = v["templates"]["template"]
    assert template["kind"] == "primary" and template["primary"] == "demo::Box"
    assert [(p["name"], p["type"], p["pack"]) for p in template["parameters"]] == [("T", None, False), ("N", "int", False)]
    variants = v["templates"]["specializations"]
    assert len({item["id"] for item in variants}) == 5
    assert any(item["template"]["kind"] == "partial_specialization" for item in variants)
    assert {item["template"]["specialization_kind"] for item in variants} == {"DECL_TEMPLATE_SPECIALIZATION_KIND_EXPLICIT_SPECIALIZATION", "DECL_TEMPLATE_SPECIALIZATION_KIND_IMPLICIT_INSTANTIATION"}
    for key, spelling in (("hierarchy", "demo::Box<int, 3>"), ("partial_hierarchy", "demo::Box<int *, 3>"), ("full_hierarchy", "demo::Box<double, 3>")):
        hierarchy = v[key]
        assert hierarchy["complete"]
        assert hierarchy["levels"][0][0]["display_name"] == spelling
        assert hierarchy["levels"][1][0]["name"] == "demo::Root"
        assert hierarchy["tree"]["bases"][0]["kind"] == "TAG_KIND_STRUCT"
    assert v["pack"]["template"]["parameters"][0]["pack"]
    elements = v["pack"]["specializations"][0]["template"]["arguments"][0]["elements"]
    assert [element["type"] for element in elements] == ["int", "double"]
    assert v["wrapper"]["template"]["parameters"][0]["parameters"][0]["pack"]
    assert v["ordinary"]["status"] == "not_template"
    assert v["missing"] == "missing" and v["ambiguous"] == "ambiguous"
