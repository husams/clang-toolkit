from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from typing import ClassVar as _ClassVar, Optional as _Optional

DESCRIPTOR: _descriptor.FileDescriptor

class CacheResources(_message.Message):
    __slots__ = ("memory_available", "reusable_snapshots", "reusable_memory_bytes", "pending_builds", "storage_available", "artifact_disk_bytes", "ready_snapshots", "stale_snapshots", "leased_snapshots", "storage_root")
    MEMORY_AVAILABLE_FIELD_NUMBER: _ClassVar[int]
    REUSABLE_SNAPSHOTS_FIELD_NUMBER: _ClassVar[int]
    REUSABLE_MEMORY_BYTES_FIELD_NUMBER: _ClassVar[int]
    PENDING_BUILDS_FIELD_NUMBER: _ClassVar[int]
    STORAGE_AVAILABLE_FIELD_NUMBER: _ClassVar[int]
    ARTIFACT_DISK_BYTES_FIELD_NUMBER: _ClassVar[int]
    READY_SNAPSHOTS_FIELD_NUMBER: _ClassVar[int]
    STALE_SNAPSHOTS_FIELD_NUMBER: _ClassVar[int]
    LEASED_SNAPSHOTS_FIELD_NUMBER: _ClassVar[int]
    STORAGE_ROOT_FIELD_NUMBER: _ClassVar[int]
    memory_available: bool
    reusable_snapshots: int
    reusable_memory_bytes: int
    pending_builds: int
    storage_available: bool
    artifact_disk_bytes: int
    ready_snapshots: int
    stale_snapshots: int
    leased_snapshots: int
    storage_root: str
    def __init__(self, memory_available: _Optional[bool] = ..., reusable_snapshots: _Optional[int] = ..., reusable_memory_bytes: _Optional[int] = ..., pending_builds: _Optional[int] = ..., storage_available: _Optional[bool] = ..., artifact_disk_bytes: _Optional[int] = ..., ready_snapshots: _Optional[int] = ..., stale_snapshots: _Optional[int] = ..., leased_snapshots: _Optional[int] = ..., storage_root: _Optional[str] = ...) -> None: ...
