"""Workspace lease renewal preserves weak ownership and immutable revisions."""

from __future__ import annotations

import asyncio
import gc
import weakref

from clang_toolkit._value_lifecycle import CursorOwner
from clang_toolkit.client import Client
from clang_toolkit.cli.workspace_leases import WorkspaceLeases


def test_keepalive_renews_live_owners_without_new_aliases_or_revision_changes() -> None:
    client = Client("unix:///tmp/unused-workspace.sock")
    released: list[str] = []
    live = CursorOwner(client, "live", 7, released.append)
    closed = CursorOwner(client, "closed", 1, released.append)
    dropped = CursorOwner(client, "dropped", 1, released.append)
    client._values.update(
        {owner.session_id: weakref.ref(owner) for owner in (live, closed, dropped)}
    )
    closed.close()
    del dropped
    gc.collect()
    renewed: list[str] = []

    async def renew(identity: str):
        renewed.append(identity)
        return {"result_revision": 99}

    async def run() -> None:
        leases = WorkspaceLeases(client, renew)
        await leases.refresh()
        await leases.refresh()
        assert renewed == ["live"]
        await leases.refresh(force=True)
        assert renewed == ["live", "live"]

    asyncio.run(run())
    assert live.revision == 7 and not live.closed
    assert client._values["live"]() is live
    assert released == ["closed", "dropped"]


def test_keepalive_failure_does_not_block_local_commands_or_other_cursors() -> None:
    client = Client("unix:///tmp/unused-workspace.sock")
    owners = [
        CursorOwner(client, name, 1, lambda _: None) for name in ("expired", "live")
    ]
    client._values.update({owner.session_id: weakref.ref(owner) for owner in owners})
    renewed: list[str] = []

    async def renew(identity: str):
        renewed.append(identity)
        if identity == "expired":
            raise RuntimeError("cursor unavailable")

    asyncio.run(WorkspaceLeases(client, renew).refresh())
    assert renewed == ["expired", "live"]
    assert not any(owner.closed for owner in owners)
