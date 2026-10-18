from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class IndexState(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    INDEX_STATE_UNSPECIFIED: _ClassVar[IndexState]
    INDEX_STATE_IDLE: _ClassVar[IndexState]
    INDEX_STATE_QUEUED: _ClassVar[IndexState]
    INDEX_STATE_INDEXING: _ClassVar[IndexState]
    INDEX_STATE_PAUSED: _ClassVar[IndexState]
    INDEX_STATE_COMPLETE: _ClassVar[IndexState]
    INDEX_STATE_CANCELLED: _ClassVar[IndexState]
    INDEX_STATE_FAILED: _ClassVar[IndexState]
    INDEX_STATE_CHECKING: _ClassVar[IndexState]
INDEX_STATE_UNSPECIFIED: IndexState
INDEX_STATE_IDLE: IndexState
INDEX_STATE_QUEUED: IndexState
INDEX_STATE_INDEXING: IndexState
INDEX_STATE_PAUSED: IndexState
INDEX_STATE_COMPLETE: IndexState
INDEX_STATE_CANCELLED: IndexState
INDEX_STATE_FAILED: IndexState
INDEX_STATE_CHECKING: IndexState

class StartProjectIndexRequest(_message.Message):
    __slots__ = ("project_root", "compile_commands", "poll_interval_seconds")
    PROJECT_ROOT_FIELD_NUMBER: _ClassVar[int]
    COMPILE_COMMANDS_FIELD_NUMBER: _ClassVar[int]
    POLL_INTERVAL_SECONDS_FIELD_NUMBER: _ClassVar[int]
    project_root: str
    compile_commands: str
    poll_interval_seconds: int
    def __init__(self, project_root: _Optional[str] = ..., compile_commands: _Optional[str] = ..., poll_interval_seconds: _Optional[int] = ...) -> None: ...

class ProjectIndexRequest(_message.Message):
    __slots__ = ("project_root",)
    PROJECT_ROOT_FIELD_NUMBER: _ClassVar[int]
    project_root: str
    def __init__(self, project_root: _Optional[str] = ...) -> None: ...

class ListProjectIndexesRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class ListProjectIndexesResponse(_message.Message):
    __slots__ = ("projects", "total_count")
    PROJECTS_FIELD_NUMBER: _ClassVar[int]
    TOTAL_COUNT_FIELD_NUMBER: _ClassVar[int]
    projects: _containers.RepeatedCompositeFieldContainer[ProjectIndexStatus]
    total_count: int
    def __init__(self, projects: _Optional[_Iterable[_Union[ProjectIndexStatus, _Mapping]]] = ..., total_count: _Optional[int] = ...) -> None: ...

class ProjectIndexStatus(_message.Message):
    __slots__ = ("project_root", "state", "translation_units_total", "translation_units_completed", "translation_units_skipped", "translation_units_failed", "current_translation_unit", "error", "last_reconciled_unix_seconds", "revision", "translation_units_pending", "paused_reason", "translation_units_indexed", "translation_units_indexing")
    PROJECT_ROOT_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    TRANSLATION_UNITS_TOTAL_FIELD_NUMBER: _ClassVar[int]
    TRANSLATION_UNITS_COMPLETED_FIELD_NUMBER: _ClassVar[int]
    TRANSLATION_UNITS_SKIPPED_FIELD_NUMBER: _ClassVar[int]
    TRANSLATION_UNITS_FAILED_FIELD_NUMBER: _ClassVar[int]
    CURRENT_TRANSLATION_UNIT_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    LAST_RECONCILED_UNIX_SECONDS_FIELD_NUMBER: _ClassVar[int]
    REVISION_FIELD_NUMBER: _ClassVar[int]
    TRANSLATION_UNITS_PENDING_FIELD_NUMBER: _ClassVar[int]
    PAUSED_REASON_FIELD_NUMBER: _ClassVar[int]
    TRANSLATION_UNITS_INDEXED_FIELD_NUMBER: _ClassVar[int]
    TRANSLATION_UNITS_INDEXING_FIELD_NUMBER: _ClassVar[int]
    project_root: str
    state: IndexState
    translation_units_total: int
    translation_units_completed: int
    translation_units_skipped: int
    translation_units_failed: int
    current_translation_unit: str
    error: str
    last_reconciled_unix_seconds: int
    revision: int
    translation_units_pending: int
    paused_reason: str
    translation_units_indexed: int
    translation_units_indexing: int
    def __init__(self, project_root: _Optional[str] = ..., state: _Optional[_Union[IndexState, str]] = ..., translation_units_total: _Optional[int] = ..., translation_units_completed: _Optional[int] = ..., translation_units_skipped: _Optional[int] = ..., translation_units_failed: _Optional[int] = ..., current_translation_unit: _Optional[str] = ..., error: _Optional[str] = ..., last_reconciled_unix_seconds: _Optional[int] = ..., revision: _Optional[int] = ..., translation_units_pending: _Optional[int] = ..., paused_reason: _Optional[str] = ..., translation_units_indexed: _Optional[int] = ..., translation_units_indexing: _Optional[int] = ...) -> None: ...

class FindSymbolsRequest(_message.Message):
    __slots__ = ("project_root", "query", "limit", "match_mode", "kind")
    class MatchMode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        MATCH_MODE_EXACT: _ClassVar[FindSymbolsRequest.MatchMode]
        MATCH_MODE_PREFIX: _ClassVar[FindSymbolsRequest.MatchMode]
    MATCH_MODE_EXACT: FindSymbolsRequest.MatchMode
    MATCH_MODE_PREFIX: FindSymbolsRequest.MatchMode
    class Kind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        KIND_ANY: _ClassVar[FindSymbolsRequest.Kind]
        KIND_FUNCTION: _ClassVar[FindSymbolsRequest.Kind]
        KIND_CLASS: _ClassVar[FindSymbolsRequest.Kind]
        KIND_VARIABLE: _ClassVar[FindSymbolsRequest.Kind]
    KIND_ANY: FindSymbolsRequest.Kind
    KIND_FUNCTION: FindSymbolsRequest.Kind
    KIND_CLASS: FindSymbolsRequest.Kind
    KIND_VARIABLE: FindSymbolsRequest.Kind
    PROJECT_ROOT_FIELD_NUMBER: _ClassVar[int]
    QUERY_FIELD_NUMBER: _ClassVar[int]
    LIMIT_FIELD_NUMBER: _ClassVar[int]
    MATCH_MODE_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    project_root: str
    query: str
    limit: int
    match_mode: FindSymbolsRequest.MatchMode
    kind: FindSymbolsRequest.Kind
    def __init__(self, project_root: _Optional[str] = ..., query: _Optional[str] = ..., limit: _Optional[int] = ..., match_mode: _Optional[_Union[FindSymbolsRequest.MatchMode, str]] = ..., kind: _Optional[_Union[FindSymbolsRequest.Kind, str]] = ...) -> None: ...

class LookupSymbolRequest(_message.Message):
    __slots__ = ("project_root", "usr")
    PROJECT_ROOT_FIELD_NUMBER: _ClassVar[int]
    USR_FIELD_NUMBER: _ClassVar[int]
    project_root: str
    usr: str
    def __init__(self, project_root: _Optional[str] = ..., usr: _Optional[str] = ...) -> None: ...

class Symbol(_message.Message):
    __slots__ = ("usr", "name", "qualified_name", "kind", "file_path", "line", "column", "signature", "translation_unit", "compile_context", "byte_offset", "is_definition", "index_revision", "stale")
    USR_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    QUALIFIED_NAME_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    FILE_PATH_FIELD_NUMBER: _ClassVar[int]
    LINE_FIELD_NUMBER: _ClassVar[int]
    COLUMN_FIELD_NUMBER: _ClassVar[int]
    SIGNATURE_FIELD_NUMBER: _ClassVar[int]
    TRANSLATION_UNIT_FIELD_NUMBER: _ClassVar[int]
    COMPILE_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    BYTE_OFFSET_FIELD_NUMBER: _ClassVar[int]
    IS_DEFINITION_FIELD_NUMBER: _ClassVar[int]
    INDEX_REVISION_FIELD_NUMBER: _ClassVar[int]
    STALE_FIELD_NUMBER: _ClassVar[int]
    usr: str
    name: str
    qualified_name: str
    kind: str
    file_path: str
    line: int
    column: int
    signature: str
    translation_unit: str
    compile_context: str
    byte_offset: int
    is_definition: bool
    index_revision: int
    stale: bool
    def __init__(self, usr: _Optional[str] = ..., name: _Optional[str] = ..., qualified_name: _Optional[str] = ..., kind: _Optional[str] = ..., file_path: _Optional[str] = ..., line: _Optional[int] = ..., column: _Optional[int] = ..., signature: _Optional[str] = ..., translation_unit: _Optional[str] = ..., compile_context: _Optional[str] = ..., byte_offset: _Optional[int] = ..., is_definition: _Optional[bool] = ..., index_revision: _Optional[int] = ..., stale: _Optional[bool] = ...) -> None: ...

class FindSymbolsResponse(_message.Message):
    __slots__ = ("symbols", "revision", "stale", "translation_units_indexed", "translation_units_total", "truncated")
    SYMBOLS_FIELD_NUMBER: _ClassVar[int]
    REVISION_FIELD_NUMBER: _ClassVar[int]
    STALE_FIELD_NUMBER: _ClassVar[int]
    TRANSLATION_UNITS_INDEXED_FIELD_NUMBER: _ClassVar[int]
    TRANSLATION_UNITS_TOTAL_FIELD_NUMBER: _ClassVar[int]
    TRUNCATED_FIELD_NUMBER: _ClassVar[int]
    symbols: _containers.RepeatedCompositeFieldContainer[Symbol]
    revision: int
    stale: bool
    translation_units_indexed: int
    translation_units_total: int
    truncated: bool
    def __init__(self, symbols: _Optional[_Iterable[_Union[Symbol, _Mapping]]] = ..., revision: _Optional[int] = ..., stale: _Optional[bool] = ..., translation_units_indexed: _Optional[int] = ..., translation_units_total: _Optional[int] = ..., truncated: _Optional[bool] = ...) -> None: ...

class IndexWorkerRequest(_message.Message):
    __slots__ = ("source", "compile_commands_directory", "list_translation_units", "working_directory", "compile_arguments", "header_cache_directory", "precomputed_include_inventories")
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    COMPILE_COMMANDS_DIRECTORY_FIELD_NUMBER: _ClassVar[int]
    LIST_TRANSLATION_UNITS_FIELD_NUMBER: _ClassVar[int]
    WORKING_DIRECTORY_FIELD_NUMBER: _ClassVar[int]
    COMPILE_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    HEADER_CACHE_DIRECTORY_FIELD_NUMBER: _ClassVar[int]
    PRECOMPUTED_INCLUDE_INVENTORIES_FIELD_NUMBER: _ClassVar[int]
    source: str
    compile_commands_directory: str
    list_translation_units: bool
    working_directory: str
    compile_arguments: _containers.RepeatedScalarFieldContainer[str]
    header_cache_directory: str
    precomputed_include_inventories: _containers.RepeatedCompositeFieldContainer[IndexWorkerDependency]
    def __init__(self, source: _Optional[str] = ..., compile_commands_directory: _Optional[str] = ..., list_translation_units: _Optional[bool] = ..., working_directory: _Optional[str] = ..., compile_arguments: _Optional[_Iterable[str]] = ..., header_cache_directory: _Optional[str] = ..., precomputed_include_inventories: _Optional[_Iterable[_Union[IndexWorkerDependency, _Mapping]]] = ...) -> None: ...

class IndexWorkerTranslationUnit(_message.Message):
    __slots__ = ("source", "compile_context", "working_directory", "compile_arguments")
    SOURCE_FIELD_NUMBER: _ClassVar[int]
    COMPILE_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    WORKING_DIRECTORY_FIELD_NUMBER: _ClassVar[int]
    COMPILE_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    source: str
    compile_context: str
    working_directory: str
    compile_arguments: _containers.RepeatedScalarFieldContainer[str]
    def __init__(self, source: _Optional[str] = ..., compile_context: _Optional[str] = ..., working_directory: _Optional[str] = ..., compile_arguments: _Optional[_Iterable[str]] = ...) -> None: ...

class IndexWorkerDependency(_message.Message):
    __slots__ = ("path", "sha256")
    PATH_FIELD_NUMBER: _ClassVar[int]
    SHA256_FIELD_NUMBER: _ClassVar[int]
    path: str
    sha256: str
    def __init__(self, path: _Optional[str] = ..., sha256: _Optional[str] = ...) -> None: ...

class IndexWorkerResponse(_message.Message):
    __slots__ = ("success", "error", "compile_context", "dependencies", "symbols", "translation_units", "reused_header_symbols")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    ERROR_FIELD_NUMBER: _ClassVar[int]
    COMPILE_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    DEPENDENCIES_FIELD_NUMBER: _ClassVar[int]
    SYMBOLS_FIELD_NUMBER: _ClassVar[int]
    TRANSLATION_UNITS_FIELD_NUMBER: _ClassVar[int]
    REUSED_HEADER_SYMBOLS_FIELD_NUMBER: _ClassVar[int]
    success: bool
    error: str
    compile_context: str
    dependencies: _containers.RepeatedCompositeFieldContainer[IndexWorkerDependency]
    symbols: _containers.RepeatedCompositeFieldContainer[Symbol]
    translation_units: _containers.RepeatedCompositeFieldContainer[IndexWorkerTranslationUnit]
    reused_header_symbols: int
    def __init__(self, success: _Optional[bool] = ..., error: _Optional[str] = ..., compile_context: _Optional[str] = ..., dependencies: _Optional[_Iterable[_Union[IndexWorkerDependency, _Mapping]]] = ..., symbols: _Optional[_Iterable[_Union[Symbol, _Mapping]]] = ..., translation_units: _Optional[_Iterable[_Union[IndexWorkerTranslationUnit, _Mapping]]] = ..., reused_header_symbols: _Optional[int] = ...) -> None: ...
