from ...ast.v1 import common_pb2 as _common_pb2
from . import cfg_statement_pb2 as _cfg_statement_pb2
from . import cfg_initializer_pb2 as _cfg_initializer_pb2
from . import cfg_scope_event_pb2 as _cfg_scope_event_pb2
from . import cfg_new_allocator_pb2 as _cfg_new_allocator_pb2
from . import cfg_loop_exit_pb2 as _cfg_loop_exit_pb2
from . import cfg_destructor_pb2 as _cfg_destructor_pb2
from . import cfg_cleanup_pb2 as _cfg_cleanup_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CfgElement(_message.Message):
    __slots__ = ("kind", "statement", "initializer", "scope", "allocator", "loop_exit", "destructor", "cleanup", "is_complete", "availability")
    class Kind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        KIND_UNSPECIFIED: _ClassVar[CfgElement.Kind]
        INITIALIZER: _ClassVar[CfgElement.Kind]
        SCOPE_BEGIN: _ClassVar[CfgElement.Kind]
        SCOPE_END: _ClassVar[CfgElement.Kind]
        NEW_ALLOCATOR: _ClassVar[CfgElement.Kind]
        LIFETIME_ENDS: _ClassVar[CfgElement.Kind]
        LOOP_EXIT: _ClassVar[CfgElement.Kind]
        STATEMENT: _ClassVar[CfgElement.Kind]
        CONSTRUCTOR: _ClassVar[CfgElement.Kind]
        CXX_RECORD_TYPED_CALL: _ClassVar[CfgElement.Kind]
        AUTOMATIC_OBJECT_DTOR: _ClassVar[CfgElement.Kind]
        DELETE_DTOR: _ClassVar[CfgElement.Kind]
        BASE_DTOR: _ClassVar[CfgElement.Kind]
        MEMBER_DTOR: _ClassVar[CfgElement.Kind]
        TEMPORARY_DTOR: _ClassVar[CfgElement.Kind]
        CLEANUP_FUNCTION: _ClassVar[CfgElement.Kind]
    KIND_UNSPECIFIED: CfgElement.Kind
    INITIALIZER: CfgElement.Kind
    SCOPE_BEGIN: CfgElement.Kind
    SCOPE_END: CfgElement.Kind
    NEW_ALLOCATOR: CfgElement.Kind
    LIFETIME_ENDS: CfgElement.Kind
    LOOP_EXIT: CfgElement.Kind
    STATEMENT: CfgElement.Kind
    CONSTRUCTOR: CfgElement.Kind
    CXX_RECORD_TYPED_CALL: CfgElement.Kind
    AUTOMATIC_OBJECT_DTOR: CfgElement.Kind
    DELETE_DTOR: CfgElement.Kind
    BASE_DTOR: CfgElement.Kind
    MEMBER_DTOR: CfgElement.Kind
    TEMPORARY_DTOR: CfgElement.Kind
    CLEANUP_FUNCTION: CfgElement.Kind
    KIND_FIELD_NUMBER: _ClassVar[int]
    STATEMENT_FIELD_NUMBER: _ClassVar[int]
    INITIALIZER_FIELD_NUMBER: _ClassVar[int]
    SCOPE_FIELD_NUMBER: _ClassVar[int]
    ALLOCATOR_FIELD_NUMBER: _ClassVar[int]
    LOOP_EXIT_FIELD_NUMBER: _ClassVar[int]
    DESTRUCTOR_FIELD_NUMBER: _ClassVar[int]
    CLEANUP_FIELD_NUMBER: _ClassVar[int]
    IS_COMPLETE_FIELD_NUMBER: _ClassVar[int]
    AVAILABILITY_FIELD_NUMBER: _ClassVar[int]
    kind: CfgElement.Kind
    statement: _cfg_statement_pb2.CfgStatement
    initializer: _cfg_initializer_pb2.CfgInitializer
    scope: _cfg_scope_event_pb2.CfgScopeEvent
    allocator: _cfg_new_allocator_pb2.CfgNewAllocator
    loop_exit: _cfg_loop_exit_pb2.CfgLoopExit
    destructor: _cfg_destructor_pb2.CfgDestructor
    cleanup: _cfg_cleanup_pb2.CfgCleanup
    is_complete: bool
    availability: _containers.RepeatedCompositeFieldContainer[_common_pb2.FieldAvailability]
    def __init__(self, kind: _Optional[_Union[CfgElement.Kind, str]] = ..., statement: _Optional[_Union[_cfg_statement_pb2.CfgStatement, _Mapping]] = ..., initializer: _Optional[_Union[_cfg_initializer_pb2.CfgInitializer, _Mapping]] = ..., scope: _Optional[_Union[_cfg_scope_event_pb2.CfgScopeEvent, _Mapping]] = ..., allocator: _Optional[_Union[_cfg_new_allocator_pb2.CfgNewAllocator, _Mapping]] = ..., loop_exit: _Optional[_Union[_cfg_loop_exit_pb2.CfgLoopExit, _Mapping]] = ..., destructor: _Optional[_Union[_cfg_destructor_pb2.CfgDestructor, _Mapping]] = ..., cleanup: _Optional[_Union[_cfg_cleanup_pb2.CfgCleanup, _Mapping]] = ..., is_complete: _Optional[bool] = ..., availability: _Optional[_Iterable[_Union[_common_pb2.FieldAvailability, _Mapping]]] = ...) -> None: ...
