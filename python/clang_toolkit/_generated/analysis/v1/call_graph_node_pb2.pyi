from ...ast.v1 import semantic_types_pb2 as _semantic_types_pb2
from ...ast.v1 import semantic_pb2 as _semantic_pb2
from ...ast.v1 import common_pb2 as _common_pb2
from ...match.v1 import match_result_pb2 as _match_result_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CallGraphNode(_message.Message):
    __slots__ = ("node_index", "is_virtual_root", "function", "anonymous_declaration", "has_definition", "declaration_kind", "is_complete", "availability", "symbol_identity", "location", "range")
    NODE_INDEX_FIELD_NUMBER: _ClassVar[int]
    IS_VIRTUAL_ROOT_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_FIELD_NUMBER: _ClassVar[int]
    ANONYMOUS_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    HAS_DEFINITION_FIELD_NUMBER: _ClassVar[int]
    DECLARATION_KIND_FIELD_NUMBER: _ClassVar[int]
    IS_COMPLETE_FIELD_NUMBER: _ClassVar[int]
    AVAILABILITY_FIELD_NUMBER: _ClassVar[int]
    SYMBOL_IDENTITY_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    RANGE_FIELD_NUMBER: _ClassVar[int]
    node_index: int
    is_virtual_root: bool
    function: _semantic_pb2.DeclarationSymbol
    anonymous_declaration: _semantic_pb2.DeclarationValue
    has_definition: bool
    declaration_kind: str
    is_complete: bool
    availability: _containers.RepeatedCompositeFieldContainer[_common_pb2.FieldAvailability]
    symbol_identity: str
    location: _match_result_pb2.MatchSourcePoint
    range: _match_result_pb2.MatchSourceRange
    def __init__(self, node_index: _Optional[int] = ..., is_virtual_root: _Optional[bool] = ..., function: _Optional[_Union[_semantic_pb2.DeclarationSymbol, _Mapping]] = ..., anonymous_declaration: _Optional[_Union[_semantic_pb2.DeclarationValue, _Mapping]] = ..., has_definition: _Optional[bool] = ..., declaration_kind: _Optional[str] = ..., is_complete: _Optional[bool] = ..., availability: _Optional[_Iterable[_Union[_common_pb2.FieldAvailability, _Mapping]]] = ..., symbol_identity: _Optional[str] = ..., location: _Optional[_Union[_match_result_pb2.MatchSourcePoint, _Mapping]] = ..., range: _Optional[_Union[_match_result_pb2.MatchSourceRange, _Mapping]] = ...) -> None: ...
