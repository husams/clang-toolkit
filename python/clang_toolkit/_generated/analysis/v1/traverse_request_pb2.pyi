from ...match.v1 import match_service_pb2 as _match_service_pb2
from ...match.v1 import cache_resources_pb2 as _cache_resources_pb2
from ...match.v1 import resources_pb2 as _resources_pb2
from . import value_projection_pb2 as _value_projection_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class TraverseRequest(_message.Message):
    __slots__ = ("file", "session", "binding", "file_handle", "visit_implicit_code", "visit_template_instantiations", "max_depth", "max_nodes", "projection", "main_file_only", "resource_scope_id")
    FILE_FIELD_NUMBER: _ClassVar[int]
    SESSION_FIELD_NUMBER: _ClassVar[int]
    BINDING_FIELD_NUMBER: _ClassVar[int]
    FILE_HANDLE_FIELD_NUMBER: _ClassVar[int]
    VISIT_IMPLICIT_CODE_FIELD_NUMBER: _ClassVar[int]
    VISIT_TEMPLATE_INSTANTIATIONS_FIELD_NUMBER: _ClassVar[int]
    MAX_DEPTH_FIELD_NUMBER: _ClassVar[int]
    MAX_NODES_FIELD_NUMBER: _ClassVar[int]
    PROJECTION_FIELD_NUMBER: _ClassVar[int]
    MAIN_FILE_ONLY_FIELD_NUMBER: _ClassVar[int]
    RESOURCE_SCOPE_ID_FIELD_NUMBER: _ClassVar[int]
    file: _match_service_pb2.FileMatchTarget
    session: _match_service_pb2.SessionMatchTarget
    binding: _match_service_pb2.BindingMatchTarget
    file_handle: _resources_pb2.FileHandleTarget
    visit_implicit_code: bool
    visit_template_instantiations: bool
    max_depth: int
    max_nodes: int
    projection: _value_projection_pb2.ValueProjection
    main_file_only: bool
    resource_scope_id: str
    def __init__(self, file: _Optional[_Union[_match_service_pb2.FileMatchTarget, _Mapping]] = ..., session: _Optional[_Union[_match_service_pb2.SessionMatchTarget, _Mapping]] = ..., binding: _Optional[_Union[_match_service_pb2.BindingMatchTarget, _Mapping]] = ..., file_handle: _Optional[_Union[_resources_pb2.FileHandleTarget, _Mapping]] = ..., visit_implicit_code: _Optional[bool] = ..., visit_template_instantiations: _Optional[bool] = ..., max_depth: _Optional[int] = ..., max_nodes: _Optional[int] = ..., projection: _Optional[_Union[_value_projection_pb2.ValueProjection, _Mapping]] = ..., main_file_only: _Optional[bool] = ..., resource_scope_id: _Optional[str] = ...) -> None: ...
