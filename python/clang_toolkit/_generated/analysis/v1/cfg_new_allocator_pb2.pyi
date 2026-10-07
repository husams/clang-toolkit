from ...ast.v1 import semantic_types_pb2 as _semantic_types_pb2
from ...ast.v1 import semantic_pb2 as _semantic_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CfgNewAllocator(_message.Message):
    __slots__ = ("allocation",)
    ALLOCATION_FIELD_NUMBER: _ClassVar[int]
    allocation: _semantic_pb2.ExpressionValue
    def __init__(self, allocation: _Optional[_Union[_semantic_pb2.ExpressionValue, _Mapping]] = ...) -> None: ...
