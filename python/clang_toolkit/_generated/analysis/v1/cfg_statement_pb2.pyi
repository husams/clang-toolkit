from ...ast.v1 import semantic_types_pb2 as _semantic_types_pb2
from ...ast.v1 import semantic_pb2 as _semantic_pb2
from . import cfg_construction_context_pb2 as _cfg_construction_context_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CfgStatement(_message.Message):
    __slots__ = ("statement", "construction_context")
    STATEMENT_FIELD_NUMBER: _ClassVar[int]
    CONSTRUCTION_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    statement: _semantic_pb2.StatementValue
    construction_context: _cfg_construction_context_pb2.CfgConstructionContext
    def __init__(self, statement: _Optional[_Union[_semantic_pb2.StatementValue, _Mapping]] = ..., construction_context: _Optional[_Union[_cfg_construction_context_pb2.CfgConstructionContext, _Mapping]] = ...) -> None: ...
