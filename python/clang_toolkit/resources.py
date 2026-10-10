"""Metadata-only file inputs and bounded batch partitioning helpers."""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generic, TypeVar, cast


class ResourceError(RuntimeError):
    """A file or scoped-resource operation failed."""


def require_complete(value: Any) -> Any:
    """Reject protobuf analysis results that report omitted or partial data."""
    try:
        fields = value.ListFields()
    except AttributeError:
        return value
    descriptor = value.DESCRIPTOR
    complete_field = descriptor.fields_by_name.get("is_complete")
    if (
        complete_field is not None
        and value.HasField("is_complete")
        and not value.is_complete
    ):
        raise ResourceError(f"{descriptor.name} result is incomplete")
    omitted = descriptor.fields_by_name.get("external_edges_omitted")
    if omitted is not None and getattr(value, omitted.name) > 0:
        raise ResourceError("call graph result omitted external edges")
    for field_descriptor, field_value in fields:
        if field_descriptor.message_type is None:
            continue
        children = field_value if field_descriptor.is_repeated else (field_value,)
        for child in children:
            require_complete(child)
    return value


@dataclass(frozen=True, slots=True)
class InputDescriptor:
    """One frozen analysis input, identified by path and compilation profile."""

    path: str
    profile_id: str = ""
    working_directory: str = ""
    compile_arguments: tuple[str, ...] = ()
    compilation_database: str = ""
    source_bytes: int = 0
    estimated_parse_bytes: int = 0
    frozen_profile: bool = False

    def __post_init__(self) -> None:
        if not self.path:
            raise ValueError("input path must not be empty")
        if not isinstance(self.compile_arguments, tuple):
            object.__setattr__(self, "compile_arguments", tuple(self.compile_arguments))

    @classmethod
    def from_path(
        cls,
        path: str | Path,
        *,
        working_directory: str | Path | None = None,
        compile_arguments: Sequence[str] = (),
        compilation_database: str | Path | None = None,
        profile_id: str = "",
    ) -> InputDescriptor:
        """Build a descriptor without opening or parsing the source file."""
        # Paths belong to the serving machine. Preserve their spelling and avoid
        # consulting local symlinks or filesystem state for remote clients.
        working = (
            str(working_directory) if working_directory is not None else str(Path.cwd())
        )
        return cls(
            str(path),
            profile_id,
            working,
            tuple(compile_arguments),
            str(compilation_database) if compilation_database is not None else "",
        )

    @classmethod
    def from_proto(cls, value: Any) -> InputDescriptor:
        profile = value.profile
        return cls(
            value.file_path,
            profile.profile_id,
            profile.working_directory,
            tuple(profile.compile_arguments),
            profile.compilation_database,
            value.source_bytes,
            value.estimated_parse_bytes,
            profile.frozen,
        )

    def to_proto(self) -> Any:
        from clang_toolkit._generated.match.v1 import resources_pb2

        value = resources_pb2.InputDescriptor(
            file_path=self.path,
            profile=resources_pb2.CompilationProfile(
                profile_id=self.profile_id,
                compile_arguments=self.compile_arguments,
                working_directory=self.working_directory,
                compilation_database=self.compilation_database,
            ),
            source_bytes=self.source_bytes,
            estimated_parse_bytes=self.estimated_parse_bytes,
        )
        value.profile.frozen = self.frozen_profile
        return value


@dataclass(frozen=True, slots=True)
class FileSet:
    """Frozen metadata manifest; it does not retain ASTs or open-file leases."""

    inputs: tuple[InputDescriptor, ...]
    diagnostics: tuple[str, ...] = ()
    metadata_bytes: int = 0

    def __post_init__(self) -> None:
        object.__setattr__(self, "inputs", tuple(self.inputs))
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))
        if any(not isinstance(item, InputDescriptor) for item in self.inputs):
            raise TypeError("FileSet inputs must be InputDescriptor values")

    def __len__(self) -> int:
        return len(self.inputs)

    def __iter__(self) -> Iterator[InputDescriptor]:
        return iter(self.inputs)


@dataclass(frozen=True, slots=True)
class FileBatch:
    """One immutable, one-based slice of a frozen FileSet."""

    index: int
    length: int
    inputs: tuple[InputDescriptor, ...]

    @property
    def paths(self) -> tuple[str, ...]:
        return tuple(item.path for item in self.inputs)


ClientT = TypeVar("ClientT")


