"""Thread-safe printing bridge for the workspace's bounded transcript."""

from __future__ import annotations

from collections.abc import Callable
from io import TextIOBase
from threading import Lock

MAX_TRANSCRIPT_CHARS = 200_000


class WorkspaceOutput(TextIOBase):
    encoding = "utf-8"

    def __init__(self, publish: Callable[[str], None]) -> None:
        self.publish = publish
        self.pending = ""
        self.lock = Lock()

    def writable(self) -> bool:
        return True

    def write(self, text: str) -> int:
        with self.lock:
            self.pending += text
            while "\n" in self.pending:
                line, self.pending = self.pending.split("\n", 1)
                self.publish(line)
            if len(self.pending) > MAX_TRANSCRIPT_CHARS:
                self.publish(self.pending[-MAX_TRANSCRIPT_CHARS:])
                self.pending = ""
        return len(text)

    def flush(self) -> None:
        with self.lock:
            if self.pending:
                self.publish(self.pending)
                self.pending = ""
