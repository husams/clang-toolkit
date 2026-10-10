"""Route evaluated values to stdout or a selected file."""

from __future__ import annotations

from pathlib import Path
from typing import TextIO

import os
import tempfile


class OutputError(OSError):
    """The selected output destination could not be used."""


def write_text(path: Path, text: str, *, append: bool = False) -> None:
    """Write one print result; replacement publishes a complete sibling file."""
    temporary: str | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if append:
            with path.open("a", encoding="utf-8") as handle:
                handle.write(text + "\n")
            return
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as handle:
            temporary = handle.name
            handle.write(text + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        raise OutputError(f"cannot write output {path}: {exc}") from exc
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


class OutputSink:
    def __init__(self, cwd: Path, destination: str = "stdout") -> None:
        self.cwd = cwd
        self.destination = "stdout"
        self._handle: TextIO | None = None
        self._output_limit: int | None = None
        self._output_count = 0
        self._last_output_count = 0
        self.emission_count = 0
        self.configure(destination)

    def begin_limited_output(self, maximum: int) -> None:
        self._output_limit = maximum
        self._output_count = 0

    def end_limited_output(self) -> int:
        self._last_output_count = self._output_count
        self._output_limit = None
        self._output_count = 0
        return self._last_output_count

    def check_output(self, text: str) -> None:
        if self._output_limit is None:
            return
        if self._output_count + len(text) > self._output_limit:
            raise OutputError(
                f"batch output exceeds {self._output_limit} characters for one group"
            )
        self._output_count += len(text)

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
        self.check_output(text)
        if self._output_limit is not None:
            self.emission_count += 1
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
