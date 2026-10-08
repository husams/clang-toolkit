"""Session-tagged, user-only command history."""

from __future__ import annotations

import json
import os
import shutil
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID


class HistoryError(OSError):
    """Command history could not be saved or exported."""


class HistoryStore:
    def __init__(self, path: Path | None = None) -> None:
        state_root = Path(
            os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state")
        )
        self.path = path or state_root / "clang_tools/history.jsonl"
        self._clear_listeners: list[Callable[[], None]] = []

    def read_commands(self) -> list[str]:
        """Read valid command records in file order, skipping damaged lines."""
        try:
            lines = self.path.read_text(encoding="utf-8").split("\n")
        except FileNotFoundError:
            return []
        except (OSError, UnicodeError) as exc:
            raise HistoryError(f"cannot read history: {exc}") from exc

        commands: list[str] = []
        for line in lines:
            try:
                record = json.loads(line)
            except (json.JSONDecodeError, TypeError):
                continue
            command = record.get("command") if isinstance(record, dict) else None
            if isinstance(command, str) and command.strip():
                commands.append(command)
        return commands

    def add_clear_listener(self, listener: Callable[[], None]) -> None:
        """Register an in-memory history view to clear with the persistent log."""
        self._clear_listeners.append(listener)

    def append(self, command: str, session_id: UUID, label: str | None) -> None:
        if not command.strip():
            return
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": str(session_id),
            "label": label,
            "command": command,
        }
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(
                self.path, os.O_RDWR | os.O_CREAT | os.O_APPEND, 0o600
            )
            try:
                end = os.lseek(descriptor, 0, os.SEEK_END)
                separator = b""
                if end:
                    os.lseek(descriptor, -1, os.SEEK_END)
                    if os.read(descriptor, 1) != b"\n":
                        separator = b"\n"
                payload = (
                    separator
                    + json.dumps(record, ensure_ascii=False).encode("utf-8")
                    + b"\n"
                )
                written = os.write(descriptor, payload)
                if written != len(payload):
                    raise OSError(
                        f"short history write: {written} of {len(payload)} bytes"
                    )
            finally:
                os.close(descriptor)
        except OSError as exc:
            raise HistoryError(f"cannot append history: {exc}") from exc

    def save(self, destination: Path) -> None:
        try:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(self.path, destination)
        except OSError as exc:
            raise HistoryError(f"cannot export history: {exc}") from exc

    def clear(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text("")
            for listener in tuple(self._clear_listeners):
                listener()
            self.path.chmod(0o600)
        except OSError as exc:
            raise HistoryError(f"cannot clear history: {exc}") from exc
