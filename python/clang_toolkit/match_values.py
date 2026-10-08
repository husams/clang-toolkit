"""Immutable semantic results whose private owners retain native AST cursors."""

from __future__ import annotations

import hashlib
import inspect
from collections.abc import Awaitable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast, overload

from google.protobuf.json_format import MessageToDict

from clang_toolkit._generated.match.v1 import match_result_pb2 as results
from clang_toolkit._generated.match.v1 import match_service_pb2 as pb
from clang_toolkit._value_lifecycle import CursorOwner, MatchValueError
from clang_toolkit._row_store import RowStore

if TYPE_CHECKING:
    from clang_toolkit.client import AsyncClient, Client

ClientT = TypeVar("ClientT")


@dataclass(frozen=True)
class ParsedTree(Generic[ClientT]):
    """A reusable pinned tree; parsing does not run a matcher."""

    path: str
    _owner: CursorOwner[ClientT] = field(repr=False, compare=False)

    def close(self) -> None:
        self._owner.check_loop()
        _close_value_sync(self._owner)

    @overload
    def match(self: ParsedTree[Client], query: str, *,
              working_directory: str | Path | None = None,
              compile_arguments: Sequence[str] = (),
              traversal_mode: pb.MatchTraversalMode = pb.MATCH_TRAVERSAL_MODE_AS_IS) -> MatchValue[Client]: ...

    @overload
    def match(self: ParsedTree[AsyncClient], query: str, *,
              working_directory: str | Path | None = None,
              compile_arguments: Sequence[str] = (),
              traversal_mode: pb.MatchTraversalMode = pb.MATCH_TRAVERSAL_MODE_AS_IS) -> Awaitable[MatchValue[AsyncClient]]: ...

    def match(self, query: str, *, working_directory: str | Path | None = None,
              compile_arguments: Sequence[str] = (),
              traversal_mode: pb.MatchTraversalMode = pb.MATCH_TRAVERSAL_MODE_AS_IS
              ) -> MatchValue[Any] | Awaitable[MatchValue[Any]]:
        """Match this pinned tree using its owning sync or async client."""
        client = cast(Any, self._owner.client)
        return client.match_in(query, self, working_directory=working_directory,
                               compile_arguments=compile_arguments,
                               traversal_mode=traversal_mode)

    async def aclose(self) -> None:
        self._owner.check_loop()
        await _close_value(self._owner)

    def __enter__(self) -> ParsedTree[ClientT]:
        self._owner.check(self._owner.client)
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    async def __aenter__(self) -> ParsedTree[ClientT]:
        self._owner.check(self._owner.client)
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()


@dataclass(frozen=True)
class BindingSelection(Generic[ClientT]):
    """A named binding across result rows, or one zero-based row."""

    name: str
    _owner: CursorOwner[ClientT] = field(repr=False, compare=False)
    _index: int | None = field(default=None, repr=False)
    scope: int = results.BINDING_MATCH_SCOPE_SUBTREE
    _binding_data: bytes | None = field(default=None, repr=False, compare=False)

    @property
    def value(self) -> results.MatchBinding:
        """Return a detached copy of this binding's serialized semantic value."""
        if self._index is None or self._binding_data is None:
            raise MatchValueError("binding value requires an explicit row index")
        value = results.MatchBinding()
        value.ParseFromString(self._binding_data)
        return value

    @overload
    def match(self: BindingSelection[Client], query: str, *,
              working_directory: str | Path | None = None,
              compile_arguments: Sequence[str] = (),
              traversal_mode: pb.MatchTraversalMode = pb.MATCH_TRAVERSAL_MODE_AS_IS) -> MatchValue[Client]: ...

    @overload
    def match(self: BindingSelection[AsyncClient], query: str, *,
              working_directory: str | Path | None = None,
              compile_arguments: Sequence[str] = (),
              traversal_mode: pb.MatchTraversalMode = pb.MATCH_TRAVERSAL_MODE_AS_IS) -> Awaitable[MatchValue[AsyncClient]]: ...

    def match(self, query: str, *, working_directory: str | Path | None = None,
              compile_arguments: Sequence[str] = (),
              traversal_mode: pb.MatchTraversalMode = pb.MATCH_TRAVERSAL_MODE_AS_IS
              ) -> MatchValue[Any] | Awaitable[MatchValue[Any]]:
        client = cast(Any, self._owner.client)
        return client.match_in(query, self, working_directory=working_directory,
                               compile_arguments=compile_arguments,
                               traversal_mode=traversal_mode)


