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

    print(f"validated {len(expected)} concrete node serializers and payloads")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
