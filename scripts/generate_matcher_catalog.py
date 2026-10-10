#!/usr/bin/env python3
"""Regenerate the offline console matcher catalog from an LLVM installation."""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[1]
PROBE = REPOSITORY / "server" / "src" / "clang" / "matcher_catalog_probe.cpp"
OUTPUT = REPOSITORY / "python" / "clang_toolkit" / "cli" / "_matcher_catalog_generated.py"


def run(*command: str) -> str:
    return subprocess.check_output(command, text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llvm-config", default="llvm-config")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    llvm_config = args.llvm_config
    version = run(llvm_config, "--version")
    include = run(llvm_config, "--includedir")
    libdir = run(llvm_config, "--libdir")
    bindir = run(llvm_config, "--bindir")
    with tempfile.TemporaryDirectory(prefix="ctk-matcher-catalog-") as temp_dir:
        executable = Path(temp_dir) / "matcher-catalog"
        command = [
            str(Path(bindir) / "clang++"),
            "-std=c++20",
            f"-I{include}",
            str(PROBE),
            f"-L{libdir}",
            f"-Wl,-rpath,{libdir}",
            "-lclang-cpp",
            "-lLLVM",
            "-o",
            str(executable),
        ]
        subprocess.run(command, check=True)
        rows = run(str(executable)).splitlines()

    roots = sorted(name for name, flag in (row.split("\t") for row in rows) if flag == "1")
    nested = sorted(name for name, _ in (row.split("\t") for row in rows))
    content = [
        '"""Generated reachable registry completion names; do not edit directly.\n'
        'Regenerate with scripts/generate_matcher_catalog.py and llvm-config."""',
        f'LLVM_VERSION = {version!r}',
        f"ROOT_MATCHERS: tuple[str, ...] = {tuple(roots)!r}",
        f"NESTED_MATCHERS: tuple[str, ...] = {tuple(nested)!r}",
        "",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(content), encoding="utf-8")
    print(f"Wrote {len(roots)} root and {len(nested)} nested names from LLVM {version} to {args.output}")


if __name__ == "__main__":
    main()
