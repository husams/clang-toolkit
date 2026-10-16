from ...match.v1 import match_service_pb2 as _match_service_pb2
from ...match.v1 import resources_pb2 as _resources_pb2
from . import value_projection_pb2 as _value_projection_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CallGraphDirection(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CALL_GRAPH_DIRECTION_UNSPECIFIED: _ClassVar[CallGraphDirection]
    CALL_GRAPH_DIRECTION_OUT: _ClassVar[CallGraphDirection]
    CALL_GRAPH_DIRECTION_IN: _ClassVar[CallGraphDirection]
    CALL_GRAPH_DIRECTION_BOTH: _ClassVar[CallGraphDirection]
CALL_GRAPH_DIRECTION_UNSPECIFIED: CallGraphDirection
CALL_GRAPH_DIRECTION_OUT: CallGraphDirection
CALL_GRAPH_DIRECTION_IN: CallGraphDirection
CALL_GRAPH_DIRECTION_BOTH: CallGraphDirection

class CallGraphRequest(_message.Message):
    __slots__ = ("file", "session", "binding", "file_handle", "visit_implicit_code", "visit_template_instantiations", "max_nodes", "max_edges", "projection", "main_file_only", "resource_scope_id", "direction", "max_depth", "max_call_sites", "function", "unlimited_depth")
    FILE_FIELD_NUMBER: _ClassVar[int]
    SESSION_FIELD_NUMBER: _ClassVar[int]
    BINDING_FIELD_NUMBER: _ClassVar[int]
    FILE_HANDLE_FIELD_NUMBER: _ClassVar[int]
    VISIT_IMPLICIT_CODE_FIELD_NUMBER: _ClassVar[int]
    VISIT_TEMPLATE_INSTANTIATIONS_FIELD_NUMBER: _ClassVar[int]
    MAX_NODES_FIELD_NUMBER: _ClassVar[int]
    MAX_EDGES_FIELD_NUMBER: _ClassVar[int]
    PROJECTION_FIELD_NUMBER: _ClassVar[int]
    MAIN_FILE_ONLY_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_SCOPE_ID_FIELD_NUMBER: _ClassVar[int]
    DIRECTION_FIELD_NUMBER: _ClassVar[int]
    MAX_DEPTH_FIELD_NUMBER: _ClassVar[int]
    MAX_CALL_SITES_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_FIELD_NUMBER: _ClassVar[int]
    UNLIMITED_DEPTH_FIELD_NUMBER: _ClassVar[int]
    file: _match_service_pb2.FileMatchTarget
    session: _match_service_pb2.SessionMatchTarget
    binding: _match_service_pb2.BindingMatchTarget
    file_handle: _resources_pb2.FileHandleTarget
    visit_implicit_code: bool
    visit_template_instantiations: bool
    max_nodes: int
    max_edges: int
    projection: _value_projection_pb2.ValueProjection
    main_file_only: bool
    resource_scope_id: str
    direction: CallGraphDirection
    max_depth: int
    max_call_sites: int
    function: str
    unlimited_depth: bool
    def __init__(self, file: _Optional[_Union[_match_service_pb2.FileMatchTarget, _Mapping]] = ..., session: _Optional[_Union[_match_service_pb2.SessionMatchTarget, _Mapping]] = ..., binding: _Optional[_Union[_match_service_pb2.BindingMatchTarget, _Mapping]] = ..., file_handle: _Optional[_Union[_resources_pb2.FileHandleTarget, _Mapping]] = ..., visit_implicit_code: _Optional[bool] = ..., visit_template_instantiations: _Optional[bool] = ..., max_nodes: _Optional[int] = ..., max_edges: _Optional[int] = ..., projection: _Optional[_Union[_value_projection_pb2.ValueProjection, _Mapping]] = ..., main_file_only: _Optional[bool] = ..., resource_scope_id: _Optional[str] = ..., direction: _Optional[_Union[CallGraphDirection, str]] = ..., max_depth: _Optional[int] = ..., max_call_sites: _Optional[int] = ..., function: _Optional[str] = ..., unlimited_depth: _Optional[bool] = ...) -> None: ...
