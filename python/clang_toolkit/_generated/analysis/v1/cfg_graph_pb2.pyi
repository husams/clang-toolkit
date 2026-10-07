from ...ast.v1 import semantic_types_pb2 as _semantic_types_pb2
from ...ast.v1 import semantic_pb2 as _semantic_pb2
from ...ast.v1 import common_pb2 as _common_pb2
from . import cfg_block_pb2 as _cfg_block_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CfgGraph(_message.Message):
    __slots__ = ("function", "entry_block", "exit_block", "blocks", "is_linear", "is_complete", "availability")
    FUNCTION_FIELD_NUMBER: _ClassVar[int]
    ENTRY_BLOCK_FIELD_NUMBER: _ClassVar[int]
    EXIT_BLOCK_FIELD_NUMBER: _ClassVar[int]
    BLOCKS_FIELD_NUMBER: _ClassVar[int]
    IS_LINEAR_FIELD_NUMBER: _ClassVar[int]
    IS_COMPLETE_FIELD_NUMBER: _ClassVar[int]
    AVAILABILITY_FIELD_NUMBER: _ClassVar[int]
    function: _semantic_pb2.DeclarationSymbol
    entry_block: int
    exit_block: int
    blocks: _containers.RepeatedCompositeFieldContainer[_cfg_block_pb2.CfgBlock]
    is_linear: bool
    is_complete: bool
    availability: _containers.RepeatedCompositeFieldContainer[_common_pb2.FieldAvailability]
    def __init__(self, function: _Optional[_Union[_semantic_pb2.DeclarationSymbol, _Mapping]] = ..., entry_block: _Optional[int] = ..., exit_block: _Optional[int] = ..., blocks: _Optional[_Iterable[_Union[_cfg_block_pb2.CfgBlock, _Mapping]]] = ..., is_linear: _Optional[bool] = ..., is_complete: _Optional[bool] = ..., availability: _Optional[_Iterable[_Union[_common_pb2.FieldAvailability, _Mapping]]] = ...) -> None: ...
