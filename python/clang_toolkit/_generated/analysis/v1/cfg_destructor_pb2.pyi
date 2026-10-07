from ...ast.v1 import semantic_types_pb2 as _semantic_types_pb2
from ...ast.v1 import semantic_pb2 as _semantic_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CfgDestructor(_message.Message):
    __slots__ = ("destructor", "is_no_return", "variable", "record", "field", "base", "trigger")
    DESTRUCTOR_FIELD_NUMBER: _ClassVar[int]
    IS_NO_RETURN_FIELD_NUMBER: _ClassVar[int]
    VARIABLE_FIELD_NUMBER: _ClassVar[int]
    RECORD_FIELD_NUMBER: _ClassVar[int]
    FIELD_FIELD_NUMBER: _ClassVar[int]
    BASE_FIELD_NUMBER: _ClassVar[int]
    TRIGGER_FIELD_NUMBER: _ClassVar[int]
    destructor: _semantic_pb2.DeclarationSymbol
    is_no_return: bool
    variable: _semantic_pb2.DeclarationSymbol
    record: _semantic_pb2.DeclarationSymbol
    field: _semantic_pb2.DeclarationSymbol
    base: _semantic_pb2.CXXBaseSpecifier
    trigger: _semantic_pb2.StatementValue
    def __init__(self, destructor: _Optional[_Union[_semantic_pb2.DeclarationSymbol, _Mapping]] = ..., is_no_return: _Optional[bool] = ..., variable: _Optional[_Union[_semantic_pb2.DeclarationSymbol, _Mapping]] = ..., record: _Optional[_Union[_semantic_pb2.DeclarationSymbol, _Mapping]] = ..., field: _Optional[_Union[_semantic_pb2.DeclarationSymbol, _Mapping]] = ..., base: _Optional[_Union[_semantic_pb2.CXXBaseSpecifier, _Mapping]] = ..., trigger: _Optional[_Union[_semantic_pb2.StatementValue, _Mapping]] = ...) -> None: ...