@dataclass(frozen=True)
class MatchRow(Generic[ClientT]):
    """One immutable row with copy-on-read protobuf semantic bindings."""

    _data: bytes = field(repr=False)
    _owner: CursorOwner[ClientT] = field(repr=False, compare=False)
    _index: int = field(repr=False)

    def _message(self) -> results.MatchResult:
        row = results.MatchResult()
        row.ParseFromString(self._data)
        return row

    @property
    def bindings(self) -> Mapping[str, results.MatchBinding]:
        return dict(self._message().bindings)

    @property
    def source_match_index(self) -> int | None:
        row = self._message()
        return row.source_match_index if row.HasField("source_match_index") else None

    def to_dict(self) -> dict[str, Any]:
        return MessageToDict(self._message(), preserving_proto_field_name=True)

    def binding(self, name: str, *,
                scope: int = results.BINDING_MATCH_SCOPE_SUBTREE) -> BindingSelection[ClientT]:
        bindings = self.bindings
        if name not in bindings:
            raise MatchValueError(f"unknown binding: {name}")
        return BindingSelection(
            name, self._owner, self._index, scope,
            _binding_data=bindings[name].SerializeToString(),
        )


@dataclass(frozen=True, eq=False)
class MatchValue(Generic[ClientT]):
    """Reusable immutable matching results on their own retained cursor."""

    _store: RowStore = field(repr=False, compare=False)
    _owner: CursorOwner[ClientT] = field(repr=False, compare=False)

    @classmethod
    def _from_response(cls, response: pb.MatchResponse,
                       owner: CursorOwner[ClientT]) -> MatchValue[ClientT]:
        store = RowStore()
        try:
            for row in response.results:
                store.append(row.SerializeToString(), binding_names=row.bindings)
        except BaseException:
            store.close()
            raise
        return cls(store, owner)

    @classmethod
    def _from_store(cls, store: RowStore,
                    owner: CursorOwner[ClientT]) -> MatchValue[ClientT]:
        return cls(store, owner)

    @property
    def rows(self) -> tuple[MatchRow[ClientT], ...]:
        return tuple(self.iter_rows())

    def iter_rows(self) -> Iterator[MatchRow[ClientT]]:
        """Yield immutable rows without materializing the full collection."""
        for index, data in enumerate(self._store.iter_bytes()):
            yield MatchRow(data, self._owner, index)

    def __len__(self) -> int:
        return len(self._store)

    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self):
            return False
        if len(self) != len(other):
            return False
        return all(
            left == right
            for left, right in zip(
                self._store.iter_bytes(), other._store.iter_bytes(), strict=True
            )
        )

    def __hash__(self) -> int:
        """Hash framed row bytes with constant extra memory."""
        digest = hashlib.blake2b(digest_size=32)
        digest.update(len(self).to_bytes(8, "big"))
        for data in self._store.iter_bytes():
            digest.update(len(data).to_bytes(8, "big"))
            digest.update(data)
        return hash(digest.digest())

    def __iter__(self) -> Iterator[MatchRow[ClientT]]:
        return self.iter_rows()

    def __getitem__(self, index: int) -> MatchRow[ClientT]:
        if type(index) is not int or index < 0 or index >= len(self._store):
            raise MatchValueError("match row index must be a valid zero-based integer")
        return MatchRow(self._store.read(index), self._owner, index)

    def binding(self, name: str, *,
                scope: int = results.BINDING_MATCH_SCOPE_SUBTREE) -> BindingSelection[ClientT]:
        if not isinstance(name, str) or not name:
            raise MatchValueError("binding name must be nonempty")
        if len(self) and name not in self.binding_names():
            raise MatchValueError(f"unknown binding: {name}")
        return BindingSelection(name, self._owner, scope=scope)

    def binding_names(self) -> set[str]:
        """Return distinct bind names while retaining only the names in memory."""
        return self._store.binding_names()

    def close(self) -> None:
        self._owner.check_loop()
        _close_value_sync(self._owner)

    async def aclose(self) -> None:
        self._owner.check_loop()
        await _close_value(self._owner)

    def __enter__(self) -> MatchValue[ClientT]:
        self._owner.check(self._owner.client)
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    async def __aenter__(self) -> MatchValue[ClientT]:
        self._owner.check(self._owner.client)
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()


MatchTarget = str | Path | ParsedTree[Any] | MatchValue[Any] | BindingSelection[Any]


async def _close_value(owner: CursorOwner[Any]) -> None:
    owner.close()
    flush = getattr(owner.client, "_close_value_cleanup")
    await flush(owner.session_id)


def _close_value_sync(owner: CursorOwner[Any]) -> None:
    owner.close()
    flush = getattr(owner.client, "_close_value_cleanup")
    if not inspect.iscoroutinefunction(flush):
        flush(owner.session_id)
