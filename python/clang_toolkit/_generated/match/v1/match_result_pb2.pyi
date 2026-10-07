from ...ast.v1 import common_pb2 as _common_pb2
from ...ast.v1 import node_pb2 as _node_pb2
from ...ast.v1 import semantic_types_pb2 as _semantic_types_pb2
from ...ast.v1 import semantic_pb2 as _semantic_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class BindingMatchScope(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    BINDING_MATCH_SCOPE_UNSPECIFIED: _ClassVar[BindingMatchScope]
    BINDING_MATCH_SCOPE_ROOT_ONLY: _ClassVar[BindingMatchScope]
    BINDING_MATCH_SCOPE_SUBTREE: _ClassVar[BindingMatchScope]
BINDING_MATCH_SCOPE_UNSPECIFIED: BindingMatchScope
BINDING_MATCH_SCOPE_ROOT_ONLY: BindingMatchScope
BINDING_MATCH_SCOPE_SUBTREE: BindingMatchScope

class MatchBinding(_message.Message):
    __slots__ = ("node", "qualified_type", "unsupported", "availability", "is_complete", "supported_scopes")
    NODE_FIELD_NUMBER: _ClassVar[int]
    QUALIFIED_TYPE_FIELD_NUMBER: _ClassVar[int]
    UNSUPPORTED_FIELD_NUMBER: _ClassVar[int]
    AVAILABILITY_FIELD_NUMBER: _ClassVar[int]
    IS_COMPLETE_FIELD_NUMBER: _ClassVar[int]
    SUPPORTED_SCOPES_FIELD_NUMBER: _ClassVar[int]
    node: _node_pb2.AstNode
    qualified_type: _semantic_pb2.QualType
    unsupported: _node_pb2.UnsupportedValue
    availability: _containers.RepeatedCompositeFieldContainer[_common_pb2.FieldAvailability]
    is_complete: bool
    supported_scopes: _containers.RepeatedScalarFieldContainer[BindingMatchScope]
    def __init__(self, node: _Optional[_Union[_node_pb2.AstNode, _Mapping]] = ..., qualified_type: _Optional[_Union[_semantic_pb2.QualType, _Mapping]] = ..., unsupported: _Optional[_Union[_node_pb2.UnsupportedValue, _Mapping]] = ..., availability: _Optional[_Iterable[_Union[_common_pb2.FieldAvailability, _Mapping]]] = ..., is_complete: _Optional[bool] = ..., supported_scopes: _Optional[_Iterable[_Union[BindingMatchScope, str]]] = ...) -> None: ...

class MatchResult(_message.Message):
    __slots__ = ("bindings", "source_match_index")
    class BindingsEntry(_message.Message):
        __slots__ = ("key", "value")
        KEY_FIELD_NUMBER: _ClassVar[int]
        VALUE_FIELD_NUMBER: _ClassVar[int]
        key: str
        value: MatchBinding
        def __init__(self, key: _Optional[str] = ..., value: _Optional[_Union[MatchBinding, _Mapping]] = ...) -> None: ...
    BINDINGS_FIELD_NUMBER: _ClassVar[int]
    SOURCE_MATCH_INDEX_FIELD_NUMBER: _ClassVar[int]
    bindings: _containers.MessageMap[str, MatchBinding]
    source_match_index: int
    def __init__(self, bindings: _Optional[_Mapping[str, MatchBinding]] = ..., source_match_index: _Optional[int] = ...) -> None: ...
