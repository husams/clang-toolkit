import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from . import match_result_pb2 as _match_result_pb2
from . import match_stream_pb2 as _match_stream_pb2
from . import parse_request_pb2 as _parse_request_pb2
from . import parse_response_pb2 as _parse_response_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class MatchTraversalMode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    MATCH_TRAVERSAL_MODE_UNSPECIFIED: _ClassVar[MatchTraversalMode]
    MATCH_TRAVERSAL_MODE_AS_IS: _ClassVar[MatchTraversalMode]
    MATCH_TRAVERSAL_MODE_IGNORE_UNLESS_SPELLED_IN_SOURCE: _ClassVar[MatchTraversalMode]
MATCH_TRAVERSAL_MODE_UNSPECIFIED: MatchTraversalMode
MATCH_TRAVERSAL_MODE_AS_IS: MatchTraversalMode
MATCH_TRAVERSAL_MODE_IGNORE_UNLESS_SPELLED_IN_SOURCE: MatchTraversalMode

class MatchRequest(_message.Message):
    __slots__ = ("query", "file", "session", "binding", "traversal_mode", "preserve_source")
    QUERY_FIELD_NUMBER: _ClassVar[int]
    FILE_FIELD_NUMBER: _ClassVar[int]
    SESSION_FIELD_NUMBER: _ClassVar[int]
    BINDING_FIELD_NUMBER: _ClassVar[int]
    TRAVERSAL_MODE_FIELD_NUMBER: _ClassVar[int]
    PRESERVE_SOURCE_FIELD_NUMBER: _ClassVar[int]
    query: str
    file: FileMatchTarget
    session: SessionMatchTarget
    binding: BindingMatchTarget
    traversal_mode: MatchTraversalMode
    preserve_source: bool
    def __init__(self, query: _Optional[str] = ..., file: _Optional[_Union[FileMatchTarget, _Mapping]] = ..., session: _Optional[_Union[SessionMatchTarget, _Mapping]] = ..., binding: _Optional[_Union[BindingMatchTarget, _Mapping]] = ..., traversal_mode: _Optional[_Union[MatchTraversalMode, str]] = ..., preserve_source: _Optional[bool] = ...) -> None: ...

class FileMatchTarget(_message.Message):
    __slots__ = ("file_path", "compile_arguments", "working_directory", "compilation_database")
    FILE_PATH_FIELD_NUMBER: _ClassVar[int]
    COMPILE_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    WORKING_DIRECTORY_FIELD_NUMBER: _ClassVar[int]
    COMPILATION_DATABASE_FIELD_NUMBER: _ClassVar[int]
    file_path: str
    compile_arguments: _containers.RepeatedScalarFieldContainer[str]
    working_directory: str
    compilation_database: str
    def __init__(self, file_path: _Optional[str] = ..., compile_arguments: _Optional[_Iterable[str]] = ..., working_directory: _Optional[str] = ..., compilation_database: _Optional[str] = ...) -> None: ...

class SessionMatchTarget(_message.Message):
    __slots__ = ("session_id", "expected_result_revision")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    EXPECTED_RESULT_REVISION_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    expected_result_revision: int
    def __init__(self, session_id: _Optional[str] = ..., expected_result_revision: _Optional[int] = ...) -> None: ...

class BindingMatchTarget(_message.Message):
    __slots__ = ("session_id", "bind", "match_index", "scope", "expected_result_revision")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    BIND_FIELD_NUMBER: _ClassVar[int]
    MATCH_INDEX_FIELD_NUMBER: _ClassVar[int]
    SCOPE_FIELD_NUMBER: _ClassVar[int]
    EXPECTED_RESULT_REVISION_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    bind: str
    match_index: int
    scope: _match_result_pb2.BindingMatchScope
    expected_result_revision: int
    def __init__(self, session_id: _Optional[str] = ..., bind: _Optional[str] = ..., match_index: _Optional[int] = ..., scope: _Optional[_Union[_match_result_pb2.BindingMatchScope, str]] = ..., expected_result_revision: _Optional[int] = ...) -> None: ...

