"""Reuse LALR tables across processes instead of rebuilding them at startup."""

import hashlib
import os
import secrets
import stat
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

import lark
from lark import Lark

_FORMAT = 1
_MAX_ENTRIES = 32


def cache_root() -> Path:
    """Return the per-user cache directory shared by every clang-toolkit cache."""
    configured = os.environ.get("XDG_CACHE_HOME")
    base = Path(configured) if configured and Path(configured).is_absolute() else Path.home() / ".cache"
    return base / "clang-toolkit"


def _entry_path(grammar: str, postlex: Any, options: dict[str, Any]) -> Path:
    """Name the entry after everything that changes the generated tables.

    Lark's own ``cache=`` option is avoided: it hashes the cache path into the
    entry, so an atomic write-then-rename can never be loaded back, and it
    rewrites a damaged entry in place.
    """
    postlex_type = type(postlex)
    identity = repr((
        _FORMAT, sys.version, lark.__version__, grammar, sorted(options.items()),
        postlex_type.__module__, postlex_type.__qualname__,
        getattr(postlex, "always_accept", ()), getattr(postlex, "__dict__", None),
    ))
    return cache_root() / "parsers" / f"{hashlib.sha256(identity.encode()).hexdigest()}.lark"


def _private(info: os.stat_result, kind: Callable[[int], bool]) -> bool:
    """Only trust (pickled) entries that no other user could have written."""
    return kind(info.st_mode) and info.st_uid == os.getuid() and not info.st_mode & 0o022


def _read(path: Path) -> Lark:
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, "rb") as entry:
        if not _private(os.fstat(entry.fileno()), stat.S_ISREG):
            raise ValueError("unsafe parser cache entry")
        return Lark.load(entry)


def _write(path: Path, parser: Lark) -> None:
    temporary = path.with_name(f".{path.name}.{secrets.token_hex(8)}")
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as entry:
            parser.save(entry)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
    entries = []
    for entry_path in path.parent.glob("*.lark"):
        try:
            entries.append((entry_path.lstat().st_mtime_ns, entry_path))
        except OSError:
            continue
    for _, stale in sorted(entries)[:-_MAX_ENTRIES]:
        stale.unlink(missing_ok=True)


def cached_lalr(grammar: str, *, postlex: Any = None, **options: Any) -> Lark:
    """Build a LALR parser, loading its tables from a private disk cache.

    The cache is best effort: a missing home, an unwritable or shared directory,
    or an unreadable, stale or damaged entry all fall back to an ordinary build
    without output. Entries are written under a unique name and published with
    ``os.replace``, so concurrent processes never load a partial file.
    """
    def build() -> Lark:
        return Lark(grammar, parser="lalr", postlex=postlex, **options)

    try:
        path = _entry_path(grammar, postlex, options)
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if not _private(path.parent.lstat(), stat.S_ISDIR):
            return build()
    except (OSError, RuntimeError):
        return build()
    try:
        return _read(path)
    except Exception:  # Pickle can raise nearly anything for an old or damaged entry.
        pass
    parser = build()
    try:
        _write(path, parser)
    except Exception:  # The parser is already usable; only persistence failed.
        pass
    return parser
