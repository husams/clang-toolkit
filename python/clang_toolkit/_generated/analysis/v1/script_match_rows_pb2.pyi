from ...match.v1 import match_result_pb2 as _match_result_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class ScriptMatchRows(_message.Message):
    __slots__ = ("rows",)
    ROWS_FIELD_NUMBER: _ClassVar[int]
    rows: _containers.RepeatedCompositeFieldContainer[_match_result_pb2.MatchResult]
    def __init__(self, rows: _Optional[_Iterable[_Union[_match_result_pb2.MatchResult, _Mapping]]] = ...) -> None: ...
