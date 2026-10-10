import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class FileState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    FILE_STATE_UNSPECIFIED: _ClassVar[FileState]
    FILE_STATE_OPENING: _ClassVar[FileState]
    FILE_STATE_OPEN: _ClassVar[FileState]
    FILE_STATE_PINNED: _ClassVar[FileState]
    FILE_STATE_CLOSING: _ClassVar[FileState]
    FILE_STATE_FAILED: _ClassVar[FileState]
    FILE_STATE_CLOSED: _ClassVar[FileState]

class ResourceScopeState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    RESOURCE_SCOPE_STATE_UNSPECIFIED: _ClassVar[ResourceScopeState]
    RESOURCE_SCOPE_STATE_OPEN: _ClassVar[ResourceScopeState]
    RESOURCE_SCOPE_STATE_CANCELLING: _ClassVar[ResourceScopeState]
    RESOURCE_SCOPE_STATE_RELEASING: _ClassVar[ResourceScopeState]
    RESOURCE_SCOPE_STATE_RELEASED: _ClassVar[ResourceScopeState]
    RESOURCE_SCOPE_STATE_EXPIRED: _ClassVar[ResourceScopeState]
FILE_STATE_UNSPECIFIED: FileState
FILE_STATE_OPENING: FileState
FILE_STATE_OPEN: FileState
FILE_STATE_PINNED: FileState
FILE_STATE_CLOSING: FileState
FILE_STATE_FAILED: FileState
FILE_STATE_CLOSED: FileState
RESOURCE_SCOPE_STATE_UNSPECIFIED: ResourceScopeState
RESOURCE_SCOPE_STATE_OPEN: ResourceScopeState
RESOURCE_SCOPE_STATE_CANCELLING: ResourceScopeState
RESOURCE_SCOPE_STATE_RELEASING: ResourceScopeState
RESOURCE_SCOPE_STATE_RELEASED: ResourceScopeState
RESOURCE_SCOPE_STATE_EXPIRED: ResourceScopeState

class CompilationProfile(_message.Message):
    __slots__ = ("profile_id", "compile_arguments", "working_directory", "compilation_database", "frozen")
    PROFILE_ID_FIELD_NUMBER: _ClassVar[int]
    COMPILE_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    WORKING_DIRECTORY_FIELD_NUMBER: _ClassVar[int]
    COMPILATION_DATABASE_FIELD_NUMBER: _ClassVar[int]
    FROZEN_FIELD_NUMBER: _ClassVar[int]
    profile_id: str
    compile_arguments: _containers.RepeatedScalarFieldContainer[str]
    working_directory: str
    compilation_database: str
    frozen: bool
    def __init__(self, profile_id: _Optional[str] = ..., compile_arguments: _Optional[_Iterable[str]] = ..., working_directory: _Optional[str] = ..., compilation_database: _Optional[str] = ..., frozen: _Optional[bool] = ...) -> None: ...

class InputDescriptor(_message.Message):
    __slots__ = ("file_path", "profile", "source_bytes", "estimated_parse_bytes")
    FILE_PATH_FIELD_NUMBER: _ClassVar[int]
    PROFILE_FIELD_NUMBER: _ClassVar[int]
    SOURCE_BYTES_FIELD_NUMBER: _ClassVar[int]
    ESTIMATED_PARSE_BYTES_FIELD_NUMBER: _ClassVar[int]
    file_path: str
    profile: CompilationProfile
    source_bytes: int
    estimated_parse_bytes: int
    def __init__(self, file_path: _Optional[str] = ..., profile: _Optional[_Union[CompilationProfile, _Mapping]] = ..., source_bytes: _Optional[int] = ..., estimated_parse_bytes: _Optional[int] = ...) -> None: ...

class DiscoverFilesRequest(_message.Message):
    __slots__ = ("paths", "profile", "inputs", "max_inputs", "max_metadata_bytes")
    PATHS_FIELD_NUMBER: _ClassVar[int]
    PROFILE_FIELD_NUMBER: _ClassVar[int]
    INPUTS_FIELD_NUMBER: _ClassVar[int]
    MAX_INPUTS_FIELD_NUMBER: _ClassVar[int]
    MAX_METADATA_BYTES_FIELD_NUMBER: _ClassVar[int]
    paths: _containers.RepeatedScalarFieldContainer[str]
    profile: CompilationProfile
    inputs: _containers.RepeatedCompositeFieldContainer[InputDescriptor]
    max_inputs: int
    max_metadata_bytes: int
    def __init__(self, paths: _Optional[_Iterable[str]] = ..., profile: _Optional[_Union[CompilationProfile, _Mapping]] = ..., inputs: _Optional[_Iterable[_Union[InputDescriptor, _Mapping]]] = ..., max_inputs: _Optional[int] = ..., max_metadata_bytes: _Optional[int] = ...) -> None: ...

