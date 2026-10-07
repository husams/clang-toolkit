from . import traversal_node_pb2 as _traversal_node_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TraverseResponse(_message.Message):
    __slots__ = ("nodes", "depth_limited")
    NODES_FIELD_NUMBER: _ClassVar[int]
    DEPTH_LIMITED_FIELD_NUMBER: _ClassVar[int]
    nodes: _containers.RepeatedCompositeFieldContainer[_traversal_node_pb2.TraversalNode]
    depth_limited: bool
    def __init__(self, nodes: _Optional[_Iterable[_Union[_traversal_node_pb2.TraversalNode, _Mapping]]] = ..., depth_limited: _Optional[bool] = ...) -> None: ...
