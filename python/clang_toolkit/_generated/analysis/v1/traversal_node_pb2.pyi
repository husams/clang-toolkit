from ...match.v1 import match_result_pb2 as _match_result_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TraversalNode(_message.Message):
    __slots__ = ("parent_index", "depth", "value")
    PARENT_INDEX_FIELD_NUMBER: _ClassVar[int]
    DEPTH_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    parent_index: int
    depth: int
    value: _match_result_pb2.MatchBinding
    def __init__(self, parent_index: _Optional[int] = ..., depth: _Optional[int] = ..., value: _Optional[_Union[_match_result_pb2.MatchBinding, _Mapping]] = ...) -> None: ...
