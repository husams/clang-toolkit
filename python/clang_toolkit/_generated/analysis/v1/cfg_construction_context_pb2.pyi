from ...ast.v1 import semantic_types_pb2 as _semantic_types_pb2
from ...ast.v1 import semantic_pb2 as _semantic_pb2
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class CfgConstructionContext(_message.Message):
    __slots__ = ("kind", "decl_statement", "initializer", "allocation", "temporary_binding", "materialization", "constructor_after_elision", "context_after_elision", "returned_value", "call_like_expression", "argument_index", "lambda_expression", "capture_index", "capture_initializer", "capture_field", "array_initialization_loop")
    class Kind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
        __slots__ = ()
        KIND_UNSPECIFIED: _ClassVar[CfgConstructionContext.Kind]
        SIMPLE_VARIABLE: _ClassVar[CfgConstructionContext.Kind]
        CXX17_ELIDED_COPY_VARIABLE: _ClassVar[CfgConstructionContext.Kind]
        SIMPLE_CONSTRUCTOR_INITIALIZER: _ClassVar[CfgConstructionContext.Kind]
        CXX17_ELIDED_COPY_CONSTRUCTOR_INITIALIZER: _ClassVar[CfgConstructionContext.Kind]
        NEW_ALLOCATED_OBJECT: _ClassVar[CfgConstructionContext.Kind]
        SIMPLE_TEMPORARY_OBJECT: _ClassVar[CfgConstructionContext.Kind]
        ELIDED_TEMPORARY_OBJECT: _ClassVar[CfgConstructionContext.Kind]
        SIMPLE_RETURNED_VALUE: _ClassVar[CfgConstructionContext.Kind]
        CXX17_ELIDED_COPY_RETURNED_VALUE: _ClassVar[CfgConstructionContext.Kind]
        ARGUMENT: _ClassVar[CfgConstructionContext.Kind]
        LAMBDA_CAPTURE: _ClassVar[CfgConstructionContext.Kind]
    KIND_UNSPECIFIED: CfgConstructionContext.Kind
    SIMPLE_VARIABLE: CfgConstructionContext.Kind
    CXX17_ELIDED_COPY_VARIABLE: CfgConstructionContext.Kind
    SIMPLE_CONSTRUCTOR_INITIALIZER: CfgConstructionContext.Kind
    CXX17_ELIDED_COPY_CONSTRUCTOR_INITIALIZER: CfgConstructionContext.Kind
    NEW_ALLOCATED_OBJECT: CfgConstructionContext.Kind
    SIMPLE_TEMPORARY_OBJECT: CfgConstructionContext.Kind
    ELIDED_TEMPORARY_OBJECT: CfgConstructionContext.Kind
    SIMPLE_RETURNED_VALUE: CfgConstructionContext.Kind
    CXX17_ELIDED_COPY_RETURNED_VALUE: CfgConstructionContext.Kind
    ARGUMENT: CfgConstructionContext.Kind
    LAMBDA_CAPTURE: CfgConstructionContext.Kind
    KIND_FIELD_NUMBER: _ClassVar[int]
    DECL_STATEMENT_FIELD_NUMBER: _ClassVar[int]
    INITIALIZER_FIELD_NUMBER: _ClassVar[int]
    ALLOCATION_FIELD_NUMBER: _ClassVar[int]
    TEMPORARY_BINDING_FIELD_NUMBER: _ClassVar[int]
    MATERIALIZATION_FIELD_NUMBER: _ClassVar[int]
    CONSTRUCTOR_AFTER_ELISION_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_AFTER_ELISION_FIELD_NUMBER: _ClassVar[int]
    RETURNED_VALUE_FIELD_NUMBER: _ClassVar[int]
    CALL_LIKE_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    ARGUMENT_INDEX_FIELD_NUMBER: _ClassVar[int]
    LAMBDA_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    CAPTURE_INDEX_FIELD_NUMBER: _ClassVar[int]
    CAPTURE_INITIALIZER_FIELD_NUMBER: _ClassVar[int]
    CAPTURE_FIELD_FIELD_NUMBER: _ClassVar[int]
    ARRAY_INITIALIZATION_LOOP_FIELD_NUMBER: _ClassVar[int]
    kind: CfgConstructionContext.Kind
    decl_statement: _semantic_pb2.StatementValue
    initializer: _semantic_pb2.CXXCtorInitializer
    allocation: _semantic_pb2.ExpressionValue
    temporary_binding: _semantic_pb2.ExpressionValue
    materialization: _semantic_pb2.ExpressionValue
    constructor_after_elision: _semantic_pb2.ExpressionValue
    context_after_elision: CfgConstructionContext
    returned_value: _semantic_pb2.StatementValue
    call_like_expression: _semantic_pb2.ExpressionValue
    argument_index: int
    lambda_expression: _semantic_pb2.ExpressionValue
    capture_index: int
    capture_initializer: _semantic_pb2.ExpressionValue
    capture_field: _semantic_pb2.DeclarationSymbol
    array_initialization_loop: _semantic_pb2.ExpressionValue
    def __init__(self, kind: _Optional[_Union[CfgConstructionContext.Kind, str]] = ..., decl_statement: _Optional[_Union[_semantic_pb2.StatementValue, _Mapping]] = ..., initializer: _Optional[_Union[_semantic_pb2.CXXCtorInitializer, _Mapping]] = ..., allocation: _Optional[_Union[_semantic_pb2.ExpressionValue, _Mapping]] = ..., temporary_binding: _Optional[_Union[_semantic_pb2.ExpressionValue, _Mapping]] = ..., materialization: _Optional[_Union[_semantic_pb2.ExpressionValue, _Mapping]] = ..., constructor_after_elision: _Optional[_Union[_semantic_pb2.ExpressionValue, _Mapping]] = ..., context_after_elision: _Optional[_Union[CfgConstructionContext, _Mapping]] = ..., returned_value: _Optional[_Union[_semantic_pb2.StatementValue, _Mapping]] = ..., call_like_expression: _Optional[_Union[_semantic_pb2.ExpressionValue, _Mapping]] = ..., argument_index: _Optional[int] = ..., lambda_expression: _Optional[_Union[_semantic_pb2.ExpressionValue, _Mapping]] = ..., capture_index: _Optional[int] = ..., capture_initializer: _Optional[_Union[_semantic_pb2.ExpressionValue, _Mapping]] = ..., capture_field: _Optional[_Union[_semantic_pb2.DeclarationSymbol, _Mapping]] = ..., array_initialization_loop: _Optional[_Union[_semantic_pb2.ExpressionValue, _Mapping]] = ...) -> None: ...
