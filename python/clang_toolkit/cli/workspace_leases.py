"""Renew only live cursors owned by this workspace without creating aliases."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from time import monotonic
from typing import Any

from clang_toolkit.client import Client


class WorkspaceLeases:
    def __init__(self, client: Client, renew: Callable[[str], Awaitable[Any]]) -> None:
        self.client = client
        self.renew = renew
        self.last_refresh = float("-inf")

    async def refresh(self, *, force: bool = False) -> None:
        now = monotonic()
        if not force and now - self.last_refresh < 30:
            return
        # Snapshot under the caller's Runtime lock. The SDK registry uses weak
        # references, so dropped bindings and closed cursors are not kept alive.
        identifiers = [
            identity
            for identity, reference in tuple(self.client._values.items())
            if (owner := reference()) is not None and not owner.closed
        ]
        if identifiers:
            # AttachSession metadata renews leases without allocating a new
            # CursorOwner. Creating temporary SDK aliases could close the cursor
            # on garbage collection or change a stale revision's ownership.
            await asyncio.gather(
                *(self.renew(identity) for identity in identifiers),
                return_exceptions=True,
            )
        self.last_refresh = now
