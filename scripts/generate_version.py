"""Capture immutable build identity for native and Python distributions."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess
import tomllib


def build_version(root: Path) -> dict[str, str]:
    version = tomllib.loads((root / "pyproject.toml").read_text())["project"]["version"]
    revision = "unknown"
    if (root / ".git").exists():
        result = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"], cwd=root,
            capture_output=True, text=True, check=False,
        )
        if result.returncode == 0 and re.fullmatch(r"[0-9a-f]{12,40}", result.stdout.strip()):
            revision = result.stdout.strip()
    else:
        stamp = root / "python/clang_toolkit/_build_version.json"
        if stamp.is_file():
            revision = json.loads(stamp.read_text()).get("revision", "unknown")
    return {"version": version, "revision": revision}


def write_if_changed(path: Path, text: str) -> None:
    if not path.is_file() or path.read_text() != text:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cpp", type=Path, required=True)
    args = parser.parse_args()
    info = build_version(Path(__file__).resolve().parents[1])
    write_if_changed(args.cpp, '#pragma once\n#include <string_view>\n'
        'namespace ctk::build {\n'
        f'inline constexpr std::string_view version = {json.dumps(info["version"])};\n'
        f'inline constexpr std::string_view revision = {json.dumps(info["revision"])};\n'
        '}\n')


if __name__ == "__main__":
    main()
