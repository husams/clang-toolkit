"""Private ownership and operation leases for retained native cursors."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Generic, TypeVar

ClientT = TypeVar("ClientT")


class MatchValueError(ValueError):
    """A retained value is closed or used by another client."""


class CursorOwner(Generic[ClientT]):
    """One retained cursor shared by its values, rows and selections."""

    def __init__(self, client: ClientT, session_id: str, revision: int,
                 release: Callable[[str], None], *,
                 loop: asyncio.AbstractEventLoop | None = None) -> None:
        self.client = client
        self.session_id = session_id
        self.revision = revision
        self._release = release
        self.loop = loop
        self.closed = False

    def check(self, client: ClientT) -> None:
        if self.closed:
            raise MatchValueError("retained value has been closed")
        if self.client is not client:
            raise MatchValueError("retained value belongs to another client")
        self.check_loop()

    def check_loop(self) -> None:
        if self.loop is None:
            return
        try:
            current = asyncio.get_running_loop()
        except RuntimeError as error:
            raise RuntimeError("async retained values must be used on their owning event loop") from error
        if current is not self.loop:
            raise RuntimeError("async retained values must be used on their owning event loop")

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            self._release(self.session_id)

    def __del__(self) -> None:
        # Finalizers may run on an arbitrary thread; release callbacks marshal
        # asynchronous cleanup to the recorded owner loop.
        self.close()


class OperationLease:
    """Admission token allowing accepted work to finish during shutdown."""

    def __init__(self, client: object) -> None:
        self.client = client
        self.active = True

    def close(self) -> None:
        self.active = False
