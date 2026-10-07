from . import call_graph_node_pb2 as _call_graph_node_pb2
from . import call_graph_edge_pb2 as _call_graph_edge_pb2
from ...ast.v1 import common_pb2 as _common_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CallGraphResponse(_message.Message):
    __slots__ = ("root_node", "nodes", "edges", "is_complete", "availability")
    ROOT_NODE_FIELD_NUMBER: _ClassVar[int]
    NODES_FIELD_NUMBER: _ClassVar[int]
    EDGES_FIELD_NUMBER: _ClassVar[int]
    IS_COMPLETE_FIELD_NUMBER: _ClassVar[int]
    AVAILABILITY_FIELD_NUMBER: _ClassVar[int]
    root_node: int
    nodes: _containers.RepeatedCompositeFieldContainer[_call_graph_node_pb2.CallGraphNode]
    edges: _containers.RepeatedCompositeFieldContainer[_call_graph_edge_pb2.CallGraphEdge]
    is_complete: bool
    availability: _containers.RepeatedCompositeFieldContainer[_common_pb2.FieldAvailability]
    def __init__(self, root_node: _Optional[int] = ..., nodes: _Optional[_Iterable[_Union[_call_graph_node_pb2.CallGraphNode, _Mapping]]] = ..., edges: _Optional[_Iterable[_Union[_call_graph_edge_pb2.CallGraphEdge, _Mapping]]] = ..., is_complete: _Optional[bool] = ..., availability: _Optional[_Iterable[_Union[_common_pb2.FieldAvailability, _Mapping]]] = ...) -> None: ...
