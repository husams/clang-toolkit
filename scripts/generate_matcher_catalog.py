#!/usr/bin/env python3
"""Regenerate the offline console matcher catalog from an LLVM installation."""

from __future__ import annotations

import argparse
import subprocess
import tempfile
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import urlopen


REPOSITORY = Path(__file__).resolve().parents[1]
PROBE = REPOSITORY / "server" / "src" / "clang" / "matcher_catalog_probe.cpp"
OUTPUT = (
    REPOSITORY / "python" / "clang_toolkit" / "cli" / "_matcher_catalog_generated.py"
)
REFERENCE_URL = (
    "https://raw.githubusercontent.com/llvm/llvm-project/llvmorg-{version}/"
    "clang/docs/LibASTMatchersReference.html"
)
type MatcherMetadata = tuple[str, str, tuple[str, ...], tuple[str, ...], str]


@dataclass
class ReferenceEntry:
    kind: str
    anchor: str
    signatures: list[str] = field(default_factory=list)
    documentation: list[str] = field(default_factory=list)


class MatcherReferenceParser(HTMLParser):
    """Read categories, overload signatures and documentation from LLVM's tables."""

    def __init__(self) -> None:
        super().__init__()
        self.entries: dict[str, ReferenceEntry] = {}
        self.category = ""
        self.cells: list[str] = []
        self.cell: list[str] | None = None
        self.anchor = ""
        self.name = ""
        self.is_documentation = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "h2":
            self.category = {
                "decl-matchers": "node",
                "narrowing-matchers": "narrowing",
                "traversal-matchers": "traversal",
            }.get(attributes.get("id") or "", "")
        elif tag == "tr":
            self.cells = []
            self.is_documentation = False
        elif tag == "td":
            self.cell = []
            self.is_documentation = attributes.get("class") == "doc"
        elif tag == "a" and (attributes.get("name") or "").endswith("Anchor"):
            self.anchor = attributes["name"] or ""

    def handle_data(self, data: str) -> None:
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "td" and self.cell is not None:
            self.cells.append("".join(self.cell).strip())
            self.cell = None
        elif tag == "tr" and self.category and self.cells:
            if self.is_documentation and self.name:
                entry = self.entries[self.name]
                documentation = entry.documentation
                if self.cells[0] and self.cells[0] not in documentation:
                    if not documentation:
                        entry.anchor = self.anchor
                    documentation.append(self.cells[0])
            elif len(self.cells) == 3:
                returns, self.name, parameters = (
                    " ".join(c.split()) for c in self.cells
                )
                entry = self.entries.setdefault(
                    self.name, ReferenceEntry(self.category, self.anchor)
                )
                signature = f"{returns} {self.name}({parameters})"
                if signature not in entry.signatures:
                    entry.signatures.append(signature)


def matcher_metadata(reference: str, names: list[str]) -> dict[str, MatcherMetadata]:
    """Require source-backed help for every name reachable in the live registry."""
    parsed = MatcherReferenceParser()
    parsed.feed(reference)
    missing = sorted(set(names) - parsed.entries.keys())
    if missing:
        raise ValueError(f"LLVM reference is missing registered matchers: {missing}")
    metadata: dict[str, MatcherMetadata] = {}
    for name in names:
        entry = parsed.entries[name]
        documentation = tuple(entry.documentation)
        if not documentation:
            raise ValueError(f"LLVM reference has no documentation for {name}")
        summary = " ".join(documentation[0].split("\n\n", 1)[0].split())
        metadata[name] = (
            entry.kind,
            summary,
            tuple(entry.signatures),
            documentation,
            entry.anchor,
        )
    return metadata


def run(*command: str) -> str:
    return subprocess.check_output(command, text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llvm-config", default="llvm-config")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument(
        "--reference", type=Path, help="use a saved LLVM reference HTML file"
    )
    args = parser.parse_args()

    llvm_config = args.llvm_config
    version = run(llvm_config, "--version")
    include = run(llvm_config, "--includedir")
    libdir = run(llvm_config, "--libdir")
    bindir = run(llvm_config, "--bindir")
    reference_url = REFERENCE_URL.format(version=version)
    if args.reference is not None:
        reference = args.reference.read_text(encoding="utf-8")
    else:
        with urlopen(reference_url, timeout=30) as response:
            reference = response.read().decode("utf-8")
    documented = MatcherReferenceParser()
    documented.feed(reference)
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
        rows = run(str(executable), *sorted(documented.entries)).splitlines()

    roots = sorted(
        name for name, flag in (row.split("\t") for row in rows) if flag == "1"
    )
    nested = sorted(name for name, _ in (row.split("\t") for row in rows))
    metadata = matcher_metadata(reference, nested)
    content = [
        '"""Generated registry names and LLVM reference help; do not edit directly.\n'
        'Regenerate with scripts/generate_matcher_catalog.py and llvm-config."""',
        f"LLVM_VERSION = {version!r}",
        f"REFERENCE_SOURCE = {reference_url!r}",
        'REFERENCE_URL = "https://clang.llvm.org/docs/LibASTMatchersReference.html"',
        f"ROOT_MATCHERS: tuple[str, ...] = {tuple(roots)!r}",
        f"NESTED_MATCHERS: tuple[str, ...] = {tuple(nested)!r}",
        "# name: (kind, summary, overload signatures, documentation, reference anchor)",
        "MATCHER_METADATA: dict[str, tuple[str, str, tuple[str, ...], tuple[str, ...], str]] = {",
        *(f"    {name!r}: {metadata[name]!r}," for name in nested),
        "}",
        "",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(content), encoding="utf-8")
    print(
        f"Wrote {len(roots)} root and {len(nested)} nested names from LLVM {version} to {args.output}"
    )


if __name__ == "__main__":
    main()
