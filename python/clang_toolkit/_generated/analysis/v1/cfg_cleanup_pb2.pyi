from ...ast.v1 import semantic_types_pb2 as _semantic_types_pb2
from ...ast.v1 import semantic_pb2 as _semantic_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CfgCleanup(_message.Message):
    __slots__ = ("variable", "function")
    VARIABLE_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_FIELD_NUMBER: _ClassVar[int]
    variable: _semantic_pb2.DeclarationSymbol
    function: _semantic_pb2.DeclarationSymbol
    def __init__(self, variable: _Optional[_Union[_semantic_pb2.DeclarationSymbol, _Mapping]] = ..., function: _Optional[_Union[_semantic_pb2.DeclarationSymbol, _Mapping]] = ...) -> None: ...
