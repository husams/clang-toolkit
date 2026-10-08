"""Print the functions defined in one source file using a server-side ctk script.

usage: uv run python function_names.py <source-file> [compile_commands.json]
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from google.protobuf.json_format import MessageToDict

from clang_toolkit.client import Client

SCRIPT = Path(__file__).with_name("function_names.ctks").read_text()


def declared_name(node: Any) -> str | None:
    """Return the first `named.qualified_name` found in a serialized declaration."""
    if isinstance(node, dict):
        named = node.get("named")
        if isinstance(named, dict) and "qualified_name" in named:
            return named["qualified_name"]
        for value in node.values():
            if (found := declared_name(value)) is not None:
                return found
    elif isinstance(node, list):
        for value in node:
            if (found := declared_name(value)) is not None:
                return found
    return None


def main(source: str, database: str = "build/dev/compile_commands.json") -> None:
    client = Client(None, compilation_database=str(Path(database).resolve()))
    response = client.run_script(SCRIPT, path=str(Path(source).resolve()),
                                 working_directory=Path.cwd())
    for emission in MessageToDict(response, preserving_proto_field_name=True)["emissions"]:
        if emission.get("name") != "fns":
            continue
        for row in emission["value"]["matches"].get("rows", []):
            print(declared_name(row["bindings"]["fn"]))


if __name__ == "__main__":
    main(*sys.argv[1:])
