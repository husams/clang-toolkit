"""Programmatic client used by the CLI, scripts and AI agents."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Client:
    address: str = "127.0.0.1:7878"

    def match(self, matcher: str, *, files: list[str] | None = None) -> list[str]:
        """Run a matcher over the active project or an explicit file selection."""
        del matcher, files
        raise NotImplementedError("transport (gRPC/REST) not wired yet")

    def cfg(self, function: str) -> str:
        raise NotImplementedError("transport (gRPC/REST) not wired yet")

    def callgraph(self) -> str:
        raise NotImplementedError("transport (gRPC/REST) not wired yet")
