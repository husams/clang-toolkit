"""Programmatic client used by the CLI, scripts and AI agents."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Client:
    address: str = "127.0.0.1:7878"

    def match(self, matcher: str) -> list[str]:
        raise NotImplementedError("transport (gRPC/REST) not wired yet")

    def cfg(self, function: str) -> str:
        raise NotImplementedError("transport (gRPC/REST) not wired yet")

    def callgraph(self) -> str:
        raise NotImplementedError("transport (gRPC/REST) not wired yet")
