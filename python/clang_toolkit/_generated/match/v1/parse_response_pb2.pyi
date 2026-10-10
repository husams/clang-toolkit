import datetime

from google.protobuf import timestamp_pb2 as _timestamp_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ParseResponse(_message.Message):
    __slots__ = ("session_id", "result_revision", "expires_at", "file_lease_id")
    SESSION_ID_FIELD_NUMBER: _ClassVar[int]
    RESULT_REVISION_FIELD_NUMBER: _ClassVar[int]
    EXPIRES_AT_FIELD_NUMBER: _ClassVar[int]
    FILE_LEASE_ID_FIELD_NUMBER: _ClassVar[int]
    session_id: str
    result_revision: int
    expires_at: _timestamp_pb2.Timestamp
    file_lease_id: str
    def __init__(self, session_id: _Optional[str] = ..., result_revision: _Optional[int] = ..., expires_at: _Optional[_Union[datetime.datetime, _timestamp_pb2.Timestamp, _Mapping]] = ..., file_lease_id: _Optional[str] = ...) -> None: ...
