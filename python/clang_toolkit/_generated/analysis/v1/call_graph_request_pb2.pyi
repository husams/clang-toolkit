from ...match.v1 import match_service_pb2 as _match_service_pb2
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CallGraphRequest(_message.Message):
    __slots__ = ("file", "visit_implicit_code", "visit_template_instantiations", "max_nodes", "max_edges")
    FILE_FIELD_NUMBER: _ClassVar[int]
    VISIT_IMPLICIT_CODE_FIELD_NUMBER: _ClassVar[int]
    VISIT_TEMPLATE_INSTANTIATIONS_FIELD_NUMBER: _ClassVar[int]
    MAX_NODES_FIELD_NUMBER: _ClassVar[int]
    MAX_EDGES_FIELD_NUMBER: _ClassVar[int]
    file: _match_service_pb2.FileMatchTarget
    visit_implicit_code: bool
    visit_template_instantiations: bool
    max_nodes: int
    max_edges: int
    def __init__(self, file: _Optional[_Union[_match_service_pb2.FileMatchTarget, _Mapping]] = ..., visit_implicit_code: _Optional[bool] = ..., visit_template_instantiations: _Optional[bool] = ..., max_nodes: _Optional[int] = ..., max_edges: _Optional[int] = ...) -> None: ...
