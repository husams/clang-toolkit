from . import traversal_node_pb2 as _traversal_node_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TraverseStreamEvent(_message.Message):
    __slots__ = ("node", "completed")
    NODE_FIELD_NUMBER: _ClassVar[int]
    COMPLETED_FIELD_NUMBER: _ClassVar[int]
    node: _traversal_node_pb2.TraversalNode
    completed: TraverseCompleted
    def __init__(self, node: _Optional[_Union[_traversal_node_pb2.TraversalNode, _Mapping]] = ..., completed: _Optional[_Union[TraverseCompleted, _Mapping]] = ...) -> None: ...

class TraverseCompleted(_message.Message):
    __slots__ = ("node_count", "depth_limited")
    NODE_COUNT_FIELD_NUMBER: _ClassVar[int]
    DEPTH_LIMITED_FIELD_NUMBER: _ClassVar[int]
    node_count: int
    depth_limited: bool
    def __init__(self, node_count: _Optional[int] = ..., depth_limited: _Optional[bool] = ...) -> None: ...
