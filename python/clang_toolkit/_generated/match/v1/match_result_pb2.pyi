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

class CallDispatch(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CALL_DISPATCH_UNSPECIFIED: _ClassVar[CallDispatch]
    CALL_DISPATCH_DIRECT: _ClassVar[CallDispatch]
    CALL_DISPATCH_INDIRECT: _ClassVar[CallDispatch]
    CALL_DISPATCH_VIRTUAL: _ClassVar[CallDispatch]
BINDING_MATCH_SCOPE_UNSPECIFIED: BindingMatchScope
BINDING_MATCH_SCOPE_ROOT_ONLY: BindingMatchScope
BINDING_MATCH_SCOPE_SUBTREE: BindingMatchScope
CALL_DISPATCH_UNSPECIFIED: CallDispatch
CALL_DISPATCH_DIRECT: CallDispatch
CALL_DISPATCH_INDIRECT: CallDispatch
CALL_DISPATCH_VIRTUAL: CallDispatch

class MatchBinding(_message.Message):
    __slots__ = ("node", "qualified_type", "unsupported", "availability", "is_complete", "supported_scopes", "location", "range", "symbol_identity", "documentation", "call_site")
    NODE_FIELD_NUMBER: _ClassVar[int]
    QUALIFIED_TYPE_FIELD_NUMBER: _ClassVar[int]
    UNSUPPORTED_FIELD_NUMBER: _ClassVar[int]
    AVAILABILITY_FIELD_NUMBER: _ClassVar[int]
    IS_COMPLETE_FIELD_NUMBER: _ClassVar[int]
    SUPPORTED_SCOPES_FIELD_NUMBER: _ClassVar[int]
    LOCATION_FIELD_NUMBER: _ClassVar[int]
    RANGE_FIELD_NUMBER: _ClassVar[int]
    SYMBOL_IDENTITY_FIELD_NUMBER: _ClassVar[int]
    DOCUMENTATION_FIELD_NUMBER: _ClassVar[int]
    CALL_SITE_FIELD_NUMBER: _ClassVar[int]
    node: _node_pb2.AstNode
    qualified_type: _semantic_pb2.QualType
    unsupported: _node_pb2.UnsupportedValue
    availability: _containers.RepeatedCompositeFieldContainer[_common_pb2.FieldAvailability]
    is_complete: bool
    supported_scopes: _containers.RepeatedScalarFieldContainer[BindingMatchScope]
    location: MatchSourcePoint
    range: MatchSourceRange
    symbol_identity: str
    documentation: str
    call_site: CallSiteFacts
    def __init__(self, node: _Optional[_Union[_node_pb2.AstNode, _Mapping]] = ..., qualified_type: _Optional[_Union[_semantic_pb2.QualType, _Mapping]] = ..., unsupported: _Optional[_Union[_node_pb2.UnsupportedValue, _Mapping]] = ..., availability: _Optional[_Iterable[_Union[_common_pb2.FieldAvailability, _Mapping]]] = ..., is_complete: _Optional[bool] = ..., supported_scopes: _Optional[_Iterable[_Union[BindingMatchScope, str]]] = ..., location: _Optional[_Union[MatchSourcePoint, _Mapping]] = ..., range: _Optional[_Union[MatchSourceRange, _Mapping]] = ..., symbol_identity: _Optional[str] = ..., documentation: _Optional[str] = ..., call_site: _Optional[_Union[CallSiteFacts, _Mapping]] = ...) -> None: ...

class MatchSourcePoint(_message.Message):
    __slots__ = ("file", "line", "column", "valid", "is_macro")
    FILE_FIELD_NUMBER: _ClassVar[int]
    LINE_FIELD_NUMBER: _ClassVar[int]
    COLUMN_FIELD_NUMBER: _ClassVar[int]
    VALID_FIELD_NUMBER: _ClassVar[int]
    IS_MACRO_FIELD_NUMBER: _ClassVar[int]
    file: str
    line: int
    column: int
    valid: bool
    is_macro: bool
    def __init__(self, file: _Optional[str] = ..., line: _Optional[int] = ..., column: _Optional[int] = ..., valid: _Optional[bool] = ..., is_macro: _Optional[bool] = ...) -> None: ...

class MatchSourceRange(_message.Message):
    __slots__ = ("expansion_begin", "expansion_end", "spelling_begin", "spelling_end")
    EXPANSION_BEGIN_FIELD_NUMBER: _ClassVar[int]
    EXPANSION_END_FIELD_NUMBER: _ClassVar[int]
    SPELLING_BEGIN_FIELD_NUMBER: _ClassVar[int]
    SPELLING_END_FIELD_NUMBER: _ClassVar[int]
    expansion_begin: MatchSourcePoint
    expansion_end: MatchSourcePoint
    spelling_begin: MatchSourcePoint
    spelling_end: MatchSourcePoint
    def __init__(self, expansion_begin: _Optional[_Union[MatchSourcePoint, _Mapping]] = ..., expansion_end: _Optional[_Union[MatchSourcePoint, _Mapping]] = ..., spelling_begin: _Optional[_Union[MatchSourcePoint, _Mapping]] = ..., spelling_end: _Optional[_Union[MatchSourcePoint, _Mapping]] = ...) -> None: ...

class CallSiteFacts(_message.Message):
    __slots__ = ("caller_symbol_identity", "caller_name", "dispatch", "static_callee_symbol_identity", "static_callee_name")
    CALLER_SYMBOL_IDENTITY_FIELD_NUMBER: _ClassVar[int]
    CALLER_NAME_FIELD_NUMBER: _ClassVar[int]
    DISPATCH_FIELD_NUMBER: _ClassVar[int]
    STATIC_CALLEE_SYMBOL_IDENTITY_FIELD_NUMBER: _ClassVar[int]
    STATIC_CALLEE_NAME_FIELD_NUMBER: _ClassVar[int]
    caller_symbol_identity: str
    caller_name: str
    dispatch: CallDispatch
    static_callee_symbol_identity: str
    static_callee_name: str
    def __init__(self, caller_symbol_identity: _Optional[str] = ..., caller_name: _Optional[str] = ..., dispatch: _Optional[_Union[CallDispatch, str]] = ..., static_callee_symbol_identity: _Optional[str] = ..., static_callee_name: _Optional[str] = ...) -> None: ...

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
