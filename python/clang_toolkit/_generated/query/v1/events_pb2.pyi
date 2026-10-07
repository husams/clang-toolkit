from . import errors_pb2 as _errors_pb2  # noqa: E402, F401
from ...match.v1 import match_result_pb2 as _match_result_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class Queued(_message.Message):
    __slots__ = ("pending_requests",)
    PENDING_REQUESTS_FIELD_NUMBER: _ClassVar[int]
    pending_requests: int
    def __init__(self, pending_requests: _Optional[int] = ...) -> None: ...

class Started(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class Progress(_message.Message):
    __slots__ = ("file", "profile", "completed_files", "accepted_files")
    FILE_FIELD_NUMBER: _ClassVar[int]
    PROFILE_FIELD_NUMBER: _ClassVar[int]
    COMPLETED_FILES_FIELD_NUMBER: _ClassVar[int]
    ACCEPTED_FILES_FIELD_NUMBER: _ClassVar[int]
    file: str
    profile: str
    completed_files: int
    accepted_files: int
    def __init__(self, file: _Optional[str] = ..., profile: _Optional[str] = ..., completed_files: _Optional[int] = ..., accepted_files: _Optional[int] = ...) -> None: ...

class SemanticBinding(_message.Message):
    __slots__ = ("kind", "name", "type")
    KIND_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    kind: str
    name: str
    type: str
    def __init__(self, kind: _Optional[str] = ..., name: _Optional[str] = ..., type: _Optional[str] = ...) -> None: ...

class MatchEvent(_message.Message):
    __slots__ = ("file", "profile", "bindings", "semantic_result")
    class BindingsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: SemanticBinding
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[SemanticBinding, _Mapping]] = ...) -> None: ...
    FILE_FIELD_NUMBER: _ClassVar[int]
    PROFILE_FIELD_NUMBER: _ClassVar[int]
    BINDINGS_FIELD_NUMBER: _ClassVar[int]
    SEMANTIC_RESULT_FIELD_NUMBER: _ClassVar[int]
    file: str
    profile: str
    bindings: _containers.MessageMap[str, SemanticBinding]
    semantic_result: _match_result_pb2.MatchResult
    def __init__(self, file: _Optional[str] = ..., profile: _Optional[str] = ..., bindings: _Optional[_Mapping[str, SemanticBinding]] = ..., semantic_result: _Optional[_Union[_match_result_pb2.MatchResult, _Mapping]] = ...) -> None: ...

class Completed(_message.Message):
    __slots__ = ("completed_files", "match_count")
    COMPLETED_FILES_FIELD_NUMBER: _ClassVar[int]
    MATCH_COUNT_FIELD_NUMBER: _ClassVar[int]
    completed_files: int
    match_count: int
    def __init__(self, completed_files: _Optional[int] = ..., match_count: _Optional[int] = ...) -> None: ...

class Control(_message.Message):
    __slots__ = ("action",)
    ACTION_FIELD_NUMBER: _ClassVar[int]
    action: str
    def __init__(self, action: _Optional[str] = ...) -> None: ...

class QueryEvent(_message.Message):
    __slots__ = ("request_id", "queued", "started", "progress", "match", "completed", "rejected", "control")
    REQUEST_ID_FIELD_NUMBER: _ClassVar[int]
    QUEUED_FIELD_NUMBER: _ClassVar[int]
    STARTED_FIELD_NUMBER: _ClassVar[int]
    PROGRESS_FIELD_NUMBER: _ClassVar[int]
    MATCH_FIELD_NUMBER: _ClassVar[int]
    COMPLETED_FIELD_NUMBER: _ClassVar[int]
    REJECTED_FIELD_NUMBER: _ClassVar[int]
    CONTROL_FIELD_NUMBER: _ClassVar[int]
    request_id: str
    queued: Queued
    started: Started
    progress: Progress
    match: MatchEvent
    completed: Completed
    rejected: _errors_pb2.Rejected
    control: Control
    def __init__(self, request_id: _Optional[str] = ..., queued: _Optional[_Union[Queued, _Mapping]] = ..., started: _Optional[_Union[Started, _Mapping]] = ..., progress: _Optional[_Union[Progress, _Mapping]] = ..., match: _Optional[_Union[MatchEvent, _Mapping]] = ..., completed: _Optional[_Union[Completed, _Mapping]] = ..., rejected: _Optional[_Union[_errors_pb2.Rejected, _Mapping]] = ..., control: _Optional[_Union[Control, _Mapping]] = ...) -> None: ...
