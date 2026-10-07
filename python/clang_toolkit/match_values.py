"""Immutable semantic results whose private owners retain native AST cursors."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Awaitable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast, overload

from google.protobuf.json_format import MessageToDict

from clang_toolkit._generated.match.v1 import match_result_pb2 as results
from clang_toolkit._generated.match.v1 import match_service_pb2 as pb
from clang_toolkit._value_lifecycle import CursorOwner, MatchValueError

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
        if name not in self.bindings:
            raise MatchValueError(f"unknown binding: {name}")
        return BindingSelection(name, self._owner, self._index, scope)


@dataclass(frozen=True)
class MatchValue(Generic[ClientT]):
    """Reusable immutable matching results on their own retained cursor."""

    _data: tuple[bytes, ...] = field(repr=False)
    _owner: CursorOwner[ClientT] = field(repr=False, compare=False)

    @classmethod
    def _from_response(cls, response: pb.MatchResponse,
                       owner: CursorOwner[ClientT]) -> MatchValue[ClientT]:
        return cls(tuple(row.SerializeToString() for row in response.results), owner)

    @property
    def rows(self) -> tuple[MatchRow[ClientT], ...]:
        return tuple(MatchRow(data, self._owner, index)
                     for index, data in enumerate(self._data))

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[MatchRow[ClientT]]:
        return iter(self.rows)

    def __getitem__(self, index: int) -> MatchRow[ClientT]:
        if type(index) is not int or index < 0 or index >= len(self._data):
            raise MatchValueError("match row index must be a valid zero-based integer")
        return MatchRow(self._data[index], self._owner, index)

    def binding(self, name: str, *,
                scope: int = results.BINDING_MATCH_SCOPE_SUBTREE) -> BindingSelection[ClientT]:
        if not isinstance(name, str) or not name:
            raise MatchValueError("binding name must be nonempty")
        if self._data and not any(name in row.bindings for row in self.rows):
            raise MatchValueError(f"unknown binding: {name}")
        return BindingSelection(name, self._owner, scope=scope)

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
