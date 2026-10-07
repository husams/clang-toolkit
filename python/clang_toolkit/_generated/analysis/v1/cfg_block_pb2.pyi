from ...ast.v1 import semantic_types_pb2 as _semantic_types_pb2
from ...ast.v1 import semantic_pb2 as _semantic_pb2
from ...ast.v1 import common_pb2 as _common_pb2
from . import cfg_element_pb2 as _cfg_element_pb2
from . import cfg_edge_pb2 as _cfg_edge_pb2
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CfgBlock(_message.Message):
    __slots__ = ("block_index", "elements", "predecessors", "successors", "label", "loop_target", "terminator_kind", "terminator", "terminator_condition", "last_condition", "has_no_return_element", "is_complete", "availability")
    class TerminatorKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        TERMINATOR_UNSPECIFIED: _ClassVar[CfgBlock.TerminatorKind]
        STATEMENT_BRANCH: _ClassVar[CfgBlock.TerminatorKind]
        TEMPORARY_DTORS_BRANCH: _ClassVar[CfgBlock.TerminatorKind]
        VIRTUAL_BASE_BRANCH: _ClassVar[CfgBlock.TerminatorKind]
    TERMINATOR_UNSPECIFIED: CfgBlock.TerminatorKind
    STATEMENT_BRANCH: CfgBlock.TerminatorKind
    TEMPORARY_DTORS_BRANCH: CfgBlock.TerminatorKind
    VIRTUAL_BASE_BRANCH: CfgBlock.TerminatorKind
    BLOCK_INDEX_FIELD_NUMBER: _ClassVar[int]
    ELEMENTS_FIELD_NUMBER: _ClassVar[int]
    PREDECESSORS_FIELD_NUMBER: _ClassVar[int]
    SUCCESSORS_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    LOOP_TARGET_FIELD_NUMBER: _ClassVar[int]
    TERMINATOR_KIND_FIELD_NUMBER: _ClassVar[int]
    TERMINATOR_FIELD_NUMBER: _ClassVar[int]
    TERMINATOR_CONDITION_FIELD_NUMBER: _ClassVar[int]
    LAST_CONDITION_FIELD_NUMBER: _ClassVar[int]
    HAS_NO_RETURN_ELEMENT_FIELD_NUMBER: _ClassVar[int]
    IS_COMPLETE_FIELD_NUMBER: _ClassVar[int]
    AVAILABILITY_FIELD_NUMBER: _ClassVar[int]
    block_index: int
    elements: _containers.RepeatedCompositeFieldContainer[_cfg_element_pb2.CfgElement]
    predecessors: _containers.RepeatedCompositeFieldContainer[_cfg_edge_pb2.CfgEdge]
    successors: _containers.RepeatedCompositeFieldContainer[_cfg_edge_pb2.CfgEdge]
    label: _semantic_pb2.StatementValue
    loop_target: _semantic_pb2.StatementValue
    terminator_kind: CfgBlock.TerminatorKind
    terminator: _semantic_pb2.StatementValue
    terminator_condition: _semantic_pb2.StatementValue
    last_condition: _semantic_pb2.ExpressionValue
    has_no_return_element: bool
    is_complete: bool
    availability: _containers.RepeatedCompositeFieldContainer[_common_pb2.FieldAvailability]
    def __init__(self, block_index: _Optional[int] = ..., elements: _Optional[_Iterable[_Union[_cfg_element_pb2.CfgElement, _Mapping]]] = ..., predecessors: _Optional[_Iterable[_Union[_cfg_edge_pb2.CfgEdge, _Mapping]]] = ..., successors: _Optional[_Iterable[_Union[_cfg_edge_pb2.CfgEdge, _Mapping]]] = ..., label: _Optional[_Union[_semantic_pb2.StatementValue, _Mapping]] = ..., loop_target: _Optional[_Union[_semantic_pb2.StatementValue, _Mapping]] = ..., terminator_kind: _Optional[_Union[CfgBlock.TerminatorKind, str]] = ..., terminator: _Optional[_Union[_semantic_pb2.StatementValue, _Mapping]] = ..., terminator_condition: _Optional[_Union[_semantic_pb2.StatementValue, _Mapping]] = ..., last_condition: _Optional[_Union[_semantic_pb2.ExpressionValue, _Mapping]] = ..., has_no_return_element: _Optional[bool] = ..., is_complete: _Optional[bool] = ..., availability: _Optional[_Iterable[_Union[_common_pb2.FieldAvailability, _Mapping]]] = ...) -> None: ...
