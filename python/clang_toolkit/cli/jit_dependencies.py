"""Filesystem observations for the generated CTK translation unit."""

from __future__ import annotations

import os
from pathlib import Path
import re

_MAX_OBSERVATIONS = 16384
_INCLUDE_START = '#include "..." search starts here:\n'
_INCLUDE_END = "\nEnd of search list."


def identity(path: Path) -> tuple[int, ...]:
    status = path.stat()
    return (
        status.st_dev,
        status.st_ino,
        status.st_size,
        status.st_mtime_ns,
        status.st_ctime_ns,
    )


def _stamp(path: Path) -> list[int] | None:
    try:
        return list(identity(path))
    except (FileNotFoundError, NotADirectoryError):
        return None


def unchanged(observed: object) -> bool:
    if not isinstance(observed, dict) or not observed:
        return False
    return all(_stamp(Path(path)) == stamp for path, stamp in observed.items())


def _dep_paths(depfile: str) -> set[Path]:
    target, separator, body = depfile.partition(":")
    if target != "ctk-jit" or not separator:
        return set()
    body = body.replace("\\\n", " ")
    return {
        Path(re.sub(r"\\(.)|\$\$", lambda match: match[1] or "$", token)).absolute()
        for token in re.findall(r"(?:\\.|[^\s\\])+", body)
    }


def _raise_walk_error(error: OSError) -> None:
    raise error


def observe(
    depfile: str, diagnostics: str, started_ns: int
) -> dict[str, list[int] | None] | None:
    """Record used files and include namespaces, or decline the fast path."""
    _, start, search = diagnostics.partition(_INCLUDE_START)
    roots, end, _ = search.partition(_INCLUDE_END)
    headers = _dep_paths(depfile)
    if not start or not end or not headers or "[-Wdate-time]" in diagnostics:
        return None
    directories = {
        Path(line.strip().removesuffix(" (framework directory)")).absolute()
        for line in roots.splitlines()
        if line.strip() and not line.startswith("#include")
    }
    if not directories:
        return None
    missing = re.findall(r'^ignoring nonexistent directory "(.*)"$', diagnostics, re.M)
    duplicates = re.findall(r'^ignoring duplicate directory "(.*)"$', diagnostics, re.M)
    observed: dict[str, list[int] | None] = {}
    visited: set[tuple[int, ...]] = set()

    def record(path: Path) -> list[int] | None:
        name = str(path)
        if name not in observed:
            stamp = _stamp(path)
            if len(observed) >= _MAX_OBSERVATIONS or (
                stamp is not None and stamp[-1] >= started_ns
            ):
                raise ValueError(
                    "include inputs changed or exceeded the observation limit"
                )
            observed[name] = stamp
        return observed[name]

    try:
        for name in missing:
            if record(Path(name).absolute()) is not None:
                return None
        for name in duplicates:
            if record(Path(name).absolute()) is None:
                return None
        physical_roots = {path.resolve() for path in directories}
        for header in headers:
            if record(header) is None:
                return None
            record(header.parent)
            parent = header.parent.resolve()
            if not any(parent.is_relative_to(root) for root in physical_roots):
                directories.add(header.parent)
        for root in directories:
            if record(root) is None:
                return None
            for directory, children, files in os.walk(
                root, onerror=_raise_walk_error, followlinks=True
            ):
                path = Path(directory)
                stamp = record(path)
                if stamp is None:
                    return None
                unique = tuple(stamp[:2])
                if unique in visited:
                    children.clear()
                    continue
                visited.add(unique)
                # A dangling symlink can begin resolving without a directory edit.
                for name in files:
                    candidate = path / name
                    if candidate.is_symlink():
                        record(candidate)
    except (OSError, ValueError):
        return None
    return observed
