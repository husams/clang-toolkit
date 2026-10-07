import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from . import match_result_pb2 as _match_result_pb2
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
    __slots__ = ("file_path", "compile_arguments", "working_directory")
    FILE_PATH_FIELD_NUMBER: _ClassVar[int]
    COMPILE_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    WORKING_DIRECTORY_FIELD_NUMBER: _ClassVar[int]
    file_path: str
    compile_arguments: _containers.RepeatedScalarFieldContainer[str]
    working_directory: str
    def __init__(self, file_path: _Optional[str] = ..., compile_arguments: _Optional[_Iterable[str]] = ..., working_directory: _Optional[str] = ...) -> None: ...

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