class DiscoverFilesResponse(_message.Message):
    __slots__ = ("inputs", "diagnostics", "metadata_bytes")
    INPUTS_FIELD_NUMBER: _ClassVar[int]
    DIAGNOSTICS_FIELD_NUMBER: _ClassVar[int]
    METADATA_BYTES_FIELD_NUMBER: _ClassVar[int]
    inputs: _containers.RepeatedCompositeFieldContainer[InputDescriptor]
    diagnostics: _containers.RepeatedScalarFieldContainer[str]
    metadata_bytes: int
    def __init__(self, inputs: _Optional[_Iterable[_Union[InputDescriptor, _Mapping]]] = ..., diagnostics: _Optional[_Iterable[str]] = ..., metadata_bytes: _Optional[int] = ...) -> None: ...

class FileInfo(_message.Message):
    __slots__ = ("lease_id", "input", "snapshot_id", "source_revision", "explicit_leases", "cursor_count", "active_work", "accounted_native_bytes", "state", "session_ids", "resource_scope_id", "expires_at", "root_session_id")
    LEASE_ID_FIELD_NUMBER: _ClassVar[int]
    INPUT_FIELD_NUMBER: _ClassVar[int]
    SNAPSHOT_ID_FIELD_NUMBER: _ClassVar[int]
    SOURCE_REVISION_FIELD_NUMBER: _ClassVar[int]
    EXPLICIT_LEASES_FIELD_NUMBER: _ClassVar[int]
    CURSOR_COUNT_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_WORK_FIELD_NUMBER: _ClassVar[int]
    ACCOUNTED_NATIVE_BYTES_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    SESSION_IDS_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_SCOPE_ID_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    ROOT_SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    lease_id: str
    input: InputDescriptor
    snapshot_id: str
    source_revision: str
    explicit_leases: int
    cursor_count: int
    active_work: int
    accounted_native_bytes: int
    state: FileState
    session_ids: _containers.RepeatedScalarFieldContainer[str]
    resource_scope_id: str
    expires_at: _timestamp_pb2.Timestamp
    root_session_id: str
    def __init__(self, lease_id: _Optional[str] = ..., input: _Optional[_Union[InputDescriptor, _Mapping]] = ..., snapshot_id: _Optional[str] = ..., source_revision: _Optional[str] = ..., explicit_leases: _Optional[int] = ..., cursor_count: _Optional[int] = ..., active_work: _Optional[int] = ..., accounted_native_bytes: _Optional[int] = ..., state: _Optional[_Union[FileState, str]] = ..., session_ids: _Optional[_Iterable[str]] = ..., resource_scope_id: _Optional[str] = ..., expires_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., root_session_id: _Optional[str] = ...) -> None: ...

class OpenFileRequest(_message.Message):
    __slots__ = ("input", "resource_scope_id")
    INPUT_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_SCOPE_ID_FIELD_NUMBER: _ClassVar[int]
    input: InputDescriptor
    resource_scope_id: str
    def __init__(self, input: _Optional[_Union[InputDescriptor, _Mapping]] = ..., resource_scope_id: _Optional[str] = ...) -> None: ...

class ListFilesRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ListFilesResponse(_message.Message):
    __slots__ = ("files",)
    FILES_FIELD_NUMBER: _ClassVar[int]
    files: _containers.RepeatedCompositeFieldContainer[FileInfo]
    def __init__(self, files: _Optional[_Iterable[_Union[FileInfo, _Mapping]]] = ...) -> None: ...

class DescribeFileRequest(_message.Message):
    __slots__ = ("lease_id", "session_id")
    LEASE_ID_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    lease_id: str
    session_id: str
    def __init__(self, lease_id: _Optional[str] = ..., session_id: _Optional[str] = ...) -> None: ...

class CloseFileRequest(_message.Message):
    __slots__ = ("lease_id", "session_id")
    LEASE_ID_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    lease_id: str
    session_id: str
    def __init__(self, lease_id: _Optional[str] = ..., session_id: _Optional[str] = ...) -> None: ...

