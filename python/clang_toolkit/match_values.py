"""Immutable semantic results whose private owners retain native AST cursors."""

from __future__ import annotations

import hashlib
import inspect
from collections.abc import Awaitable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from itertools import islice
from pathlib import Path
from typing import TYPE_CHECKING, Any, Generic, TypeVar, cast, overload

from google.protobuf.json_format import MessageToDict

from clang_toolkit._generated.match.v1 import match_result_pb2 as results
from clang_toolkit._generated.match.v1 import match_service_pb2 as pb
from clang_toolkit._value_lifecycle import CursorOwner, MatchValueError
from clang_toolkit._row_store import RowStore
from clang_toolkit.matchers import MatcherInput
from clang_toolkit.resources import FileHandle, InputDescriptor

if TYPE_CHECKING:
    from clang_toolkit.client import AsyncClient, Client

ClientT = TypeVar("ClientT")


@dataclass(frozen=True)
class ParsedTree(Generic[ClientT]):
    """A reusable pinned tree; parsing does not run a matcher."""

    path: str
    _owner: CursorOwner[ClientT] = field(repr=False, compare=False)
    source_file: str | None = field(default=None, repr=False, compare=False)

    def close(self) -> None:
        self._owner.check_loop()
        _close_value_sync(self._owner)

    @overload
    def match(self: ParsedTree[Client], query: MatcherInput, *,
              working_directory: str | Path | None = None,
              compile_arguments: Sequence[str] = (),
              traversal_mode: pb.MatchTraversalMode = pb.MATCH_TRAVERSAL_MODE_AS_IS) -> MatchValue[Client]: ...

    @overload
    def match(self: ParsedTree[AsyncClient], query: MatcherInput, *,
              working_directory: str | Path | None = None,
              compile_arguments: Sequence[str] = (),
              traversal_mode: pb.MatchTraversalMode = pb.MATCH_TRAVERSAL_MODE_AS_IS) -> Awaitable[MatchValue[AsyncClient]]: ...

    def match(self, query: MatcherInput, *, working_directory: str | Path | None = None,
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
    source_file: str | None = field(default=None, repr=False, compare=False)

    @property
    def value(self) -> results.MatchBinding:
        """Return a detached copy of this binding's serialized semantic value."""
        if self._index is None or self._binding_data is None:
            raise MatchValueError("binding value requires an explicit row index")
        value = results.MatchBinding()
        value.ParseFromString(self._binding_data)
        return value

    @property
    def decl_name(self) -> str | None:
        return _binding_decl_name(self.value)

    @property
    def parameter_name(self) -> str | None:
        return self.decl_name

    @property
    def record_name(self) -> str | None:
        return self.decl_name

    @property
    def decl_type(self) -> str | None:
        return _binding_decl_type(self.value)

    @property
    def type_name(self) -> str | None:
        return self.decl_type

    @overload
    def match(self: BindingSelection[Client], query: MatcherInput, *,
              working_directory: str | Path | None = None,
              compile_arguments: Sequence[str] = (),
              traversal_mode: pb.MatchTraversalMode = pb.MATCH_TRAVERSAL_MODE_AS_IS) -> MatchValue[Client]: ...

    @overload
    def match(self: BindingSelection[AsyncClient], query: MatcherInput, *,
              working_directory: str | Path | None = None,
              compile_arguments: Sequence[str] = (),
              traversal_mode: pb.MatchTraversalMode = pb.MATCH_TRAVERSAL_MODE_AS_IS) -> Awaitable[MatchValue[AsyncClient]]: ...

    def match(self, query: MatcherInput, *, working_directory: str | Path | None = None,
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
    _source_file: str | None = field(default=None, repr=False, compare=False)

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

    @property
    def source_file(self) -> str | None:
        """The input file that produced this row, when known."""
        return self._source_file

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
            source_file=self._source_file,
        )


@dataclass(frozen=True, eq=False)
class MatchValue(Generic[ClientT]):
    """Reusable immutable matching results on their own retained cursor."""

    _store: RowStore = field(repr=False, compare=False)
    _owner: CursorOwner[ClientT] = field(repr=False, compare=False)
    _source_file: str | None = field(default=None, repr=False, compare=False)

    @classmethod
    def _from_response(cls, response: pb.MatchResponse,
                       owner: CursorOwner[ClientT], *,
                       source_file: str | None = None) -> MatchValue[ClientT]:
        store = RowStore()
        try:
            for row in response.results:
                store.append(row.SerializeToString(), binding_names=row.bindings)
        except BaseException:
            store.close()
            raise
        return cls(store, owner, source_file)

    @classmethod
    def _from_store(cls, store: RowStore,
                    owner: CursorOwner[ClientT], *,
                    source_file: str | None = None) -> MatchValue[ClientT]:
        return cls(store, owner, source_file)

    @property
    def rows(self) -> tuple[MatchRow[ClientT], ...]:
        return tuple(self.iter_rows())

    def iter_rows(self) -> Iterator[MatchRow[ClientT]]:
        """Yield immutable rows without materializing the full collection."""
        for index, data in enumerate(self._store.iter_bytes()):
            yield MatchRow(data, self._owner, index, self.source_file)

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
        return MatchRow(self._store.read(index), self._owner, index, self.source_file)

    def binding(self, name: str, *,
                scope: int = results.BINDING_MATCH_SCOPE_SUBTREE) -> BindingSelection[ClientT]:
        if not isinstance(name, str) or not name:
            raise MatchValueError("binding name must be nonempty")
        if len(self) and name not in self.binding_names():
            raise MatchValueError(f"unknown binding: {name}")
        return BindingSelection(name, self._owner, scope=scope,
                                source_file=self._source_file)

    def binding_names(self) -> set[str]:
        """Return distinct bind names while retaining only the names in memory."""
        return self._store.binding_names()

    @property
    def source_file(self) -> str | None:
        return self._source_file

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


@dataclass(frozen=True, eq=False)
class NativeMatchCollection(Generic[ClientT]):
    """A bounded, ordered collection of independently retained per-file matches."""

    matches: tuple[MatchValue[ClientT], ...]
    files: tuple[str, ...]

    def __post_init__(self) -> None:
        if len(self.matches) != len(self.files):
            raise ValueError("native match collection file metadata is inconsistent")

    def __len__(self) -> int:
        return sum(map(len, self.matches))

    @property
    def rows(self) -> tuple[MatchRow[ClientT], ...]:
        return tuple(iter(self))

    def iter_rows(self) -> Iterator[MatchRow[ClientT]]:
        return iter(self)

    def __iter__(self) -> Iterator[MatchRow[ClientT]]:
        for match, path in zip(self.matches, self.files, strict=True):
            for row in match.iter_rows():
                yield MatchRow(row._data, row._owner, row._index, path)

    def __getitem__(self, index: int) -> MatchRow[ClientT]:
        if type(index) is not int or index < 0:
            raise MatchValueError("match row index must be a valid zero-based integer")
        remaining = index
        for match, path in zip(self.matches, self.files, strict=True):
            if remaining < len(match):
                row = match[remaining]
                return MatchRow(row._data, row._owner, row._index, path)
            remaining -= len(match)
        raise MatchValueError("match row index must be a valid zero-based integer")

    def binding_names(self) -> set[str]:
        names: set[str] = set()
        for match in self.matches:
            names.update(match.binding_names())
        return names

    def binding(self, name: str) -> NativeBindingCollection[ClientT]:
        if not isinstance(name, str) or not name:
            raise MatchValueError("binding name must be nonempty")
        if name not in self.binding_names() and len(self):
            raise MatchValueError(f"unknown binding: {name}")
        selections = tuple(
            BindingSelection(name, match._owner, source_file=match.source_file or path)
            if name in match.binding_names() else None
            for match, path in zip(self.matches, self.files, strict=True)
        )
        if not any(selection is not None for selection in selections) and len(self):
            raise MatchValueError(f"unknown binding: {name}")
        return NativeBindingCollection(selections, self.files, self.matches)

    def close(self) -> None:
        errors: list[BaseException] = []
        for match in self.matches:
            try:
                match.close()
            except BaseException as error:
                errors.append(error)
        _raise_cleanup_errors(errors)

    async def aclose(self) -> None:
        errors: list[BaseException] = []
        for match in self.matches:
            try:
                await match.aclose()
            except BaseException as error:
                errors.append(error)
        _raise_cleanup_errors(errors)


@dataclass(frozen=True)
class NativeBindingCollection(Generic[ClientT]):
    """A named binding selection spanning independent per-file match cursors."""

    selections: tuple[BindingSelection[ClientT] | None, ...]
    files: tuple[str, ...]
    matches: tuple[MatchValue[ClientT], ...] = field(default=(), repr=False, compare=False)

    def __post_init__(self) -> None:
        if len(self.selections) != len(self.files):
            raise ValueError("native binding collection file metadata is inconsistent")
        if self.matches and len(self.matches) != len(self.files):
            raise ValueError("native binding collection match metadata is inconsistent")

    def __len__(self) -> int:
        if self.matches:
            return sum(1 for _ in self)
        return sum(selection is not None for selection in self.selections)

    def binding_names(self) -> set[str]:
        return {selection.name for selection in self.selections if selection is not None}

    def __iter__(self) -> Iterator[BindingSelection[ClientT]]:
        if not self.matches:
            return iter(selection for selection in self.selections if selection is not None)

        def selections() -> Iterator[BindingSelection[ClientT]]:
            for match, selection in zip(self.matches, self.selections, strict=True):
                if selection is None:
                    continue
                for row in match.iter_rows():
                    if selection.name not in row.bindings:
                        continue
                    binding = row.binding(selection.name)
                    yield BindingSelection(
                        binding.name, binding._owner, binding._index,
                        binding.scope, binding._binding_data, selection.source_file,
                    )

        return selections()

    def __getitem__(self, index: int) -> BindingSelection[ClientT]:
        if type(index) is not int or index < 0 or index >= len(self):
            raise MatchValueError("binding selection index must be a valid zero-based integer")
        try:
            return next(islice(iter(self), index, None))
        except StopIteration as error:
            raise MatchValueError("binding selection index must be a valid zero-based integer") from error

    def close(self) -> None:
        owners = {selection._owner for selection in self.selections if selection is not None}
        owners.update(match._owner for match in self.matches)
        errors: list[BaseException] = []
        for owner in owners:
            try:
                _close_value_sync(owner)
            except BaseException as error:
                errors.append(error)
        _raise_cleanup_errors(errors)

    async def aclose(self) -> None:
        owners = {selection._owner for selection in self.selections if selection is not None}
        owners.update(match._owner for match in self.matches)
        errors: list[BaseException] = []
        for owner in owners:
            try:
                await _close_value(owner)
            except BaseException as error:
                errors.append(error)
        _raise_cleanup_errors(errors)


def _raise_cleanup_errors(errors: list[BaseException]) -> None:
    if len(errors) == 1:
        raise errors[0]
    if errors:
        raise BaseExceptionGroup("native match aggregate cleanup failed", errors)


def _messages(message: Any) -> Iterator[Any]:
    """Walk only copied protobuf values in a binding's shallow projection."""
    from google.protobuf.message import Message

    if not isinstance(message, Message):
        return
    yield message
    for field, item in message.ListFields():
        if field.is_repeated:
            if field.message_type is not None and not field.message_type.GetOptions().map_entry:
                for child in item:
                    yield from _messages(child)
        elif field.message_type is not None:
            yield from _messages(item)


def _binding_decl_name(binding: results.MatchBinding) -> str | None:
    messages = list(_messages(binding))
    for field_name in ("qualified_name", "identifier", "literal_operator_suffix"):
        for message in messages:
            descriptor = message.DESCRIPTOR.fields_by_name.get(field_name)
            if descriptor is not None and descriptor.type == descriptor.TYPE_STRING:
                value = getattr(message, field_name)
                if value:
                    return value
    return None


def _binding_decl_type(binding: results.MatchBinding) -> str | None:
    for message in _messages(binding):
        if message.DESCRIPTOR.name == "QualType":
            description = getattr(message, "description", None)
            value = getattr(description, "spelling", "") if description is not None else ""
            if value:
                return value
    return None


MatchTarget = str | Path | ParsedTree[Any] | MatchValue[Any] | BindingSelection[Any] | FileHandle[Any] | InputDescriptor


async def _close_value(owner: CursorOwner[Any]) -> None:
    owner.close()
    flush = getattr(owner.client, "_close_value_cleanup")
    await flush(owner.session_id)


def _close_value_sync(owner: CursorOwner[Any]) -> None:
    owner.close()
    flush = getattr(owner.client, "_close_value_cleanup")
    if not inspect.iscoroutinefunction(flush):
        flush(owner.session_id)
