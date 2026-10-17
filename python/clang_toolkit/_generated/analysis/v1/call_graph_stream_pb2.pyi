from ...match.v1 import match_stream_pb2 as _match_stream_pb2
from . import call_graph_node_pb2 as _call_graph_node_pb2
from . import call_graph_edge_pb2 as _call_graph_edge_pb2
from . import call_graph_response_pb2 as _call_graph_response_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CallGraphStreamEvent(_message.Message):
    __slots__ = ("graph_started", "node", "edge", "call_site", "completed")
    GRAPH_STARTED_FIELD_NUMBER: _ClassVar[int]
    NODE_FIELD_NUMBER: _ClassVar[int]
    EDGE_FIELD_NUMBER: _ClassVar[int]
    CALL_SITE_FIELD_NUMBER: _ClassVar[int]
    COMPLETED_FIELD_NUMBER: _ClassVar[int]
    graph_started: CallGraphStarted
    node: CallGraphNodeEvent
    edge: CallGraphEdgeEvent
    call_site: CallGraphCallSiteEvent
    completed: CallGraphCompleted
    def __init__(self, graph_started: _Optional[_Union[CallGraphStarted, _Mapping]] = ..., node: _Optional[_Union[CallGraphNodeEvent, _Mapping]] = ..., edge: _Optional[_Union[CallGraphEdgeEvent, _Mapping]] = ..., call_site: _Optional[_Union[CallGraphCallSiteEvent, _Mapping]] = ..., completed: _Optional[_Union[CallGraphCompleted, _Mapping]] = ...) -> None: ...

class CallGraphStarted(_message.Message):
    __slots__ = ("graph_index", "snapshot_generation", "graph")
    GRAPH_INDEX_FIELD_NUMBER: _ClassVar[int]
    SNAPSHOT_GENERATION_FIELD_NUMBER: _ClassVar[int]
    GRAPH_FIELD_NUMBER: _ClassVar[int]
    graph_index: int
    snapshot_generation: int
    graph: _call_graph_response_pb2.CallGraphResponse
    def __init__(self, graph_index: _Optional[int] = ..., snapshot_generation: _Optional[int] = ..., graph: _Optional[_Union[_call_graph_response_pb2.CallGraphResponse, _Mapping]] = ...) -> None: ...

class CallGraphNodeEvent(_message.Message):
    __slots__ = ("graph_index", "node")
    GRAPH_INDEX_FIELD_NUMBER: _ClassVar[int]
    NODE_FIELD_NUMBER: _ClassVar[int]
    graph_index: int
    node: _call_graph_node_pb2.CallGraphNode
    def __init__(self, graph_index: _Optional[int] = ..., node: _Optional[_Union[_call_graph_node_pb2.CallGraphNode, _Mapping]] = ...) -> None: ...

class CallGraphEdgeEvent(_message.Message):
    __slots__ = ("graph_index", "edge")
    GRAPH_INDEX_FIELD_NUMBER: _ClassVar[int]
    EDGE_FIELD_NUMBER: _ClassVar[int]
    graph_index: int
    edge: _call_graph_edge_pb2.CallGraphEdge
    def __init__(self, graph_index: _Optional[int] = ..., edge: _Optional[_Union[_call_graph_edge_pb2.CallGraphEdge, _Mapping]] = ...) -> None: ...

class CallGraphCallSiteEvent(_message.Message):
    __slots__ = ("graph_index", "call_site")
    GRAPH_INDEX_FIELD_NUMBER: _ClassVar[int]
    CALL_SITE_FIELD_NUMBER: _ClassVar[int]
    graph_index: int
    call_site: _call_graph_response_pb2.CallGraphCallSite
    def __init__(self, graph_index: _Optional[int] = ..., call_site: _Optional[_Union[_call_graph_response_pb2.CallGraphCallSite, _Mapping]] = ...) -> None: ...

class CallGraphCompleted(_message.Message):
    __slots__ = ("graph_count", "node_count", "edge_count", "call_site_count", "is_complete", "retained_nodes")
    GRAPH_COUNT_FIELD_NUMBER: _ClassVar[int]
    NODE_COUNT_FIELD_NUMBER: _ClassVar[int]
    EDGE_COUNT_FIELD_NUMBER: _ClassVar[int]
    CALL_SITE_COUNT_FIELD_NUMBER: _ClassVar[int]
    IS_COMPLETE_FIELD_NUMBER: _ClassVar[int]
    RETAINED_NODES_FIELD_NUMBER: _ClassVar[int]
    graph_count: int
    node_count: int
    edge_count: int
    call_site_count: int
    is_complete: bool
    retained_nodes: _match_stream_pb2.MatchStreamCompleted
    def __init__(self, graph_count: _Optional[int] = ..., node_count: _Optional[int] = ..., edge_count: _Optional[int] = ..., call_site_count: _Optional[int] = ..., is_complete: _Optional[bool] = ..., retained_nodes: _Optional[_Union[_match_stream_pb2.MatchStreamCompleted, _Mapping]] = ...) -> None: ...
