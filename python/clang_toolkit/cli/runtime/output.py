"""Route evaluated values to stdout or a selected file."""

from __future__ import annotations

from pathlib import Path
from typing import TextIO


class OutputError(OSError):
    """The selected output destination could not be used."""


class OutputSink:
    def __init__(self, cwd: Path, destination: str = "stdout") -> None:
        self.cwd = cwd
        self.destination = "stdout"
        self._handle: TextIO | None = None
        self.configure(destination)

    def configure(self, destination: str, *, replace: bool = False) -> None:
        new_handle: TextIO | None = None
        if destination != "stdout":
            path = Path(destination)
            path = path if path.is_absolute() else self.cwd / path
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                new_handle = path.open("w" if replace else "a", encoding="utf-8")
            except OSError as exc:
                raise OutputError(f"cannot open output {path}: {exc}") from exc
        old_handle = self._handle
        self._handle = new_handle
        self.destination = destination
        if old_handle is not None:
            old_handle.close()

    def emit(self, text: str) -> str:
        if self._handle is None:
            return text
        try:
            self._handle.write(text + "\n")
            self._handle.flush()
        except OSError as exc:
            raise OutputError(f"cannot write output {self.destination}: {exc}") from exc
        return ""

    def close(self) -> None:
        if self._handle is not None:
            self._handle.close()
            self._handle = None
