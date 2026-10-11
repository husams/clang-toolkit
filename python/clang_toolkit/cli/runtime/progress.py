"""Immutable presentation events; progress never changes batch execution."""

from __future__ import annotations

from dataclasses import dataclass

from clang_toolkit.batches import BatchRun


@dataclass(frozen=True)
class BatchProgress:
    run_id: str
    total: int
    done: int = 0
    succeeded: int = 0
    failed: int = 0
    state: str = "running"
    durable: bool = False
    skipped: int = 0
    revision: int = 0

    @property
    def active(self) -> bool:
        return self.state in {"queued", "running"}

    def label(self, width: int = 24) -> str:
        done = min(self.total, max(0, self.done))
        filled = width * done // self.total if self.total else (width if not self.active else 0)
        return (
            f"Batch {self.run_id} {done}/{self.total} files · {self.state} "
            f"[{('━' * filled).ljust(width, '─')}] · "
            f"{self.succeeded} succeeded · {self.failed} failed"
            + (f" · {self.skipped} skipped" if self.skipped else "")
            + (" · [Cancel]" if self.active else "")
        )


def durable_progress(run: BatchRun) -> BatchProgress:
    """Durable counters use frozen group inputs, never current discovery."""
    groups = run.groups
    succeeded = sum(len(group.inputs) for group in groups if group.state == "completed")
    failed = sum(len(group.inputs) for group in groups if group.state == "failed")
    return BatchProgress(
        run.run_id, sum(len(group.inputs) for group in groups), succeeded + failed,
        succeeded, failed, run.status, True,
        sum(len(group.inputs) for group in groups if group.state in {"cancelled", "unknown"}),
        run.revision,
    )
