import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from . import match_result_pb2 as _match_result_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class MatchStreamEvent(_message.Message):
    __slots__ = ("row", "completed")
    ROW_FIELD_NUMBER: _ClassVar[int]
    COMPLETED_FIELD_NUMBER: _ClassVar[int]
    row: _match_result_pb2.MatchResult
    completed: MatchStreamCompleted
    def __init__(self, row: _Optional[_Union[_match_result_pb2.MatchResult, _Mapping]] = ..., completed: _Optional[_Union[MatchStreamCompleted, _Mapping]] = ...) -> None: ...

class MatchStreamCompleted(_message.Message):
    __slots__ = ("session_id", "result_revision", "expires_at", "row_count")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    RESULT_REVISION_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    ROW_COUNT_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    result_revision: int
    expires_at: _timestamp_pb2.Timestamp
    row_count: int
    def __init__(self, session_id: _Optional[str] = ..., result_revision: _Optional[int] = ..., expires_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., row_count: _Optional[int] = ...) -> None: ...
