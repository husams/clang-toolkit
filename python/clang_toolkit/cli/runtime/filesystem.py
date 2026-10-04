"""Typed snapshots of files and directories returned by ``glob``."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class FileSystemEntry:
    path: str
    absolute: str
    size: int
    modified: datetime

    @property
    def basename(self) -> str:
        return Path(self.path).name

    @property
    def dirname(self) -> str:
        return Path(self.path).parent.as_posix()

    @property
    def parts(self) -> list[str]:
        return list(Path(self.path).parts)

    def __str__(self) -> str:
        return self.path


@dataclass(frozen=True)
class File(FileSystemEntry):
    """A file and its metadata as observed when the glob ran."""


@dataclass(frozen=True)
class Directory(FileSystemEntry):
    """A directory; size is its filesystem entry size, not recursive contents."""


def from_path(path: Path, cwd: Path) -> FileSystemEntry | None:
    """Snapshot a glob result, omitting non-filesystem and vanished entries."""
    resolved = path.resolve()
    try:
        metadata = resolved.stat()
    except OSError:
        return None
    kind: type[FileSystemEntry]
    if resolved.is_file():
        kind = File
    elif resolved.is_dir():
        kind = Directory
    else:
        return None
    display = path.relative_to(cwd).as_posix()
    return kind(
        path=display,
        absolute=str(resolved),
        size=metadata.st_size,
        modified=datetime.fromtimestamp(metadata.st_mtime, tz=timezone.utc),
    )
