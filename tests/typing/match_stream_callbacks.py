"""Static typing examples for synchronous and asynchronous row callbacks."""

from __future__ import annotations

from clang_toolkit import AsyncClient, Client
from clang_toolkit._generated.match.v1.match_result_pb2 import MatchResult


def consume_sync(path: str) -> None:
    rows: list[MatchResult] = []

    def on_row(value: MatchResult) -> None:
        rows.append(value)

    with Client() as client:
        matches = client.match_in("functionDecl().bind('function')", path, on_row=on_row)
        assert len(rows) == len(matches)


async def consume_async(path: str) -> None:
    rows: list[MatchResult] = []

    async def on_row(value: MatchResult) -> None:
        rows.append(value)

    async with AsyncClient() as client:
        matches = await client.match_in("functionDecl().bind('function')", path, on_row=on_row)
        assert len(rows) == len(matches)
