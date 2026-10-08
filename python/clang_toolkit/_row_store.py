"""Bounded-memory storage for serialized match rows."""

from __future__ import annotations

import struct
import tempfile
from collections.abc import Iterable
from typing import BinaryIO, Iterator

from clang_toolkit._generated.match.v1 import match_result_pb2


class RowStore:
    """Append-only protobuf row storage with a disk-backed random-access index."""

    _INDEX = struct.Struct("!QQ")

    def __init__(self, *, memory_limit: int = 64 * 1024) -> None:
        self._closed = True
        self._memory_limit = memory_limit
        self._memory = bytearray()
        self._data: BinaryIO | None = None
        self._index: BinaryIO | None = None
        self._index = tempfile.TemporaryFile(mode="w+b")
        self._count = 0
        self._binding_names: set[str] = set()
        self._binding_names_complete = True
        self._closed = False

    def append(self, data: bytes, *, binding_names: Iterable[str] | None = None) -> None:
        if self._closed:
            raise RuntimeError("row store is closed")
        length = len(data)
        if self._data is None and len(self._memory) + length <= self._memory_limit:
            offset = len(self._memory)
            self._memory.extend(data)
        else:
            if self._data is None:
                self._data = tempfile.TemporaryFile(mode="w+b")
                self._data.write(self._memory)
                self._memory.clear()
            self._data.seek(0, 2)
            offset = self._data.tell()
            self._data.write(data)
        assert self._index is not None
        self._index.seek(0, 2)
        self._index.write(self._INDEX.pack(offset, length))
        self._count += 1
        if binding_names is None:
            self._binding_names_complete = False
        else:
            self._binding_names.update(binding_names)

    def read(self, index: int) -> bytes:
        if self._closed:
            raise RuntimeError("row store is closed")
        if index < 0 or index >= self._count:
            raise IndexError(index)
        assert self._index is not None
        self._index.seek(index * self._INDEX.size)
        offset, length = self._INDEX.unpack(self._index.read(self._INDEX.size))
        if self._data is None:
            return bytes(self._memory[offset : offset + length])
        self._data.seek(offset)
        data = self._data.read(length)
        if len(data) != length:
            raise OSError("truncated match row spool")
        return data

    def iter_bytes(self) -> Iterator[bytes]:
        for index in range(self._count):
            yield self.read(index)

    def binding_names(self) -> set[str]:
        """Return cached distinct names, scanning legacy raw appends at most once."""
        if not self._binding_names_complete:
            names = set(self._binding_names)
            for data in self.iter_bytes():
                row = match_result_pb2.MatchResult.FromString(data)
                names.update(row.bindings)
            self._binding_names = names
            self._binding_names_complete = True
        return set(self._binding_names)

    def flush(self) -> None:
        """Surface deferred spool write failures before publishing a result."""
        if self._closed:
            raise RuntimeError("row store is closed")
        if self._data is not None:
            self._data.flush()
        assert self._index is not None
        self._index.flush()

    def __len__(self) -> int:
        return self._count

    @property
    def spilled(self) -> bool:
        return self._data is not None

    def close(self) -> None:
        if getattr(self, "_closed", True):
            return
        self._closed = True
        errors: list[BaseException] = []
        for resource in (getattr(self, "_index", None), getattr(self, "_data", None)):
            if resource is not None:
                try:
                    resource.close()
                except BaseException as error:
                    errors.append(error)
        memory = getattr(self, "_memory", None)
        if memory is not None:
            memory.clear()
        if errors:
            raise errors[0]

    def __del__(self) -> None:
        try:
            self.close()
        except BaseException:
            pass
