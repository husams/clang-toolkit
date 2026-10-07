from ...ast.v1 import semantic_types_pb2 as _semantic_types_pb2
from ...ast.v1 import semantic_pb2 as _semantic_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CfgInitializer(_message.Message):
    __slots__ = ("initializer",)
    INITIALIZER_FIELD_NUMBER: _ClassVar[int]
    initializer: _semantic_pb2.CXXCtorInitializer
    def __init__(self, initializer: _Optional[_Union[_semantic_pb2.CXXCtorInitializer, _Mapping]] = ...) -> None: ...
