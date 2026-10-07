#!/usr/bin/env python3
"""Check concrete Clang serializer classes against the versioned AST catalog."""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]


def field_name(name: str) -> str:
    value = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", value).lower()


def main() -> int:
    catalog = json.loads((ROOT / "api/catalog.json").read_text())
    tags = json.loads((ROOT / "api/node_tags.json").read_text())["tags"]
    expected = {
        entry["name"]: field_name(entry["name"])
        for entry in catalog["classes"]
        if entry["status"] == "included"
    }
    if set(expected) != set(tags):
        print("AST schema catalog and stable node tags disagree", file=sys.stderr)
        return 1

    source = (ROOT / "server/src/clang/serialization/"
              "node_serializer_catalog.inc").read_text()
    actual = {
        name: field
        for name, field in re.findall(r"CTK_AST_NODE\((\w+),\s*(\w+)\)", source)
    }
    if actual != expected:
        missing = sorted(set(expected) - set(actual))
        extra = sorted(set(actual) - set(expected))
        wrong = sorted(name for name in set(actual) & set(expected)
                       if actual[name] != expected[name])
        print(f"serializer coverage mismatch: missing={missing}, extra={extra}, "
              f"wrong_payload={wrong}", file=sys.stderr)
        return 1

    node_proto = (ROOT / "api/ast/v1/node.proto").read_text()
    node_union = node_proto.split("\nenum UnsupportedReason", 1)[0]
    payloads = dict(re.findall(
        r"^\s*(\w+)\s+(\w+)\s*=\s*\d+;", node_union, re.MULTILINE))
    if payloads != expected:
        print("AST node payload fields do not match serializer mappings",
              file=sys.stderr)
        return 1

    directory = ROOT / "server/src/clang/serialization"
    shared = {"DeclInfo", "NamedDeclInfo", "ValueDeclInfo", "DeclaratorDeclInfo",
              "FunctionDeclInfo", "CXXMethodDeclInfo", "VarDeclInfo", "TypeDeclInfo",
              "TagDeclInfo", "RecordDeclInfo", "ExprInfo", "TypeInfo"}
    fields = 0
    failures = []
    for entry in catalog["classes"]:
        if entry["status"] != "included":
            continue
        name, family = entry["name"], entry["family"]
        stem = directory / family / field_name(name)
        header, source_path = stem.with_suffix(".hpp"), stem.with_suffix(".cpp")
        if not header.is_file() or not source_path.is_file():
            failures.append(f"{name}: dedicated source/header missing")
            continue
        declaration, implementation = header.read_text(), source_path.read_text()
        if not re.search(rf"class\s+{name}Serializer\s+final\s*:\s*public\s+NodeSerializer", declaration):
            failures.append(f"{name}: dedicated serializer class missing")
        if not re.search(rf"bool\s+{name}Serializer::serialize\s*\(", implementation):
            failures.append(f"{name}: dedicated field extraction definition missing")
        if f"mutable_{field_name(name)}()" not in implementation:
            failures.append(f"{name}: incorrect concrete payload selection")
        proto = (ROOT / "api" / entry["protobuf_file"]).read_text()
        declared_fields = re.findall(
            r"^\s*(?:(?:optional|repeated)\s+)?(\w+)\s+(\w+)\s*=\s*\d+;",
            proto, re.MULTILINE)
        for message_type, field in declared_fields:
            fields += 1
            direct = re.search(rf"(?:mutable_|set_|add_){field}\s*\(", implementation)
            common = message_type in shared and "helpers::write_common(" in implementation
            unavailable = re.search(rf'"(?:[^"\n]*\.)?{field}"', implementation) and "unavailable(" in implementation
            if not (direct or common or unavailable):
                failures.append(f"{name}.{field}: no field extraction or availability evidence")
    if failures:
        print("\n".join(failures), file=sys.stderr)
        return 1
    print(f"validated {len(expected)} dedicated concrete serializers and {fields} payload field extraction paths")
    print("This source gate checks mapping/extraction evidence; native fixtures verify values and presence.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
