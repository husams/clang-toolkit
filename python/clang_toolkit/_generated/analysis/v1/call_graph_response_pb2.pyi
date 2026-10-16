from . import call_graph_node_pb2 as _call_graph_node_pb2
from . import call_graph_edge_pb2 as _call_graph_edge_pb2
from . import call_graph_request_pb2 as _call_graph_request_pb2
from ...ast.v1 import common_pb2 as _common_pb2
from ...ast.v1 import semantic_types_pb2 as _semantic_types_pb2
from ...ast.v1 import semantic_pb2 as _semantic_pb2
from ...match.v1 import match_result_pb2 as _match_result_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CallGraphResponse(_message.Message):
    __slots__ = ("root_node", "nodes", "edges", "is_complete", "availability", "main_file_only", "external_edges_omitted", "call_sites", "snapshot_generation", "source_file", "source_revision", "compilation_profile_id", "focus_node", "selection_direction", "selection_max_depth", "selection_boundary_edges", "selection_boundary_call_sites")
    ROOT_NODE_FIELD_NUMBER: _ClassVar[int]
    NODES_FIELD_NUMBER: _ClassVar[int]
    EDGES_FIELD_NUMBER: _ClassVar[int]
    IS_COMPLETE_FIELD_NUMBER: _ClassVar[int]
    AVAILABILITY_FIELD_NUMBER: _ClassVar[int]
    MAIN_FILE_ONLY_FIELD_NUMBER: _ClassVar[int]
    EXTERNAL_EDGES_OMITTED_FIELD_NUMBER: _ClassVar[int]
    CALL_SITES_FIELD_NUMBER: _ClassVar[int]
    SNAPSHOT_GENERATION_FIELD_NUMBER: _ClassVar[int]
    SOURCE_FILE_FIELD_NUMBER: _ClassVar[int]
    SOURCE_REVISION_FIELD_NUMBER: _ClassVar[int]
    COMPILATION_PROFILE_ID_FIELD_NUMBER: _ClassVar[int]
    FOCUS_NODE_FIELD_NUMBER: _ClassVar[int]
    SELECTION_DIRECTION_FIELD_NUMBER: _ClassVar[int]
    SELECTION_MAX_DEPTH_FIELD_NUMBER: _ClassVar[int]
    SELECTION_BOUNDARY_EDGES_FIELD_NUMBER: _ClassVar[int]
    SELECTION_BOUNDARY_CALL_SITES_FIELD_NUMBER: _ClassVar[int]
    root_node: int
    nodes: _containers.RepeatedCompositeFieldContainer[_call_graph_node_pb2.CallGraphNode]
    edges: _containers.RepeatedCompositeFieldContainer[_call_graph_edge_pb2.CallGraphEdge]
    is_complete: bool
    availability: _containers.RepeatedCompositeFieldContainer[_common_pb2.FieldAvailability]
    main_file_only: bool
    external_edges_omitted: int
    call_sites: _containers.RepeatedCompositeFieldContainer[CallGraphCallSite]
    snapshot_generation: int
    source_file: str
    source_revision: str
    compilation_profile_id: str
    focus_node: int
    selection_direction: _call_graph_request_pb2.CallGraphDirection
    selection_max_depth: int
    selection_boundary_edges: int
    selection_boundary_call_sites: int
    def __init__(self, root_node: _Optional[int] = ..., nodes: _Optional[_Iterable[_Union[_call_graph_node_pb2.CallGraphNode, _Mapping]]] = ..., edges: _Optional[_Iterable[_Union[_call_graph_edge_pb2.CallGraphEdge, _Mapping]]] = ..., is_complete: _Optional[bool] = ..., availability: _Optional[_Iterable[_Union[_common_pb2.FieldAvailability, _Mapping]]] = ..., main_file_only: _Optional[bool] = ..., external_edges_omitted: _Optional[int] = ..., call_sites: _Optional[_Iterable[_Union[CallGraphCallSite, _Mapping]]] = ..., snapshot_generation: _Optional[int] = ..., source_file: _Optional[str] = ..., source_revision: _Optional[str] = ..., compilation_profile_id: _Optional[str] = ..., focus_node: _Optional[int] = ..., selection_direction: _Optional[_Union[_call_graph_request_pb2.CallGraphDirection, str]] = ..., selection_max_depth: _Optional[int] = ..., selection_boundary_edges: _Optional[int] = ..., selection_boundary_call_sites: _Optional[int] = ...) -> None: ...

class CallGraphCallSite(_message.Message):
    __slots__ = ("caller_node", "callee_node", "call", "location", "range", "facts", "is_complete", "availability")
    CALLER_NODE_FIELD_NUMBER: _ClassVar[int]
    CALLEE_NODE_FIELD_NUMBER: _ClassVar[int]
    CALL_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    RANGE_FIELD_NUMBER: _ClassVar[int]
    FACTS_FIELD_NUMBER: _ClassVar[int]
    IS_COMPLETE_FIELD_NUMBER: _ClassVar[int]
    AVAILABILITY_FIELD_NUMBER: _ClassVar[int]
    caller_node: int
    callee_node: int
    call: _semantic_pb2.ExpressionValue
    location: _match_result_pb2.MatchSourcePoint
    range: _match_result_pb2.MatchSourceRange
    facts: _match_result_pb2.CallSiteFacts
    is_complete: bool
    availability: _containers.RepeatedCompositeFieldContainer[_common_pb2.FieldAvailability]
    def __init__(self, caller_node: _Optional[int] = ..., callee_node: _Optional[int] = ..., call: _Optional[_Union[_semantic_pb2.ExpressionValue, _Mapping]] = ..., location: _Optional[_Union[_match_result_pb2.MatchSourcePoint, _Mapping]] = ..., range: _Optional[_Union[_match_result_pb2.MatchSourceRange, _Mapping]] = ..., facts: _Optional[_Union[_match_result_pb2.CallSiteFacts, _Mapping]] = ..., is_complete: _Optional[bool] = ..., availability: _Optional[_Iterable[_Union[_common_pb2.FieldAvailability, _Mapping]]] = ...) -> None: ...