class CloseFileResponse(_message.Message):
    __slots__ = ("released_leases", "closed_cursors", "remaining")
    RELEASED_LEASES_FIELD_NUMBER: _ClassVar[int]
    CLOSED_CURSORS_FIELD_NUMBER: _ClassVar[int]
    REMAINING_FIELD_NUMBER: _ClassVar[int]
    released_leases: int
    closed_cursors: int
    remaining: _containers.RepeatedCompositeFieldContainer[FileInfo]
    def __init__(self, released_leases: _Optional[int] = ..., closed_cursors: _Optional[int] = ..., remaining: _Optional[_Iterable[_Union[FileInfo, _Mapping]]] = ...) -> None: ...

class CloseAllFilesRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class RefreshFileRequest(_message.Message):
    __slots__ = ("lease_id", "session_id", "resource_scope_id")
    LEASE_ID_FIELD_NUMBER: _ClassVar[int]
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_SCOPE_ID_FIELD_NUMBER: _ClassVar[int]
    lease_id: str
    session_id: str
    resource_scope_id: str
    def __init__(self, lease_id: _Optional[str] = ..., session_id: _Optional[str] = ..., resource_scope_id: _Optional[str] = ...) -> None: ...

class FileHandleTarget(_message.Message):
    __slots__ = ("lease_id",)
    LEASE_ID_FIELD_NUMBER: _ClassVar[int]
    lease_id: str
    def __init__(self, lease_id: _Optional[str] = ...) -> None: ...

class OpenResourceScopeRequest(_message.Message):
    __slots__ = ("inputs", "memory_bytes", "jobs", "transient", "ttl_ms")
    INPUTS_FIELD_NUMBER: _ClassVar[int]
    MEMORY_BYTES_FIELD_NUMBER: _ClassVar[int]
    JOBS_FIELD_NUMBER: _ClassVar[int]
    TRANSIENT_FIELD_NUMBER: _ClassVar[int]
    TTL_MS_FIELD_NUMBER: _ClassVar[int]
    inputs: _containers.RepeatedCompositeFieldContainer[InputDescriptor]
    memory_bytes: int
    jobs: int
    transient: bool
    ttl_ms: int
    def __init__(self, inputs: _Optional[_Iterable[_Union[InputDescriptor, _Mapping]]] = ..., memory_bytes: _Optional[int] = ..., jobs: _Optional[int] = ..., transient: _Optional[bool] = ..., ttl_ms: _Optional[int] = ...) -> None: ...

class ResourceScopeRequest(_message.Message):
    __slots__ = ("resource_scope_id",)
    RESOURCE_SCOPE_ID_FIELD_NUMBER: _ClassVar[int]
    resource_scope_id: str
    def __init__(self, resource_scope_id: _Optional[str] = ...) -> None: ...

class ResourceScopeInfo(_message.Message):
    __slots__ = ("resource_scope_id", "state", "admitted_inputs", "reserved_bytes", "accounted_native_bytes", "file_leases", "result_cursors", "active_work", "result_buffer_bytes", "memory_limit_bytes", "jobs", "transient", "expires_at", "cleanup_acknowledged", "peak_accounted_bytes", "peak_reserved_bytes")
    RESOURCE_SCOPE_ID_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    ADMITTED_INPUTS_FIELD_NUMBER: _ClassVar[int]
    RESERVED_BYTES_FIELD_NUMBER: _ClassVar[int]
    ACCOUNTED_NATIVE_BYTES_FIELD_NUMBER: _ClassVar[int]
    FILE_LEASES_FIELD_NUMBER: _ClassVar[int]
    RESULT_CURSORS_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_WORK_FIELD_NUMBER: _ClassVar[int]
    RESULT_BUFFER_BYTES_FIELD_NUMBER: _ClassVar[int]
    MEMORY_LIMIT_BYTES_FIELD_NUMBER: _ClassVar[int]
    JOBS_FIELD_NUMBER: _ClassVar[int]
    TRANSIENT_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    CLEANUP_ACKNOWLEDGED_FIELD_NUMBER: _ClassVar[int]
    PEAK_ACCOUNTED_BYTES_FIELD_NUMBER: _ClassVar[int]
    PEAK_RESERVED_BYTES_FIELD_NUMBER: _ClassVar[int]
    resource_scope_id: str
    state: ResourceScopeState
    admitted_inputs: int
    reserved_bytes: int
    accounted_native_bytes: int
    file_leases: int
    result_cursors: int
    active_work: int
    result_buffer_bytes: int
    memory_limit_bytes: int
    jobs: int
    transient: bool
    expires_at: _timestamp_pb2.Timestamp
    cleanup_acknowledged: bool
    peak_accounted_bytes: int
    peak_reserved_bytes: int
    def __init__(self, resource_scope_id: _Optional[str] = ..., state: _Optional[_Union[ResourceScopeState, str]] = ..., admitted_inputs: _Optional[int] = ..., reserved_bytes: _Optional[int] = ..., accounted_native_bytes: _Optional[int] = ..., file_leases: _Optional[int] = ..., result_cursors: _Optional[int] = ..., active_work: _Optional[int] = ..., result_buffer_bytes: _Optional[int] = ..., memory_limit_bytes: _Optional[int] = ..., jobs: _Optional[int] = ..., transient: _Optional[bool] = ..., expires_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., cleanup_acknowledged: _Optional[bool] = ..., peak_accounted_bytes: _Optional[int] = ..., peak_reserved_bytes: _Optional[int] = ...) -> None: ...

class ResourceStatusRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ResourceStatusResponse(_message.Message):
    __slots__ = ("opened_inputs", "explicit_file_leases", "result_cursors", "active_work", "accounted_native_bytes", "reserved_bytes", "result_buffer_bytes", "queued_work", "reusable_snapshots", "reusable_memory_bytes", "resident_memory_bytes", "max_inputs", "max_memory_bytes", "max_result_rows", "max_result_bytes", "max_manifest_inputs", "max_manifest_bytes", "scopes", "legacy_accounting_separate")
    OPENED_INPUTS_FIELD_NUMBER: _ClassVar[int]
    EXPLICIT_FILE_LEASES_FIELD_NUMBER: _ClassVar[int]
    RESULT_CURSORS_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_WORK_FIELD_NUMBER: _ClassVar[int]
    ACCOUNTED_NATIVE_BYTES_FIELD_NUMBER: _ClassVar[int]
    RESERVED_BYTES_FIELD_NUMBER: _ClassVar[int]
    RESULT_BUFFER_BYTES_FIELD_NUMBER: _ClassVar[int]
    QUEUED_WORK_FIELD_NUMBER: _ClassVar[int]
    REUSABLE_SNAPSHOTS_FIELD_NUMBER: _ClassVar[int]
    REUSABLE_MEMORY_BYTES_FIELD_NUMBER: _ClassVar[int]
    RESIDENT_MEMORY_BYTES_FIELD_NUMBER: _ClassVar[int]
    MAX_INPUTS_FIELD_NUMBER: _ClassVar[int]
    MAX_MEMORY_BYTES_FIELD_NUMBER: _ClassVar[int]
    MAX_RESULT_ROWS_FIELD_NUMBER: _ClassVar[int]
    MAX_RESULT_BYTES_FIELD_NUMBER: _ClassVar[int]
    MAX_MANIFEST_INPUTS_FIELD_NUMBER: _ClassVar[int]
    MAX_MANIFEST_BYTES_FIELD_NUMBER: _ClassVar[int]
    SCOPES_FIELD_NUMBER: _ClassVar[int]
    LEGACY_ACCOUNTING_SEPARATE_FIELD_NUMBER: _ClassVar[int]
    opened_inputs: int
    explicit_file_leases: int
    result_cursors: int
    active_work: int
    accounted_native_bytes: int
    reserved_bytes: int
    result_buffer_bytes: int
    queued_work: int
    reusable_snapshots: int
    reusable_memory_bytes: int
    resident_memory_bytes: int
    max_inputs: int
    max_memory_bytes: int
    max_result_rows: int
    max_result_bytes: int
    max_manifest_inputs: int
    max_manifest_bytes: int
    scopes: _containers.RepeatedCompositeFieldContainer[ResourceScopeInfo]
    legacy_accounting_separate: bool
    def __init__(self, opened_inputs: _Optional[int] = ..., explicit_file_leases: _Optional[int] = ..., result_cursors: _Optional[int] = ..., active_work: _Optional[int] = ..., accounted_native_bytes: _Optional[int] = ..., reserved_bytes: _Optional[int] = ..., result_buffer_bytes: _Optional[int] = ..., queued_work: _Optional[int] = ..., reusable_snapshots: _Optional[int] = ..., reusable_memory_bytes: _Optional[int] = ..., resident_memory_bytes: _Optional[int] = ..., max_inputs: _Optional[int] = ..., max_memory_bytes: _Optional[int] = ..., max_result_rows: _Optional[int] = ..., max_result_bytes: _Optional[int] = ..., max_manifest_inputs: _Optional[int] = ..., max_manifest_bytes: _Optional[int] = ..., scopes: _Optional[_Iterable[_Union[ResourceScopeInfo, _Mapping]]] = ..., legacy_accounting_separate: _Optional[bool] = ...) -> None: ...
