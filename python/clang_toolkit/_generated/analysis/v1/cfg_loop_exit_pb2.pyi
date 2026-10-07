from ...ast.v1 import semantic_types_pb2 as _semantic_types_pb2
from ...ast.v1 import semantic_pb2 as _semantic_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CfgLoopExit(_message.Message):
    __slots__ = ("loop",)
    LOOP_FIELD_NUMBER: _ClassVar[int]
    loop: _semantic_pb2.StatementValue
    def __init__(self, loop: _Optional[_Union[_semantic_pb2.StatementValue, _Mapping]] = ...) -> None: ...