class MatchResponse(_message.Message):
    __slots__ = ("session_id", "result_revision", "results", "expires_at")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    RESULT_REVISION_FIELD_NUMBER: _ClassVar[int]
    RESULTS_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    result_revision: int
    results: _containers.RepeatedCompositeFieldContainer[_match_result_pb2.MatchResult]
    expires_at: _timestamp_pb2.Timestamp
    def __init__(self, session_id: _Optional[str] = ..., result_revision: _Optional[int] = ..., results: _Optional[_Iterable[_Union[_match_result_pb2.MatchResult, _Mapping]]] = ..., expires_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class CloseSessionRequest(_message.Message):
    __slots__ = ("session_id",)
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    def __init__(self, session_id: _Optional[str] = ...) -> None: ...

class CloseSessionResponse(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ListSessionsRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ListSessionsResponse(_message.Message):
    __slots__ = ("sessions",)
    SESSIONS_FIELD_NUMBER: _ClassVar[int]
    sessions: _containers.RepeatedCompositeFieldContainer[SessionInfo]
    def __init__(self, sessions: _Optional[_Iterable[_Union[SessionInfo, _Mapping]]] = ...) -> None: ...

class AttachSessionRequest(_message.Message):
    __slots__ = ("session_id",)
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    def __init__(self, session_id: _Optional[str] = ...) -> None: ...

class SessionInfo(_message.Message):
    __slots__ = ("session_id", "result_revision", "file_path", "row_count", "binding_names", "expires_at")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    RESULT_REVISION_FIELD_NUMBER: _ClassVar[int]
    FILE_PATH_FIELD_NUMBER: _ClassVar[int]
    ROW_COUNT_FIELD_NUMBER: _ClassVar[int]
    BINDING_NAMES_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    result_revision: int
    file_path: str
    row_count: int
    binding_names: _containers.RepeatedScalarFieldContainer[str]
    expires_at: _timestamp_pb2.Timestamp
    def __init__(self, session_id: _Optional[str] = ..., result_revision: _Optional[int] = ..., file_path: _Optional[str] = ..., row_count: _Optional[int] = ..., binding_names: _Optional[_Iterable[str]] = ..., expires_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ...) -> None: ...

class ServerStatusRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

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

class ServerStatusResponse(_message.Message):
    __slots__ = ("uptime_ms", "resident_memory_bytes", "active_sessions", "retained_memory_bytes", "max_sessions", "max_retained_memory_bytes", "cache")
    UPTIME_MS_FIELD_NUMBER: _ClassVar[int]
    RESIDENT_MEMORY_BYTES_FIELD_NUMBER: _ClassVar[int]
    ACTIVE_SESSIONS_FIELD_NUMBER: _ClassVar[int]
    RETAINED_MEMORY_BYTES_FIELD_NUMBER: _ClassVar[int]
    MAX_SESSIONS_FIELD_NUMBER: _ClassVar[int]
    MAX_RETAINED_MEMORY_BYTES_FIELD_NUMBER: _ClassVar[int]
    CACHE_FIELD_NUMBER: _ClassVar[int]
    uptime_ms: int
    resident_memory_bytes: int
    active_sessions: int
    retained_memory_bytes: int
    max_sessions: int
    max_retained_memory_bytes: int
    cache: CacheResources
    def __init__(self, uptime_ms: _Optional[int] = ..., resident_memory_bytes: _Optional[int] = ..., active_sessions: _Optional[int] = ..., retained_memory_bytes: _Optional[int] = ..., max_sessions: _Optional[int] = ..., max_retained_memory_bytes: _Optional[int] = ..., cache: _Optional[_Union[CacheResources, _Mapping]] = ...) -> None: ...

class PruneCachesRequest(_message.Message):
    __slots__ = ("memory", "disk")
    MEMORY_FIELD_NUMBER: _ClassVar[int]
    DISK_FIELD_NUMBER: _ClassVar[int]
    memory: bool
    disk: bool
    def __init__(self, memory: _Optional[bool] = ..., disk: _Optional[bool] = ...) -> None: ...

class PruneCachesResponse(_message.Message):
    __slots__ = ("before", "after")
    BEFORE_FIELD_NUMBER: _ClassVar[int]
    AFTER_FIELD_NUMBER: _ClassVar[int]
    before: CacheResources
    after: CacheResources
    def __init__(self, before: _Optional[_Union[CacheResources, _Mapping]] = ..., after: _Optional[_Union[CacheResources, _Mapping]] = ...) -> None: ...
