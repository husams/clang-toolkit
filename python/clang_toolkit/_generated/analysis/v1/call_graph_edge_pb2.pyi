from ...ast.v1 import semantic_types_pb2 as _semantic_types_pb2
from ...ast.v1 import semantic_pb2 as _semantic_pb2
from ...ast.v1 import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CallGraphEdge(_message.Message):
    __slots__ = ("caller_node", "callee_node", "call", "is_virtual_root_edge", "is_complete", "availability")
    CALLER_NODE_FIELD_NUMBER: _ClassVar[int]
    CALLEE_NODE_FIELD_NUMBER: _ClassVar[int]
    CALL_FIELD_NUMBER: _ClassVar[int]
    IS_VIRTUAL_ROOT_EDGE_FIELD_NUMBER: _ClassVar[int]
    IS_COMPLETE_FIELD_NUMBER: _ClassVar[int]
    AVAILABILITY_FIELD_NUMBER: _ClassVar[int]
    caller_node: int
    callee_node: int
    call: _semantic_pb2.ExpressionValue
    is_virtual_root_edge: bool
    is_complete: bool
    availability: _containers.RepeatedCompositeFieldContainer[_common_pb2.FieldAvailability]
    def __init__(self, caller_node: _Optional[int] = ..., callee_node: _Optional[int] = ..., call: _Optional[_Union[_semantic_pb2.ExpressionValue, _Mapping]] = ..., is_virtual_root_edge: _Optional[bool] = ..., is_complete: _Optional[bool] = ..., availability: _Optional[_Iterable[_Union[_common_pb2.FieldAvailability, _Mapping]]] = ...) -> None: ...
