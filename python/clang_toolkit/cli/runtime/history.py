"""Session-tagged, user-only command history."""

from __future__ import annotations

import json
import os
import shutil
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
                self.path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600
            )
            with os.fdopen(descriptor, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
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
            self.path.chmod(0o600)
        except OSError as exc:
            raise HistoryError(f"cannot clear history: {exc}") from exc