def _preserve_cleanup_error(
    primary: BaseException | None, cleanup: BaseException, context: str
) -> None:
    """Keep a body exception primary when context-manager cleanup also fails."""
    if primary is None:
        raise cleanup
    primary.add_note(f"{context} cleanup failed: {cleanup}")


@dataclass(frozen=True, slots=True)
class FileHandle(Generic[ClientT]):
    """Caller-owned lease on one validated immutable file snapshot."""

    lease_id: str
    input: InputDescriptor
    _client: ClientT = field(repr=False, compare=False)
    source_revision: str = ""
    snapshot_id: str = ""
    state: int = 0

    @property
    def path(self) -> str:
        return self.input.path

    @property
    def profile_id(self) -> str:
        return self.input.profile_id

    def close(self) -> Any:
        return cast(Any, self._client).close_file(self)

    async def aclose(self) -> None:
        await cast(Any, self._client).close_file(self)

    def __enter__(self) -> FileHandle[ClientT]:
        return self

    def __exit__(self, exc_type: object, exc: BaseException | None, tb: object) -> None:
        try:
            self.close()
        except BaseException as cleanup:
            _preserve_cleanup_error(exc, cleanup, "file handle")

    async def __aenter__(self) -> FileHandle[ClientT]:
        return self

    async def __aexit__(
        self, exc_type: object, exc: BaseException | None, tb: object
    ) -> None:
        try:
            await self.aclose()
        except BaseException as cleanup:
            _preserve_cleanup_error(exc, cleanup, "file handle")


@dataclass(slots=True)
class ResourceScope(Generic[ClientT]):
    """Owner-scoped resource lifetime with acknowledged terminal state."""

    resource_scope_id: str
    info: Any = field(repr=False)
    _client: ClientT = field(repr=False)

    @property
    def state(self) -> int:
        return self.info.state

    @property
    def cleanup_acknowledged(self) -> bool:
        return self.info.cleanup_acknowledged

    def describe(self) -> Any:
        self.info = cast(Any, self._client).describe_resource_scope(self)
        return self.info

    async def adescribe(self) -> Any:
        self.info = await cast(Any, self._client).describe_resource_scope(self)
        return self.info

    def cancel(self) -> Any:
        self.info = cast(Any, self._client).cancel_resource_scope(self)
        return self.info

    async def acancel(self) -> Any:
        self.info = await cast(Any, self._client).cancel_resource_scope(self)
        return self.info

    def release(self) -> Any:
        self.info = cast(Any, self._client).release_resource_scope(self)
        if not self.info.cleanup_acknowledged:
            raise ResourceError("resource scope release has not been acknowledged")
        return self.info

    async def arelease(self) -> Any:
        self.info = await cast(Any, self._client).release_resource_scope(self)
        if not self.info.cleanup_acknowledged:
            raise ResourceError("resource scope release has not been acknowledged")
        return self.info

    def __enter__(self) -> ResourceScope[ClientT]:
        return self

    def __exit__(self, exc_type: object, exc: BaseException | None, tb: object) -> None:
        try:
            self.release()
        except BaseException as cleanup:
            _preserve_cleanup_error(exc, cleanup, "resource scope")

    async def __aenter__(self) -> ResourceScope[ClientT]:
        return self

    async def __aexit__(
        self, exc_type: object, exc: BaseException | None, tb: object
    ) -> None:
        try:
            await self.arelease()
        except BaseException as cleanup:
            _preserve_cleanup_error(exc, cleanup, "resource scope")


def partition_inputs(
    files: FileSet,
    *,
    size: int | None = None,
    count: int | None = None,
) -> Iterator[FileBatch]:
    """Yield bounded batches by maximum size or balanced group count.

    The iterator never aggregates results. A caller completes and releases each
    batch before requesting the next one.
    """
    if not isinstance(files, FileSet):
        raise TypeError("files must be a FileSet")
    if (size is None) == (count is None):
        raise ValueError("provide exactly one of size or count")
    requested = size if size is not None else count
    if isinstance(requested, bool) or requested is None or requested <= 0:
        raise ValueError("size and count must be positive integers")

    total = len(files)
    if size is not None:
        for offset in range(0, total, size):
            chunk = files.inputs[offset : offset + size]
            yield FileBatch(offset // size + 1, len(chunk), chunk)
        return

    if total == 0:
        return
    if count is None or count > total:
        raise ValueError("count cannot exceed the nonempty input count")
    quotient, remainder = divmod(total, count)
    offset = 0
    for index in range(count):
        length = quotient + (1 if index < remainder else 0)
        chunk = files.inputs[offset : offset + length]
        yield FileBatch(index + 1, length, chunk)
        offset += length
