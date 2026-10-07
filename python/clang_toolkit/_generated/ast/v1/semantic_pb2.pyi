from . import common_pb2 as _common_pb2  # noqa: E402, F401
from . import operators_pb2 as _operators_pb2  # noqa: E402, F401
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from collections.abc import Iterable as _Iterable, Mapping as _Mapping
from typing import ClassVar as _ClassVar, Optional as _Optional, Union as _Union

DESCRIPTOR: _descriptor.FileDescriptor

class SymbolKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SYMBOL_KIND_UNSPECIFIED: _ClassVar[SymbolKind]
    SYMBOL_KIND_NAMESPACE: _ClassVar[SymbolKind]
    SYMBOL_KIND_RECORD: _ClassVar[SymbolKind]
    SYMBOL_KIND_ENUM: _ClassVar[SymbolKind]
    SYMBOL_KIND_TYPE_ALIAS: _ClassVar[SymbolKind]
    SYMBOL_KIND_FUNCTION: _ClassVar[SymbolKind]
    SYMBOL_KIND_METHOD: _ClassVar[SymbolKind]
    SYMBOL_KIND_CONSTRUCTOR: _ClassVar[SymbolKind]
    SYMBOL_KIND_DESTRUCTOR: _ClassVar[SymbolKind]
    SYMBOL_KIND_VARIABLE: _ClassVar[SymbolKind]
    SYMBOL_KIND_FIELD: _ClassVar[SymbolKind]
    SYMBOL_KIND_PARAMETER: _ClassVar[SymbolKind]
    SYMBOL_KIND_TEMPLATE: _ClassVar[SymbolKind]
    SYMBOL_KIND_CONCEPT: _ClassVar[SymbolKind]
    SYMBOL_KIND_LABEL: _ClassVar[SymbolKind]
    SYMBOL_KIND_UNRESOLVED: _ClassVar[SymbolKind]
    SYMBOL_KIND_OTHER: _ClassVar[SymbolKind]

class TemplateArgumentDescriptionKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TEMPLATE_ARGUMENT_DESCRIPTION_KIND_UNSPECIFIED: _ClassVar[TemplateArgumentDescriptionKind]
    TEMPLATE_ARGUMENT_DESCRIPTION_KIND_NULL: _ClassVar[TemplateArgumentDescriptionKind]
    TEMPLATE_ARGUMENT_DESCRIPTION_KIND_TYPE: _ClassVar[TemplateArgumentDescriptionKind]
    TEMPLATE_ARGUMENT_DESCRIPTION_KIND_DECLARATION: _ClassVar[TemplateArgumentDescriptionKind]
    TEMPLATE_ARGUMENT_DESCRIPTION_KIND_NULL_POINTER: _ClassVar[TemplateArgumentDescriptionKind]
    TEMPLATE_ARGUMENT_DESCRIPTION_KIND_INTEGRAL: _ClassVar[TemplateArgumentDescriptionKind]
    TEMPLATE_ARGUMENT_DESCRIPTION_KIND_STRUCTURAL_VALUE: _ClassVar[TemplateArgumentDescriptionKind]
    TEMPLATE_ARGUMENT_DESCRIPTION_KIND_TEMPLATE: _ClassVar[TemplateArgumentDescriptionKind]
    TEMPLATE_ARGUMENT_DESCRIPTION_KIND_TEMPLATE_EXPANSION: _ClassVar[TemplateArgumentDescriptionKind]
    TEMPLATE_ARGUMENT_DESCRIPTION_KIND_EXPRESSION: _ClassVar[TemplateArgumentDescriptionKind]
    TEMPLATE_ARGUMENT_DESCRIPTION_KIND_PACK: _ClassVar[TemplateArgumentDescriptionKind]

class TemplateParameterDescriptionKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TEMPLATE_PARAMETER_DESCRIPTION_KIND_UNSPECIFIED: _ClassVar[TemplateParameterDescriptionKind]
    TEMPLATE_PARAMETER_DESCRIPTION_KIND_TYPE: _ClassVar[TemplateParameterDescriptionKind]
    TEMPLATE_PARAMETER_DESCRIPTION_KIND_NON_TYPE: _ClassVar[TemplateParameterDescriptionKind]
    TEMPLATE_PARAMETER_DESCRIPTION_KIND_TEMPLATE: _ClassVar[TemplateParameterDescriptionKind]

class FloatingSemantics(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    FLOATING_SEMANTICS_UNSPECIFIED: _ClassVar[FloatingSemantics]
    FLOATING_SEMANTICS_IEEE_HALF: _ClassVar[FloatingSemantics]
    FLOATING_SEMANTICS_BFLOAT: _ClassVar[FloatingSemantics]
    FLOATING_SEMANTICS_IEEE_SINGLE: _ClassVar[FloatingSemantics]
    FLOATING_SEMANTICS_IEEE_DOUBLE: _ClassVar[FloatingSemantics]
    FLOATING_SEMANTICS_IEEE_QUAD: _ClassVar[FloatingSemantics]
    FLOATING_SEMANTICS_X87_DOUBLE_EXTENDED: _ClassVar[FloatingSemantics]
    FLOATING_SEMANTICS_PPC_DOUBLE_DOUBLE: _ClassVar[FloatingSemantics]
    FLOATING_SEMANTICS_PPC_DOUBLE_DOUBLE_LEGACY: _ClassVar[FloatingSemantics]
    FLOATING_SEMANTICS_FLOAT8_E5_M2: _ClassVar[FloatingSemantics]
    FLOATING_SEMANTICS_FLOAT8_E5_M2_FNUZ: _ClassVar[FloatingSemantics]
    FLOATING_SEMANTICS_FLOAT8_E4_M3: _ClassVar[FloatingSemantics]
    FLOATING_SEMANTICS_FLOAT8_E4_M3_FN: _ClassVar[FloatingSemantics]
    FLOATING_SEMANTICS_FLOAT8_E4_M3_FNUZ: _ClassVar[FloatingSemantics]
    FLOATING_SEMANTICS_FLOAT8_E4_M3_B11_FNUZ: _ClassVar[FloatingSemantics]
    FLOATING_SEMANTICS_FLOAT8_E3_M4: _ClassVar[FloatingSemantics]
    FLOATING_SEMANTICS_FLOAT_TF32: _ClassVar[FloatingSemantics]
    FLOATING_SEMANTICS_FLOAT8_E8_M0_FNU: _ClassVar[FloatingSemantics]
    FLOATING_SEMANTICS_FLOAT6_E3_M2_FN: _ClassVar[FloatingSemantics]
    FLOATING_SEMANTICS_FLOAT6_E2_M3_FN: _ClassVar[FloatingSemantics]
    FLOATING_SEMANTICS_FLOAT4_E2_M1_FN: _ClassVar[FloatingSemantics]

class LambdaCaptureKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    LAMBDA_CAPTURE_KIND_UNSPECIFIED: _ClassVar[LambdaCaptureKind]
    LAMBDA_CAPTURE_KIND_THIS: _ClassVar[LambdaCaptureKind]
    LAMBDA_CAPTURE_KIND_STAR_THIS: _ClassVar[LambdaCaptureKind]
    LAMBDA_CAPTURE_KIND_BY_COPY: _ClassVar[LambdaCaptureKind]
    LAMBDA_CAPTURE_KIND_BY_REFERENCE: _ClassVar[LambdaCaptureKind]
    LAMBDA_CAPTURE_KIND_VLA_TYPE: _ClassVar[LambdaCaptureKind]

class ExprRequirementSatisfactionStatus(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    EXPR_REQUIREMENT_SATISFACTION_STATUS_UNSPECIFIED: _ClassVar[ExprRequirementSatisfactionStatus]
    EXPR_REQUIREMENT_SATISFACTION_STATUS_DEPENDENT: _ClassVar[ExprRequirementSatisfactionStatus]
    EXPR_REQUIREMENT_SATISFACTION_STATUS_EXPR_SUBSTITUTION_FAILURE: _ClassVar[ExprRequirementSatisfactionStatus]
    EXPR_REQUIREMENT_SATISFACTION_STATUS_NOEXCEPT_NOT_MET: _ClassVar[ExprRequirementSatisfactionStatus]
    EXPR_REQUIREMENT_SATISFACTION_STATUS_TYPE_REQUIREMENT_SUBSTITUTION_FAILURE: _ClassVar[ExprRequirementSatisfactionStatus]
    EXPR_REQUIREMENT_SATISFACTION_STATUS_CONSTRAINTS_NOT_SATISFIED: _ClassVar[ExprRequirementSatisfactionStatus]
    EXPR_REQUIREMENT_SATISFACTION_STATUS_SATISFIED: _ClassVar[ExprRequirementSatisfactionStatus]

class DeclLinkageLanguage(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DECL_LINKAGE_LANGUAGE_UNSPECIFIED: _ClassVar[DeclLinkageLanguage]
    DECL_LINKAGE_LANGUAGE_C: _ClassVar[DeclLinkageLanguage]
    DECL_LINKAGE_LANGUAGE_CXX: _ClassVar[DeclLinkageLanguage]

class DeclTemplateSpecializationKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DECL_TEMPLATE_SPECIALIZATION_KIND_UNSPECIFIED: _ClassVar[DeclTemplateSpecializationKind]
    DECL_TEMPLATE_SPECIALIZATION_KIND_UNDECLARED: _ClassVar[DeclTemplateSpecializationKind]
    DECL_TEMPLATE_SPECIALIZATION_KIND_IMPLICIT_INSTANTIATION: _ClassVar[DeclTemplateSpecializationKind]
    DECL_TEMPLATE_SPECIALIZATION_KIND_EXPLICIT_SPECIALIZATION: _ClassVar[DeclTemplateSpecializationKind]
    DECL_TEMPLATE_SPECIALIZATION_KIND_EXPLICIT_INSTANTIATION_DECLARATION: _ClassVar[DeclTemplateSpecializationKind]
    DECL_TEMPLATE_SPECIALIZATION_KIND_EXPLICIT_INSTANTIATION_DEFINITION: _ClassVar[DeclTemplateSpecializationKind]

class DeclPragmaCommentKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DECL_PRAGMA_COMMENT_KIND_UNSPECIFIED: _ClassVar[DeclPragmaCommentKind]
    DECL_PRAGMA_COMMENT_KIND_UNKNOWN: _ClassVar[DeclPragmaCommentKind]
    DECL_PRAGMA_COMMENT_KIND_LINKER: _ClassVar[DeclPragmaCommentKind]
    DECL_PRAGMA_COMMENT_KIND_LIB: _ClassVar[DeclPragmaCommentKind]
    DECL_PRAGMA_COMMENT_KIND_COMPILER: _ClassVar[DeclPragmaCommentKind]
    DECL_PRAGMA_COMMENT_KIND_EXE_STR: _ClassVar[DeclPragmaCommentKind]
    DECL_PRAGMA_COMMENT_KIND_USER: _ClassVar[DeclPragmaCommentKind]

class DeclBuiltinTemplateKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DECL_BUILTIN_TEMPLATE_KIND_UNSPECIFIED: _ClassVar[DeclBuiltinTemplateKind]
    DECL_BUILTIN_TEMPLATE_KIND_COMMON_TYPE: _ClassVar[DeclBuiltinTemplateKind]
    DECL_BUILTIN_TEMPLATE_KIND_DEDUP_PACK: _ClassVar[DeclBuiltinTemplateKind]
    DECL_BUILTIN_TEMPLATE_KIND_MAKE_INTEGER_SEQ: _ClassVar[DeclBuiltinTemplateKind]
    DECL_BUILTIN_TEMPLATE_KIND_TYPE_PACK_ELEMENT: _ClassVar[DeclBuiltinTemplateKind]

class DeclVariableTLSKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DECL_VARIABLE_TLS_KIND_UNSPECIFIED: _ClassVar[DeclVariableTLSKind]
    DECL_VARIABLE_TLS_KIND_NONE: _ClassVar[DeclVariableTLSKind]
    DECL_VARIABLE_TLS_KIND_STATIC: _ClassVar[DeclVariableTLSKind]
    DECL_VARIABLE_TLS_KIND_DYNAMIC: _ClassVar[DeclVariableTLSKind]

class DeclVariableInitializationStyle(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DECL_VARIABLE_INITIALIZATION_STYLE_UNSPECIFIED: _ClassVar[DeclVariableInitializationStyle]
    DECL_VARIABLE_INITIALIZATION_STYLE_C: _ClassVar[DeclVariableInitializationStyle]
    DECL_VARIABLE_INITIALIZATION_STYLE_CALL: _ClassVar[DeclVariableInitializationStyle]
    DECL_VARIABLE_INITIALIZATION_STYLE_LIST: _ClassVar[DeclVariableInitializationStyle]
    DECL_VARIABLE_INITIALIZATION_STYLE_PAREN_LIST: _ClassVar[DeclVariableInitializationStyle]

class DeclDeductionCandidateKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DECL_DEDUCTION_CANDIDATE_KIND_UNSPECIFIED: _ClassVar[DeclDeductionCandidateKind]
    DECL_DEDUCTION_CANDIDATE_KIND_NORMAL: _ClassVar[DeclDeductionCandidateKind]
    DECL_DEDUCTION_CANDIDATE_KIND_COPY: _ClassVar[DeclDeductionCandidateKind]
    DECL_DEDUCTION_CANDIDATE_KIND_AGGREGATE: _ClassVar[DeclDeductionCandidateKind]

class DeclSourceDeductionGuideKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DECL_SOURCE_DEDUCTION_GUIDE_KIND_UNSPECIFIED: _ClassVar[DeclSourceDeductionGuideKind]
    DECL_SOURCE_DEDUCTION_GUIDE_KIND_NONE: _ClassVar[DeclSourceDeductionGuideKind]
    DECL_SOURCE_DEDUCTION_GUIDE_KIND_ALIAS: _ClassVar[DeclSourceDeductionGuideKind]

class CharacterKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CHARACTER_KIND_UNSPECIFIED: _ClassVar[CharacterKind]
    CHARACTER_KIND_ASCII: _ClassVar[CharacterKind]
    CHARACTER_KIND_UTF8: _ClassVar[CharacterKind]
    CHARACTER_KIND_UTF16: _ClassVar[CharacterKind]
    CHARACTER_KIND_UTF32: _ClassVar[CharacterKind]
    CHARACTER_KIND_WIDE: _ClassVar[CharacterKind]

class StringLiteralKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    STRING_LITERAL_KIND_UNSPECIFIED: _ClassVar[StringLiteralKind]
    STRING_LITERAL_KIND_ORDINARY: _ClassVar[StringLiteralKind]
    STRING_LITERAL_KIND_UTF8: _ClassVar[StringLiteralKind]
    STRING_LITERAL_KIND_UTF16: _ClassVar[StringLiteralKind]
    STRING_LITERAL_KIND_UTF32: _ClassVar[StringLiteralKind]
    STRING_LITERAL_KIND_WIDE: _ClassVar[StringLiteralKind]

class UnaryExprTrait(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNARY_EXPR_TRAIT_UNSPECIFIED: _ClassVar[UnaryExprTrait]
    UNARY_EXPR_TRAIT_SIZEOF: _ClassVar[UnaryExprTrait]
    UNARY_EXPR_TRAIT_ALIGNOF: _ClassVar[UnaryExprTrait]
    UNARY_EXPR_TRAIT_OTHER: _ClassVar[UnaryExprTrait]

class ConstantExprResult(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    CONSTANT_EXPR_RESULT_UNSPECIFIED: _ClassVar[ConstantExprResult]
    CONSTANT_EXPR_RESULT_SUCCEEDED: _ClassVar[ConstantExprResult]
    CONSTANT_EXPR_RESULT_FAILED: _ClassVar[ConstantExprResult]
    CONSTANT_EXPR_RESULT_SIDE_EFFECTS: _ClassVar[ConstantExprResult]
    CONSTANT_EXPR_RESULT_NOT_EVALUATED: _ClassVar[ConstantExprResult]

class SourceLocExprKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    SOURCE_LOC_EXPR_KIND_UNSPECIFIED: _ClassVar[SourceLocExprKind]
    SOURCE_LOC_EXPR_KIND_LINE: _ClassVar[SourceLocExprKind]
    SOURCE_LOC_EXPR_KIND_COLUMN: _ClassVar[SourceLocExprKind]
    SOURCE_LOC_EXPR_KIND_FILE: _ClassVar[SourceLocExprKind]
    SOURCE_LOC_EXPR_KIND_FUNCTION: _ClassVar[SourceLocExprKind]

class PredefinedIdentKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PREDEFINED_IDENT_KIND_UNSPECIFIED: _ClassVar[PredefinedIdentKind]
    PREDEFINED_IDENT_KIND_FUNC: _ClassVar[PredefinedIdentKind]
    PREDEFINED_IDENT_KIND_FUNCTION: _ClassVar[PredefinedIdentKind]
    PREDEFINED_IDENT_KIND_PRETTY_FUNCTION: _ClassVar[PredefinedIdentKind]
    PREDEFINED_IDENT_KIND_OTHER: _ClassVar[PredefinedIdentKind]

class ArrayTypeTrait(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ARRAY_TYPE_TRAIT_UNSPECIFIED: _ClassVar[ArrayTypeTrait]
    ARRAY_TYPE_TRAIT_COUNT: _ClassVar[ArrayTypeTrait]

class ExpressionTrait(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    EXPRESSION_TRAIT_UNSPECIFIED: _ClassVar[ExpressionTrait]
    EXPRESSION_TRAIT_IS_LVALUE: _ClassVar[ExpressionTrait]
    EXPRESSION_TRAIT_IS_XVALUE: _ClassVar[ExpressionTrait]
    EXPRESSION_TRAIT_IS_PRVALUE: _ClassVar[ExpressionTrait]
    EXPRESSION_TRAIT_OTHER: _ClassVar[ExpressionTrait]

class AtomicOpcode(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ATOMIC_OPCODE_UNSPECIFIED: _ClassVar[AtomicOpcode]
    ATOMIC_OPCODE_LOAD: _ClassVar[AtomicOpcode]
    ATOMIC_OPCODE_STORE: _ClassVar[AtomicOpcode]
    ATOMIC_OPCODE_EXCHANGE: _ClassVar[AtomicOpcode]
    ATOMIC_OPCODE_COMPARE_EXCHANGE: _ClassVar[AtomicOpcode]
    ATOMIC_OPCODE_FETCH: _ClassVar[AtomicOpcode]
    ATOMIC_OPCODE_OTHER: _ClassVar[AtomicOpcode]

class TypeTrait(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TYPE_TRAIT_UNSPECIFIED: _ClassVar[TypeTrait]
    TYPE_TRAIT_OTHER: _ClassVar[TypeTrait]

class ArraySizeModifier(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ARRAY_SIZE_MODIFIER_UNSPECIFIED: _ClassVar[ArraySizeModifier]
    ARRAY_SIZE_MODIFIER_NORMAL: _ClassVar[ArraySizeModifier]
    ARRAY_SIZE_MODIFIER_STATIC: _ClassVar[ArraySizeModifier]
    ARRAY_SIZE_MODIFIER_STAR: _ClassVar[ArraySizeModifier]

class TypeOfKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    TYPE_OF_KIND_UNSPECIFIED: _ClassVar[TypeOfKind]
    TYPE_OF_KIND_QUALIFIED: _ClassVar[TypeOfKind]
    TYPE_OF_KIND_UNQUALIFIED: _ClassVar[TypeOfKind]

class AutoKeyword(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    AUTO_KEYWORD_UNSPECIFIED: _ClassVar[AutoKeyword]
    AUTO_KEYWORD_AUTO: _ClassVar[AutoKeyword]
    AUTO_KEYWORD_DECLTYPE_AUTO: _ClassVar[AutoKeyword]
    AUTO_KEYWORD_GNU_AUTO_TYPE: _ClassVar[AutoKeyword]

class VectorKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    VECTOR_KIND_UNSPECIFIED: _ClassVar[VectorKind]
    VECTOR_KIND_GENERIC: _ClassVar[VectorKind]
    VECTOR_KIND_ALTIVEC_VECTOR: _ClassVar[VectorKind]
    VECTOR_KIND_ALTIVEC_PIXEL: _ClassVar[VectorKind]
    VECTOR_KIND_ALTIVEC_BOOL: _ClassVar[VectorKind]
    VECTOR_KIND_NEON: _ClassVar[VectorKind]
    VECTOR_KIND_NEON_POLY: _ClassVar[VectorKind]
    VECTOR_KIND_SVE_FIXED_DATA: _ClassVar[VectorKind]
    VECTOR_KIND_SVE_FIXED_PREDICATE: _ClassVar[VectorKind]
    VECTOR_KIND_RVV_FIXED_DATA: _ClassVar[VectorKind]
    VECTOR_KIND_RVV_FIXED_MASK: _ClassVar[VectorKind]
    VECTOR_KIND_RVV_FIXED_MASK_1: _ClassVar[VectorKind]
    VECTOR_KIND_RVV_FIXED_MASK_2: _ClassVar[VectorKind]
    VECTOR_KIND_RVV_FIXED_MASK_4: _ClassVar[VectorKind]

class AttributedTypeKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    ATTRIBUTED_TYPE_KIND_UNSPECIFIED: _ClassVar[AttributedTypeKind]
    ATTRIBUTED_TYPE_KIND_ADDRESS_SPACE: _ClassVar[AttributedTypeKind]
    ATTRIBUTED_TYPE_KIND_NULLABILITY: _ClassVar[AttributedTypeKind]
    ATTRIBUTED_TYPE_KIND_CALLING_CONVENTION: _ClassVar[AttributedTypeKind]
    ATTRIBUTED_TYPE_KIND_VECTOR: _ClassVar[AttributedTypeKind]
    ATTRIBUTED_TYPE_KIND_FIXED_POINT: _ClassVar[AttributedTypeKind]
    ATTRIBUTED_TYPE_KIND_CPP_EXTENSION: _ClassVar[AttributedTypeKind]

class PredefinedTypeKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    PREDEFINED_TYPE_KIND_UNSPECIFIED: _ClassVar[PredefinedTypeKind]
    PREDEFINED_TYPE_KIND_SIZE_T: _ClassVar[PredefinedTypeKind]
    PREDEFINED_TYPE_KIND_SIGNED_SIZE_T: _ClassVar[PredefinedTypeKind]
    PREDEFINED_TYPE_KIND_PTRDIFF_T: _ClassVar[PredefinedTypeKind]

class DynamicCountKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    DYNAMIC_COUNT_KIND_UNSPECIFIED: _ClassVar[DynamicCountKind]
    DYNAMIC_COUNT_KIND_COUNTED_BY: _ClassVar[DynamicCountKind]
    DYNAMIC_COUNT_KIND_SIZED_BY: _ClassVar[DynamicCountKind]
    DYNAMIC_COUNT_KIND_COUNTED_BY_OR_NULL: _ClassVar[DynamicCountKind]
    DYNAMIC_COUNT_KIND_SIZED_BY_OR_NULL: _ClassVar[DynamicCountKind]

class UnaryTransformKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    UNARY_TRANSFORM_KIND_UNSPECIFIED: _ClassVar[UnaryTransformKind]
    UNARY_TRANSFORM_KIND_ADD_LVALUE_REFERENCE: _ClassVar[UnaryTransformKind]
    UNARY_TRANSFORM_KIND_ADD_POINTER: _ClassVar[UnaryTransformKind]
    UNARY_TRANSFORM_KIND_ADD_RVALUE_REFERENCE: _ClassVar[UnaryTransformKind]
    UNARY_TRANSFORM_KIND_DECAY: _ClassVar[UnaryTransformKind]
    UNARY_TRANSFORM_KIND_MAKE_SIGNED: _ClassVar[UnaryTransformKind]
    UNARY_TRANSFORM_KIND_MAKE_UNSIGNED: _ClassVar[UnaryTransformKind]
    UNARY_TRANSFORM_KIND_REMOVE_ALL_EXTENTS: _ClassVar[UnaryTransformKind]
    UNARY_TRANSFORM_KIND_REMOVE_CONST: _ClassVar[UnaryTransformKind]
    UNARY_TRANSFORM_KIND_REMOVE_CV: _ClassVar[UnaryTransformKind]
    UNARY_TRANSFORM_KIND_REMOVE_CV_REF: _ClassVar[UnaryTransformKind]
    UNARY_TRANSFORM_KIND_REMOVE_EXTENT: _ClassVar[UnaryTransformKind]
    UNARY_TRANSFORM_KIND_REMOVE_POINTER: _ClassVar[UnaryTransformKind]
    UNARY_TRANSFORM_KIND_REMOVE_REFERENCE: _ClassVar[UnaryTransformKind]
    UNARY_TRANSFORM_KIND_REMOVE_RESTRICT: _ClassVar[UnaryTransformKind]
    UNARY_TRANSFORM_KIND_REMOVE_VOLATILE: _ClassVar[UnaryTransformKind]
    UNARY_TRANSFORM_KIND_ENUM_UNDERLYING_TYPE: _ClassVar[UnaryTransformKind]

class BuiltinKind(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    BUILTIN_KIND_UNSPECIFIED: _ClassVar[BuiltinKind]
    BUILTIN_KIND_EXTENDED: _ClassVar[BuiltinKind]
    BUILTIN_KIND_VOID: _ClassVar[BuiltinKind]
    BUILTIN_KIND_BOOL: _ClassVar[BuiltinKind]
    BUILTIN_KIND_CHAR_U: _ClassVar[BuiltinKind]
    BUILTIN_KIND_UCHAR: _ClassVar[BuiltinKind]
    BUILTIN_KIND_CHAR16: _ClassVar[BuiltinKind]
    BUILTIN_KIND_CHAR32: _ClassVar[BuiltinKind]
    BUILTIN_KIND_USHORT: _ClassVar[BuiltinKind]
    BUILTIN_KIND_UINT: _ClassVar[BuiltinKind]
    BUILTIN_KIND_ULONG: _ClassVar[BuiltinKind]
    BUILTIN_KIND_ULONGLONG: _ClassVar[BuiltinKind]
    BUILTIN_KIND_UINT128: _ClassVar[BuiltinKind]
    BUILTIN_KIND_CHAR_S: _ClassVar[BuiltinKind]
    BUILTIN_KIND_SCHAR: _ClassVar[BuiltinKind]
    BUILTIN_KIND_SHORT: _ClassVar[BuiltinKind]
    BUILTIN_KIND_INT: _ClassVar[BuiltinKind]
    BUILTIN_KIND_LONG: _ClassVar[BuiltinKind]
    BUILTIN_KIND_LONGLONG: _ClassVar[BuiltinKind]
    BUILTIN_KIND_INT128: _ClassVar[BuiltinKind]
    BUILTIN_KIND_HALF: _ClassVar[BuiltinKind]
    BUILTIN_KIND_FLOAT: _ClassVar[BuiltinKind]
    BUILTIN_KIND_DOUBLE: _ClassVar[BuiltinKind]
    BUILTIN_KIND_LONGDOUBLE: _ClassVar[BuiltinKind]
    BUILTIN_KIND_FLOAT128: _ClassVar[BuiltinKind]
    BUILTIN_KIND_NULLPTR: _ClassVar[BuiltinKind]
    BUILTIN_KIND_OVERLOAD: _ClassVar[BuiltinKind]
    BUILTIN_KIND_DEPENDENT: _ClassVar[BuiltinKind]
    BUILTIN_KIND_FLOAT16: _ClassVar[BuiltinKind]
    BUILTIN_KIND_BFLOAT16: _ClassVar[BuiltinKind]
    BUILTIN_KIND_CHAR8: _ClassVar[BuiltinKind]
    BUILTIN_KIND_WCHAR_U: _ClassVar[BuiltinKind]
    BUILTIN_KIND_WCHAR_S: _ClassVar[BuiltinKind]

class FunctionCallingConvention(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    FUNCTION_CALLING_CONVENTION_UNSPECIFIED: _ClassVar[FunctionCallingConvention]
    FUNCTION_CALLING_CONVENTION_C: _ClassVar[FunctionCallingConvention]
    FUNCTION_CALLING_CONVENTION_X86_STDCALL: _ClassVar[FunctionCallingConvention]
    FUNCTION_CALLING_CONVENTION_X86_FASTCALL: _ClassVar[FunctionCallingConvention]
    FUNCTION_CALLING_CONVENTION_X86_THISCALL: _ClassVar[FunctionCallingConvention]
    FUNCTION_CALLING_CONVENTION_X86_VECTORCALL: _ClassVar[FunctionCallingConvention]
    FUNCTION_CALLING_CONVENTION_WIN64: _ClassVar[FunctionCallingConvention]
    FUNCTION_CALLING_CONVENTION_X86_64_SYSV: _ClassVar[FunctionCallingConvention]
    FUNCTION_CALLING_CONVENTION_X86_REGCALL: _ClassVar[FunctionCallingConvention]
    FUNCTION_CALLING_CONVENTION_AAPCS: _ClassVar[FunctionCallingConvention]
    FUNCTION_CALLING_CONVENTION_AAPCS_VFP: _ClassVar[FunctionCallingConvention]
    FUNCTION_CALLING_CONVENTION_SWIFT: _ClassVar[FunctionCallingConvention]
    FUNCTION_CALLING_CONVENTION_SWIFT_ASYNC: _ClassVar[FunctionCallingConvention]
    FUNCTION_CALLING_CONVENTION_PRESERVE_MOST: _ClassVar[FunctionCallingConvention]
    FUNCTION_CALLING_CONVENTION_PRESERVE_ALL: _ClassVar[FunctionCallingConvention]
    FUNCTION_CALLING_CONVENTION_AARCH64_VECTOR: _ClassVar[FunctionCallingConvention]
    FUNCTION_CALLING_CONVENTION_AARCH64_SVE: _ClassVar[FunctionCallingConvention]
    FUNCTION_CALLING_CONVENTION_PRESERVE_NONE: _ClassVar[FunctionCallingConvention]
    FUNCTION_CALLING_CONVENTION_RISCV_VECTOR: _ClassVar[FunctionCallingConvention]
    FUNCTION_CALLING_CONVENTION_TARGET_EXTENSION: _ClassVar[FunctionCallingConvention]

class ExceptionSpecification(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    EXCEPTION_SPECIFICATION_UNSPECIFIED: _ClassVar[ExceptionSpecification]
    EXCEPTION_SPECIFICATION_NONE: _ClassVar[ExceptionSpecification]
    EXCEPTION_SPECIFICATION_DYNAMIC: _ClassVar[ExceptionSpecification]
    EXCEPTION_SPECIFICATION_COMPUTED_NOEXCEPT: _ClassVar[ExceptionSpecification]
    EXCEPTION_SPECIFICATION_NO_THROW: _ClassVar[ExceptionSpecification]
    EXCEPTION_SPECIFICATION_MS_ANY: _ClassVar[ExceptionSpecification]
    EXCEPTION_SPECIFICATION_MS_BASIC_NOEXCEPT: _ClassVar[ExceptionSpecification]
    EXCEPTION_SPECIFICATION_OTHER: _ClassVar[ExceptionSpecification]
    EXCEPTION_SPECIFICATION_DYNAMIC_NONE: _ClassVar[ExceptionSpecification]
    EXCEPTION_SPECIFICATION_DEPENDENT_NOEXCEPT: _ClassVar[ExceptionSpecification]
    EXCEPTION_SPECIFICATION_NOEXCEPT_FALSE: _ClassVar[ExceptionSpecification]
    EXCEPTION_SPECIFICATION_NOEXCEPT_TRUE: _ClassVar[ExceptionSpecification]
    EXCEPTION_SPECIFICATION_UNPARSED: _ClassVar[ExceptionSpecification]
    EXCEPTION_SPECIFICATION_UNINSTANTIATED: _ClassVar[ExceptionSpecification]
    EXCEPTION_SPECIFICATION_UNEVALUATED: _ClassVar[ExceptionSpecification]
SYMBOL_KIND_UNSPECIFIED: SymbolKind
SYMBOL_KIND_NAMESPACE: SymbolKind
SYMBOL_KIND_RECORD: SymbolKind
SYMBOL_KIND_ENUM: SymbolKind
SYMBOL_KIND_TYPE_ALIAS: SymbolKind
SYMBOL_KIND_FUNCTION: SymbolKind
SYMBOL_KIND_METHOD: SymbolKind
SYMBOL_KIND_CONSTRUCTOR: SymbolKind
SYMBOL_KIND_DESTRUCTOR: SymbolKind
SYMBOL_KIND_VARIABLE: SymbolKind
SYMBOL_KIND_FIELD: SymbolKind
SYMBOL_KIND_PARAMETER: SymbolKind
SYMBOL_KIND_TEMPLATE: SymbolKind
SYMBOL_KIND_CONCEPT: SymbolKind
SYMBOL_KIND_LABEL: SymbolKind
SYMBOL_KIND_UNRESOLVED: SymbolKind
SYMBOL_KIND_OTHER: SymbolKind
TEMPLATE_ARGUMENT_DESCRIPTION_KIND_UNSPECIFIED: TemplateArgumentDescriptionKind
TEMPLATE_ARGUMENT_DESCRIPTION_KIND_NULL: TemplateArgumentDescriptionKind
TEMPLATE_ARGUMENT_DESCRIPTION_KIND_TYPE: TemplateArgumentDescriptionKind
TEMPLATE_ARGUMENT_DESCRIPTION_KIND_DECLARATION: TemplateArgumentDescriptionKind
TEMPLATE_ARGUMENT_DESCRIPTION_KIND_NULL_POINTER: TemplateArgumentDescriptionKind
TEMPLATE_ARGUMENT_DESCRIPTION_KIND_INTEGRAL: TemplateArgumentDescriptionKind
TEMPLATE_ARGUMENT_DESCRIPTION_KIND_STRUCTURAL_VALUE: TemplateArgumentDescriptionKind
TEMPLATE_ARGUMENT_DESCRIPTION_KIND_TEMPLATE: TemplateArgumentDescriptionKind
TEMPLATE_ARGUMENT_DESCRIPTION_KIND_TEMPLATE_EXPANSION: TemplateArgumentDescriptionKind
TEMPLATE_ARGUMENT_DESCRIPTION_KIND_EXPRESSION: TemplateArgumentDescriptionKind
TEMPLATE_ARGUMENT_DESCRIPTION_KIND_PACK: TemplateArgumentDescriptionKind
TEMPLATE_PARAMETER_DESCRIPTION_KIND_UNSPECIFIED: TemplateParameterDescriptionKind
TEMPLATE_PARAMETER_DESCRIPTION_KIND_TYPE: TemplateParameterDescriptionKind
TEMPLATE_PARAMETER_DESCRIPTION_KIND_NON_TYPE: TemplateParameterDescriptionKind
TEMPLATE_PARAMETER_DESCRIPTION_KIND_TEMPLATE: TemplateParameterDescriptionKind
FLOATING_SEMANTICS_UNSPECIFIED: FloatingSemantics
FLOATING_SEMANTICS_IEEE_HALF: FloatingSemantics
FLOATING_SEMANTICS_BFLOAT: FloatingSemantics
FLOATING_SEMANTICS_IEEE_SINGLE: FloatingSemantics
FLOATING_SEMANTICS_IEEE_DOUBLE: FloatingSemantics
FLOATING_SEMANTICS_IEEE_QUAD: FloatingSemantics
FLOATING_SEMANTICS_X87_DOUBLE_EXTENDED: FloatingSemantics
FLOATING_SEMANTICS_PPC_DOUBLE_DOUBLE: FloatingSemantics
FLOATING_SEMANTICS_PPC_DOUBLE_DOUBLE_LEGACY: FloatingSemantics
FLOATING_SEMANTICS_FLOAT8_E5_M2: FloatingSemantics
FLOATING_SEMANTICS_FLOAT8_E5_M2_FNUZ: FloatingSemantics
FLOATING_SEMANTICS_FLOAT8_E4_M3: FloatingSemantics
FLOATING_SEMANTICS_FLOAT8_E4_M3_FN: FloatingSemantics
FLOATING_SEMANTICS_FLOAT8_E4_M3_FNUZ: FloatingSemantics
FLOATING_SEMANTICS_FLOAT8_E4_M3_B11_FNUZ: FloatingSemantics
FLOATING_SEMANTICS_FLOAT8_E3_M4: FloatingSemantics
FLOATING_SEMANTICS_FLOAT_TF32: FloatingSemantics
FLOATING_SEMANTICS_FLOAT8_E8_M0_FNU: FloatingSemantics
FLOATING_SEMANTICS_FLOAT6_E3_M2_FN: FloatingSemantics
FLOATING_SEMANTICS_FLOAT6_E2_M3_FN: FloatingSemantics
FLOATING_SEMANTICS_FLOAT4_E2_M1_FN: FloatingSemantics
LAMBDA_CAPTURE_KIND_UNSPECIFIED: LambdaCaptureKind
LAMBDA_CAPTURE_KIND_THIS: LambdaCaptureKind
LAMBDA_CAPTURE_KIND_STAR_THIS: LambdaCaptureKind
LAMBDA_CAPTURE_KIND_BY_COPY: LambdaCaptureKind
LAMBDA_CAPTURE_KIND_BY_REFERENCE: LambdaCaptureKind
LAMBDA_CAPTURE_KIND_VLA_TYPE: LambdaCaptureKind
EXPR_REQUIREMENT_SATISFACTION_STATUS_UNSPECIFIED: ExprRequirementSatisfactionStatus
EXPR_REQUIREMENT_SATISFACTION_STATUS_DEPENDENT: ExprRequirementSatisfactionStatus
EXPR_REQUIREMENT_SATISFACTION_STATUS_EXPR_SUBSTITUTION_FAILURE: ExprRequirementSatisfactionStatus
EXPR_REQUIREMENT_SATISFACTION_STATUS_NOEXCEPT_NOT_MET: ExprRequirementSatisfactionStatus
EXPR_REQUIREMENT_SATISFACTION_STATUS_TYPE_REQUIREMENT_SUBSTITUTION_FAILURE: ExprRequirementSatisfactionStatus
EXPR_REQUIREMENT_SATISFACTION_STATUS_CONSTRAINTS_NOT_SATISFIED: ExprRequirementSatisfactionStatus
EXPR_REQUIREMENT_SATISFACTION_STATUS_SATISFIED: ExprRequirementSatisfactionStatus
DECL_LINKAGE_LANGUAGE_UNSPECIFIED: DeclLinkageLanguage
DECL_LINKAGE_LANGUAGE_C: DeclLinkageLanguage
DECL_LINKAGE_LANGUAGE_CXX: DeclLinkageLanguage
DECL_TEMPLATE_SPECIALIZATION_KIND_UNSPECIFIED: DeclTemplateSpecializationKind
DECL_TEMPLATE_SPECIALIZATION_KIND_UNDECLARED: DeclTemplateSpecializationKind
DECL_TEMPLATE_SPECIALIZATION_KIND_IMPLICIT_INSTANTIATION: DeclTemplateSpecializationKind
DECL_TEMPLATE_SPECIALIZATION_KIND_EXPLICIT_SPECIALIZATION: DeclTemplateSpecializationKind
DECL_TEMPLATE_SPECIALIZATION_KIND_EXPLICIT_INSTANTIATION_DECLARATION: DeclTemplateSpecializationKind
DECL_TEMPLATE_SPECIALIZATION_KIND_EXPLICIT_INSTANTIATION_DEFINITION: DeclTemplateSpecializationKind
DECL_PRAGMA_COMMENT_KIND_UNSPECIFIED: DeclPragmaCommentKind
DECL_PRAGMA_COMMENT_KIND_UNKNOWN: DeclPragmaCommentKind
DECL_PRAGMA_COMMENT_KIND_LINKER: DeclPragmaCommentKind
DECL_PRAGMA_COMMENT_KIND_LIB: DeclPragmaCommentKind
DECL_PRAGMA_COMMENT_KIND_COMPILER: DeclPragmaCommentKind
DECL_PRAGMA_COMMENT_KIND_EXE_STR: DeclPragmaCommentKind
DECL_PRAGMA_COMMENT_KIND_USER: DeclPragmaCommentKind
DECL_BUILTIN_TEMPLATE_KIND_UNSPECIFIED: DeclBuiltinTemplateKind
DECL_BUILTIN_TEMPLATE_KIND_COMMON_TYPE: DeclBuiltinTemplateKind
DECL_BUILTIN_TEMPLATE_KIND_DEDUP_PACK: DeclBuiltinTemplateKind
DECL_BUILTIN_TEMPLATE_KIND_MAKE_INTEGER_SEQ: DeclBuiltinTemplateKind
DECL_BUILTIN_TEMPLATE_KIND_TYPE_PACK_ELEMENT: DeclBuiltinTemplateKind
DECL_VARIABLE_TLS_KIND_UNSPECIFIED: DeclVariableTLSKind
DECL_VARIABLE_TLS_KIND_NONE: DeclVariableTLSKind
DECL_VARIABLE_TLS_KIND_STATIC: DeclVariableTLSKind
DECL_VARIABLE_TLS_KIND_DYNAMIC: DeclVariableTLSKind
DECL_VARIABLE_INITIALIZATION_STYLE_UNSPECIFIED: DeclVariableInitializationStyle
DECL_VARIABLE_INITIALIZATION_STYLE_C: DeclVariableInitializationStyle
DECL_VARIABLE_INITIALIZATION_STYLE_CALL: DeclVariableInitializationStyle
DECL_VARIABLE_INITIALIZATION_STYLE_LIST: DeclVariableInitializationStyle
DECL_VARIABLE_INITIALIZATION_STYLE_PAREN_LIST: DeclVariableInitializationStyle
DECL_DEDUCTION_CANDIDATE_KIND_UNSPECIFIED: DeclDeductionCandidateKind
DECL_DEDUCTION_CANDIDATE_KIND_NORMAL: DeclDeductionCandidateKind
DECL_DEDUCTION_CANDIDATE_KIND_COPY: DeclDeductionCandidateKind
DECL_DEDUCTION_CANDIDATE_KIND_AGGREGATE: DeclDeductionCandidateKind
DECL_SOURCE_DEDUCTION_GUIDE_KIND_UNSPECIFIED: DeclSourceDeductionGuideKind
DECL_SOURCE_DEDUCTION_GUIDE_KIND_NONE: DeclSourceDeductionGuideKind
DECL_SOURCE_DEDUCTION_GUIDE_KIND_ALIAS: DeclSourceDeductionGuideKind
CHARACTER_KIND_UNSPECIFIED: CharacterKind
CHARACTER_KIND_ASCII: CharacterKind
CHARACTER_KIND_UTF8: CharacterKind
CHARACTER_KIND_UTF16: CharacterKind
CHARACTER_KIND_UTF32: CharacterKind
CHARACTER_KIND_WIDE: CharacterKind
STRING_LITERAL_KIND_UNSPECIFIED: StringLiteralKind
STRING_LITERAL_KIND_ORDINARY: StringLiteralKind
STRING_LITERAL_KIND_UTF8: StringLiteralKind
STRING_LITERAL_KIND_UTF16: StringLiteralKind
STRING_LITERAL_KIND_UTF32: StringLiteralKind
STRING_LITERAL_KIND_WIDE: StringLiteralKind
UNARY_EXPR_TRAIT_UNSPECIFIED: UnaryExprTrait
UNARY_EXPR_TRAIT_SIZEOF: UnaryExprTrait
UNARY_EXPR_TRAIT_ALIGNOF: UnaryExprTrait
UNARY_EXPR_TRAIT_OTHER: UnaryExprTrait
CONSTANT_EXPR_RESULT_UNSPECIFIED: ConstantExprResult
CONSTANT_EXPR_RESULT_SUCCEEDED: ConstantExprResult
CONSTANT_EXPR_RESULT_FAILED: ConstantExprResult
CONSTANT_EXPR_RESULT_SIDE_EFFECTS: ConstantExprResult
CONSTANT_EXPR_RESULT_NOT_EVALUATED: ConstantExprResult
SOURCE_LOC_EXPR_KIND_UNSPECIFIED: SourceLocExprKind
SOURCE_LOC_EXPR_KIND_LINE: SourceLocExprKind
SOURCE_LOC_EXPR_KIND_COLUMN: SourceLocExprKind
SOURCE_LOC_EXPR_KIND_FILE: SourceLocExprKind
SOURCE_LOC_EXPR_KIND_FUNCTION: SourceLocExprKind
PREDEFINED_IDENT_KIND_UNSPECIFIED: PredefinedIdentKind
PREDEFINED_IDENT_KIND_FUNC: PredefinedIdentKind
PREDEFINED_IDENT_KIND_FUNCTION: PredefinedIdentKind
PREDEFINED_IDENT_KIND_PRETTY_FUNCTION: PredefinedIdentKind
PREDEFINED_IDENT_KIND_OTHER: PredefinedIdentKind
ARRAY_TYPE_TRAIT_UNSPECIFIED: ArrayTypeTrait
ARRAY_TYPE_TRAIT_COUNT: ArrayTypeTrait
EXPRESSION_TRAIT_UNSPECIFIED: ExpressionTrait
EXPRESSION_TRAIT_IS_LVALUE: ExpressionTrait
EXPRESSION_TRAIT_IS_XVALUE: ExpressionTrait
EXPRESSION_TRAIT_IS_PRVALUE: ExpressionTrait
EXPRESSION_TRAIT_OTHER: ExpressionTrait
ATOMIC_OPCODE_UNSPECIFIED: AtomicOpcode
ATOMIC_OPCODE_LOAD: AtomicOpcode
ATOMIC_OPCODE_STORE: AtomicOpcode
ATOMIC_OPCODE_EXCHANGE: AtomicOpcode
ATOMIC_OPCODE_COMPARE_EXCHANGE: AtomicOpcode
ATOMIC_OPCODE_FETCH: AtomicOpcode
ATOMIC_OPCODE_OTHER: AtomicOpcode
TYPE_TRAIT_UNSPECIFIED: TypeTrait
TYPE_TRAIT_OTHER: TypeTrait
ARRAY_SIZE_MODIFIER_UNSPECIFIED: ArraySizeModifier
ARRAY_SIZE_MODIFIER_NORMAL: ArraySizeModifier
ARRAY_SIZE_MODIFIER_STATIC: ArraySizeModifier
ARRAY_SIZE_MODIFIER_STAR: ArraySizeModifier
TYPE_OF_KIND_UNSPECIFIED: TypeOfKind
TYPE_OF_KIND_QUALIFIED: TypeOfKind
TYPE_OF_KIND_UNQUALIFIED: TypeOfKind
AUTO_KEYWORD_UNSPECIFIED: AutoKeyword
AUTO_KEYWORD_AUTO: AutoKeyword
AUTO_KEYWORD_DECLTYPE_AUTO: AutoKeyword
AUTO_KEYWORD_GNU_AUTO_TYPE: AutoKeyword
VECTOR_KIND_UNSPECIFIED: VectorKind
VECTOR_KIND_GENERIC: VectorKind
VECTOR_KIND_ALTIVEC_VECTOR: VectorKind
VECTOR_KIND_ALTIVEC_PIXEL: VectorKind
VECTOR_KIND_ALTIVEC_BOOL: VectorKind
VECTOR_KIND_NEON: VectorKind
VECTOR_KIND_NEON_POLY: VectorKind
VECTOR_KIND_SVE_FIXED_DATA: VectorKind
VECTOR_KIND_SVE_FIXED_PREDICATE: VectorKind
VECTOR_KIND_RVV_FIXED_DATA: VectorKind
VECTOR_KIND_RVV_FIXED_MASK: VectorKind
VECTOR_KIND_RVV_FIXED_MASK_1: VectorKind
VECTOR_KIND_RVV_FIXED_MASK_2: VectorKind
VECTOR_KIND_RVV_FIXED_MASK_4: VectorKind
ATTRIBUTED_TYPE_KIND_UNSPECIFIED: AttributedTypeKind
ATTRIBUTED_TYPE_KIND_ADDRESS_SPACE: AttributedTypeKind
ATTRIBUTED_TYPE_KIND_NULLABILITY: AttributedTypeKind
ATTRIBUTED_TYPE_KIND_CALLING_CONVENTION: AttributedTypeKind
ATTRIBUTED_TYPE_KIND_VECTOR: AttributedTypeKind
ATTRIBUTED_TYPE_KIND_FIXED_POINT: AttributedTypeKind
ATTRIBUTED_TYPE_KIND_CPP_EXTENSION: AttributedTypeKind
PREDEFINED_TYPE_KIND_UNSPECIFIED: PredefinedTypeKind
PREDEFINED_TYPE_KIND_SIZE_T: PredefinedTypeKind
PREDEFINED_TYPE_KIND_SIGNED_SIZE_T: PredefinedTypeKind
PREDEFINED_TYPE_KIND_PTRDIFF_T: PredefinedTypeKind
DYNAMIC_COUNT_KIND_UNSPECIFIED: DynamicCountKind
DYNAMIC_COUNT_KIND_COUNTED_BY: DynamicCountKind
DYNAMIC_COUNT_KIND_SIZED_BY: DynamicCountKind
DYNAMIC_COUNT_KIND_COUNTED_BY_OR_NULL: DynamicCountKind
DYNAMIC_COUNT_KIND_SIZED_BY_OR_NULL: DynamicCountKind
UNARY_TRANSFORM_KIND_UNSPECIFIED: UnaryTransformKind
UNARY_TRANSFORM_KIND_ADD_LVALUE_REFERENCE: UnaryTransformKind
UNARY_TRANSFORM_KIND_ADD_POINTER: UnaryTransformKind
UNARY_TRANSFORM_KIND_ADD_RVALUE_REFERENCE: UnaryTransformKind
UNARY_TRANSFORM_KIND_DECAY: UnaryTransformKind
UNARY_TRANSFORM_KIND_MAKE_SIGNED: UnaryTransformKind
UNARY_TRANSFORM_KIND_MAKE_UNSIGNED: UnaryTransformKind
UNARY_TRANSFORM_KIND_REMOVE_ALL_EXTENTS: UnaryTransformKind
UNARY_TRANSFORM_KIND_REMOVE_CONST: UnaryTransformKind
UNARY_TRANSFORM_KIND_REMOVE_CV: UnaryTransformKind
UNARY_TRANSFORM_KIND_REMOVE_CV_REF: UnaryTransformKind
UNARY_TRANSFORM_KIND_REMOVE_EXTENT: UnaryTransformKind
UNARY_TRANSFORM_KIND_REMOVE_POINTER: UnaryTransformKind
UNARY_TRANSFORM_KIND_REMOVE_REFERENCE: UnaryTransformKind
UNARY_TRANSFORM_KIND_REMOVE_RESTRICT: UnaryTransformKind
UNARY_TRANSFORM_KIND_REMOVE_VOLATILE: UnaryTransformKind
UNARY_TRANSFORM_KIND_ENUM_UNDERLYING_TYPE: UnaryTransformKind
BUILTIN_KIND_UNSPECIFIED: BuiltinKind
BUILTIN_KIND_EXTENDED: BuiltinKind
BUILTIN_KIND_VOID: BuiltinKind
BUILTIN_KIND_BOOL: BuiltinKind
BUILTIN_KIND_CHAR_U: BuiltinKind
BUILTIN_KIND_UCHAR: BuiltinKind
BUILTIN_KIND_CHAR16: BuiltinKind
BUILTIN_KIND_CHAR32: BuiltinKind
BUILTIN_KIND_USHORT: BuiltinKind
BUILTIN_KIND_UINT: BuiltinKind
BUILTIN_KIND_ULONG: BuiltinKind
BUILTIN_KIND_ULONGLONG: BuiltinKind
BUILTIN_KIND_UINT128: BuiltinKind
BUILTIN_KIND_CHAR_S: BuiltinKind
BUILTIN_KIND_SCHAR: BuiltinKind
BUILTIN_KIND_SHORT: BuiltinKind
BUILTIN_KIND_INT: BuiltinKind
BUILTIN_KIND_LONG: BuiltinKind
BUILTIN_KIND_LONGLONG: BuiltinKind
BUILTIN_KIND_INT128: BuiltinKind
BUILTIN_KIND_HALF: BuiltinKind
BUILTIN_KIND_FLOAT: BuiltinKind
BUILTIN_KIND_DOUBLE: BuiltinKind
BUILTIN_KIND_LONGDOUBLE: BuiltinKind
BUILTIN_KIND_FLOAT128: BuiltinKind
BUILTIN_KIND_NULLPTR: BuiltinKind
BUILTIN_KIND_OVERLOAD: BuiltinKind
BUILTIN_KIND_DEPENDENT: BuiltinKind
BUILTIN_KIND_FLOAT16: BuiltinKind
BUILTIN_KIND_BFLOAT16: BuiltinKind
BUILTIN_KIND_CHAR8: BuiltinKind
BUILTIN_KIND_WCHAR_U: BuiltinKind
BUILTIN_KIND_WCHAR_S: BuiltinKind
FUNCTION_CALLING_CONVENTION_UNSPECIFIED: FunctionCallingConvention
FUNCTION_CALLING_CONVENTION_C: FunctionCallingConvention
FUNCTION_CALLING_CONVENTION_X86_STDCALL: FunctionCallingConvention
FUNCTION_CALLING_CONVENTION_X86_FASTCALL: FunctionCallingConvention
FUNCTION_CALLING_CONVENTION_X86_THISCALL: FunctionCallingConvention
FUNCTION_CALLING_CONVENTION_X86_VECTORCALL: FunctionCallingConvention
FUNCTION_CALLING_CONVENTION_WIN64: FunctionCallingConvention
FUNCTION_CALLING_CONVENTION_X86_64_SYSV: FunctionCallingConvention
FUNCTION_CALLING_CONVENTION_X86_REGCALL: FunctionCallingConvention
FUNCTION_CALLING_CONVENTION_AAPCS: FunctionCallingConvention
FUNCTION_CALLING_CONVENTION_AAPCS_VFP: FunctionCallingConvention
FUNCTION_CALLING_CONVENTION_SWIFT: FunctionCallingConvention
FUNCTION_CALLING_CONVENTION_SWIFT_ASYNC: FunctionCallingConvention
FUNCTION_CALLING_CONVENTION_PRESERVE_MOST: FunctionCallingConvention
FUNCTION_CALLING_CONVENTION_PRESERVE_ALL: FunctionCallingConvention
FUNCTION_CALLING_CONVENTION_AARCH64_VECTOR: FunctionCallingConvention
FUNCTION_CALLING_CONVENTION_AARCH64_SVE: FunctionCallingConvention
FUNCTION_CALLING_CONVENTION_PRESERVE_NONE: FunctionCallingConvention
FUNCTION_CALLING_CONVENTION_RISCV_VECTOR: FunctionCallingConvention
FUNCTION_CALLING_CONVENTION_TARGET_EXTENSION: FunctionCallingConvention
EXCEPTION_SPECIFICATION_UNSPECIFIED: ExceptionSpecification
EXCEPTION_SPECIFICATION_NONE: ExceptionSpecification
EXCEPTION_SPECIFICATION_DYNAMIC: ExceptionSpecification
EXCEPTION_SPECIFICATION_COMPUTED_NOEXCEPT: ExceptionSpecification
EXCEPTION_SPECIFICATION_NO_THROW: ExceptionSpecification
EXCEPTION_SPECIFICATION_MS_ANY: ExceptionSpecification
EXCEPTION_SPECIFICATION_MS_BASIC_NOEXCEPT: ExceptionSpecification
EXCEPTION_SPECIFICATION_OTHER: ExceptionSpecification
EXCEPTION_SPECIFICATION_DYNAMIC_NONE: ExceptionSpecification
EXCEPTION_SPECIFICATION_DEPENDENT_NOEXCEPT: ExceptionSpecification
EXCEPTION_SPECIFICATION_NOEXCEPT_FALSE: ExceptionSpecification
EXCEPTION_SPECIFICATION_NOEXCEPT_TRUE: ExceptionSpecification
EXCEPTION_SPECIFICATION_UNPARSED: ExceptionSpecification
EXCEPTION_SPECIFICATION_UNINSTANTIATED: ExceptionSpecification
EXCEPTION_SPECIFICATION_UNEVALUATED: ExceptionSpecification

class DeclarationSymbol(_message.Message):
    __slots__ = ("name", "qualified_name", "kind", "type", "function", "clang_class", "template_arguments", "is_parameter_pack", "overloaded_operator")
    NAME_FIELD_NUMBER: _ClassVar[int]
    QUALIFIED_NAME_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_FIELD_NUMBER: _ClassVar[int]
    CLANG_CLASS_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    IS_PARAMETER_PACK_FIELD_NUMBER: _ClassVar[int]
    OVERLOADED_OPERATOR_FIELD_NUMBER: _ClassVar[int]
    name: str
    qualified_name: str
    kind: SymbolKind
    type: TypeDescription
    function: FunctionSignature
    clang_class: str
    template_arguments: _containers.RepeatedCompositeFieldContainer[TemplateArgumentDescription]
    is_parameter_pack: bool
    overloaded_operator: _operators_pb2.OverloadedOperatorKind
    def __init__(self, name: _Optional[str] = ..., qualified_name: _Optional[str] = ..., kind: _Optional[_Union[SymbolKind, str]] = ..., type: _Optional[_Union[TypeDescription, _Mapping]] = ..., function: _Optional[_Union[FunctionSignature, _Mapping]] = ..., clang_class: _Optional[str] = ..., template_arguments: _Optional[_Iterable[_Union[TemplateArgumentDescription, _Mapping]]] = ..., is_parameter_pack: _Optional[bool] = ..., overloaded_operator: _Optional[_Union[_operators_pb2.OverloadedOperatorKind, str]] = ...) -> None: ...

class TypeDescription(_message.Message):
    __slots__ = ("spelling", "canonical_spelling", "qualifiers", "is_dependent")
    SPELLING_FIELD_NUMBER: _ClassVar[int]
    CANONICAL_SPELLING_FIELD_NUMBER: _ClassVar[int]
    QUALIFIERS_FIELD_NUMBER: _ClassVar[int]
    IS_DEPENDENT_FIELD_NUMBER: _ClassVar[int]
    spelling: str
    canonical_spelling: str
    qualifiers: _common_pb2.Qualifiers
    is_dependent: bool
    def __init__(self, spelling: _Optional[str] = ..., canonical_spelling: _Optional[str] = ..., qualifiers: _Optional[_Union[_common_pb2.Qualifiers, _Mapping]] = ..., is_dependent: _Optional[bool] = ...) -> None: ...

class TemplateArgumentDescription(_message.Message):
    __slots__ = ("kind", "semantic_spelling", "type", "integer", "floating", "pack_elements")
    KIND_FIELD_NUMBER: _ClassVar[int]
    SEMANTIC_SPELLING_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    INTEGER_FIELD_NUMBER: _ClassVar[int]
    FLOATING_FIELD_NUMBER: _ClassVar[int]
    PACK_ELEMENTS_FIELD_NUMBER: _ClassVar[int]
    kind: TemplateArgumentDescriptionKind
    semantic_spelling: str
    type: TypeDescription
    integer: APSIntBits
    floating: APFloatBits
    pack_elements: _containers.RepeatedCompositeFieldContainer[TemplateArgumentDescription]
    def __init__(self, kind: _Optional[_Union[TemplateArgumentDescriptionKind, str]] = ..., semantic_spelling: _Optional[str] = ..., type: _Optional[_Union[TypeDescription, _Mapping]] = ..., integer: _Optional[_Union[APSIntBits, _Mapping]] = ..., floating: _Optional[_Union[APFloatBits, _Mapping]] = ..., pack_elements: _Optional[_Iterable[_Union[TemplateArgumentDescription, _Mapping]]] = ...) -> None: ...

class TemplateParameterDescription(_message.Message):
    __slots__ = ("kind", "name", "type", "is_parameter_pack", "template_parameters")
    KIND_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    IS_PARAMETER_PACK_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    kind: TemplateParameterDescriptionKind
    name: str
    type: TypeDescription
    is_parameter_pack: bool
    template_parameters: _containers.RepeatedCompositeFieldContainer[TemplateParameterDescription]
    def __init__(self, kind: _Optional[_Union[TemplateParameterDescriptionKind, str]] = ..., name: _Optional[str] = ..., type: _Optional[_Union[TypeDescription, _Mapping]] = ..., is_parameter_pack: _Optional[bool] = ..., template_parameters: _Optional[_Iterable[_Union[TemplateParameterDescription, _Mapping]]] = ...) -> None: ...

class ConstraintDescription(_message.Message):
    __slots__ = ("semantic_expression", "is_dependent", "is_satisfied")
    SEMANTIC_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    IS_DEPENDENT_FIELD_NUMBER: _ClassVar[int]
    IS_SATISFIED_FIELD_NUMBER: _ClassVar[int]
    semantic_expression: str
    is_dependent: bool
    is_satisfied: bool
    def __init__(self, semantic_expression: _Optional[str] = ..., is_dependent: _Optional[bool] = ..., is_satisfied: _Optional[bool] = ...) -> None: ...

class ExceptionDescription(_message.Message):
    __slots__ = ("kind", "exception_types", "is_noexcept", "dependent_condition")
    KIND_FIELD_NUMBER: _ClassVar[int]
    EXCEPTION_TYPES_FIELD_NUMBER: _ClassVar[int]
    IS_NOEXCEPT_FIELD_NUMBER: _ClassVar[int]
    DEPENDENT_CONDITION_FIELD_NUMBER: _ClassVar[int]
    kind: ExceptionSpecification
    exception_types: _containers.RepeatedCompositeFieldContainer[TypeDescription]
    is_noexcept: bool
    dependent_condition: ConstraintDescription
    def __init__(self, kind: _Optional[_Union[ExceptionSpecification, str]] = ..., exception_types: _Optional[_Iterable[_Union[TypeDescription, _Mapping]]] = ..., is_noexcept: _Optional[bool] = ..., dependent_condition: _Optional[_Union[ConstraintDescription, _Mapping]] = ...) -> None: ...

class ParameterValue(_message.Message):
    __slots__ = ("name", "type", "is_parameter_pack")
    NAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    IS_PARAMETER_PACK_FIELD_NUMBER: _ClassVar[int]
    name: str
    type: TypeDescription
    is_parameter_pack: bool
    def __init__(self, name: _Optional[str] = ..., type: _Optional[_Union[TypeDescription, _Mapping]] = ..., is_parameter_pack: _Optional[bool] = ...) -> None: ...

class FunctionSignature(_message.Message):
    __slots__ = ("return_type", "parameters", "is_variadic", "is_const", "is_volatile", "ref_qualifier", "is_static", "calling_convention", "exception_specification", "template_parameters", "associated_constraints")
    RETURN_TYPE_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    IS_VARIADIC_FIELD_NUMBER: _ClassVar[int]
    IS_CONST_FIELD_NUMBER: _ClassVar[int]
    IS_VOLATILE_FIELD_NUMBER: _ClassVar[int]
    REF_QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    IS_STATIC_FIELD_NUMBER: _ClassVar[int]
    CALLING_CONVENTION_FIELD_NUMBER: _ClassVar[int]
    EXCEPTION_SPECIFICATION_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    ASSOCIATED_CONSTRAINTS_FIELD_NUMBER: _ClassVar[int]
    return_type: TypeDescription
    parameters: _containers.RepeatedCompositeFieldContainer[ParameterValue]
    is_variadic: bool
    is_const: bool
    is_volatile: bool
    ref_qualifier: _common_pb2.RefQualifier
    is_static: bool
    calling_convention: FunctionExtInfo
    exception_specification: ExceptionDescription
    template_parameters: _containers.RepeatedCompositeFieldContainer[TemplateParameterDescription]
    associated_constraints: _containers.RepeatedCompositeFieldContainer[ConstraintDescription]
    def __init__(self, return_type: _Optional[_Union[TypeDescription, _Mapping]] = ..., parameters: _Optional[_Iterable[_Union[ParameterValue, _Mapping]]] = ..., is_variadic: _Optional[bool] = ..., is_const: _Optional[bool] = ..., is_volatile: _Optional[bool] = ..., ref_qualifier: _Optional[_Union[_common_pb2.RefQualifier, str]] = ..., is_static: _Optional[bool] = ..., calling_convention: _Optional[_Union[FunctionExtInfo, _Mapping]] = ..., exception_specification: _Optional[_Union[ExceptionDescription, _Mapping]] = ..., template_parameters: _Optional[_Iterable[_Union[TemplateParameterDescription, _Mapping]]] = ..., associated_constraints: _Optional[_Iterable[_Union[ConstraintDescription, _Mapping]]] = ...) -> None: ...

class AttributeValue(_message.Message):
    __slots__ = ("clang_class", "state", "reason")
    CLANG_CLASS_FIELD_NUMBER: _ClassVar[int]
    STATE_FIELD_NUMBER: _ClassVar[int]
    REASON_FIELD_NUMBER: _ClassVar[int]
    clang_class: str
    state: _common_pb2.FieldState
    reason: str
    def __init__(self, clang_class: _Optional[str] = ..., state: _Optional[_Union[_common_pb2.FieldState, str]] = ..., reason: _Optional[str] = ...) -> None: ...

class CleanupValue(_message.Message):
    __slots__ = ("block", "compound_literal")
    BLOCK_FIELD_NUMBER: _ClassVar[int]
    COMPOUND_LITERAL_FIELD_NUMBER: _ClassVar[int]
    block: DeclarationSymbol
    compound_literal: ExpressionValue
    def __init__(self, block: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., compound_literal: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class QualType(_message.Message):
    __slots__ = ("type", "qualifiers")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    QUALIFIERS_FIELD_NUMBER: _ClassVar[int]
    type: TypeValue
    qualifiers: _common_pb2.Qualifiers
    def __init__(self, type: _Optional[_Union[TypeValue, _Mapping]] = ..., qualifiers: _Optional[_Union[_common_pb2.Qualifiers, _Mapping]] = ...) -> None: ...

class APIntBits(_message.Message):
    __slots__ = ("bit_width", "little_endian_bits", "unsigned_decimal")
    BIT_WIDTH_FIELD_NUMBER: _ClassVar[int]
    LITTLE_ENDIAN_BITS_FIELD_NUMBER: _ClassVar[int]
    UNSIGNED_DECIMAL_FIELD_NUMBER: _ClassVar[int]
    bit_width: int
    little_endian_bits: bytes
    unsigned_decimal: str
    def __init__(self, bit_width: _Optional[int] = ..., little_endian_bits: _Optional[bytes] = ..., unsigned_decimal: _Optional[str] = ...) -> None: ...

class APSIntBits(_message.Message):
    __slots__ = ("value", "is_unsigned", "decimal_value")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    IS_UNSIGNED_FIELD_NUMBER: _ClassVar[int]
    DECIMAL_VALUE_FIELD_NUMBER: _ClassVar[int]
    value: APIntBits
    is_unsigned: bool
    decimal_value: str
    def __init__(self, value: _Optional[_Union[APIntBits, _Mapping]] = ..., is_unsigned: _Optional[bool] = ..., decimal_value: _Optional[str] = ...) -> None: ...

class APFloatBits(_message.Message):
    __slots__ = ("semantics", "bit_pattern", "decimal_value")
    SEMANTICS_FIELD_NUMBER: _ClassVar[int]
    BIT_PATTERN_FIELD_NUMBER: _ClassVar[int]
    DECIMAL_VALUE_FIELD_NUMBER: _ClassVar[int]
    semantics: FloatingSemantics
    bit_pattern: APIntBits
    decimal_value: str
    def __init__(self, semantics: _Optional[_Union[FloatingSemantics, str]] = ..., bit_pattern: _Optional[_Union[APIntBits, _Mapping]] = ..., decimal_value: _Optional[str] = ...) -> None: ...

class APFixedPointBits(_message.Message):
    __slots__ = ("bit_pattern", "scale", "is_unsigned", "is_saturated", "has_unsigned_padding")
    BIT_PATTERN_FIELD_NUMBER: _ClassVar[int]
    SCALE_FIELD_NUMBER: _ClassVar[int]
    IS_UNSIGNED_FIELD_NUMBER: _ClassVar[int]
    IS_SATURATED_FIELD_NUMBER: _ClassVar[int]
    HAS_UNSIGNED_PADDING_FIELD_NUMBER: _ClassVar[int]
    bit_pattern: APIntBits
    scale: int
    is_unsigned: bool
    is_saturated: bool
    has_unsigned_padding: bool
    def __init__(self, bit_pattern: _Optional[_Union[APIntBits, _Mapping]] = ..., scale: _Optional[int] = ..., is_unsigned: _Optional[bool] = ..., is_saturated: _Optional[bool] = ..., has_unsigned_padding: _Optional[bool] = ...) -> None: ...

class DeclarationName(_message.Message):
    __slots__ = ("identifier", "constructor_type", "destructor_type", "conversion_type", "overloaded_operator", "literal_operator_suffix", "deduction_guide_template", "using_directive", "empty_name")
    IDENTIFIER_FIELD_NUMBER: _ClassVar[int]
    CONSTRUCTOR_TYPE_FIELD_NUMBER: _ClassVar[int]
    DESTRUCTOR_TYPE_FIELD_NUMBER: _ClassVar[int]
    CONVERSION_TYPE_FIELD_NUMBER: _ClassVar[int]
    OVERLOADED_OPERATOR_FIELD_NUMBER: _ClassVar[int]
    LITERAL_OPERATOR_SUFFIX_FIELD_NUMBER: _ClassVar[int]
    DEDUCTION_GUIDE_TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    USING_DIRECTIVE_FIELD_NUMBER: _ClassVar[int]
    EMPTY_NAME_FIELD_NUMBER: _ClassVar[int]
    identifier: str
    constructor_type: QualType
    destructor_type: QualType
    conversion_type: QualType
    overloaded_operator: _operators_pb2.OverloadedOperatorKind
    literal_operator_suffix: str
    deduction_guide_template: DeclarationSymbol
    using_directive: _common_pb2.Empty
    empty_name: _common_pb2.Empty
    def __init__(self, identifier: _Optional[str] = ..., constructor_type: _Optional[_Union[QualType, _Mapping]] = ..., destructor_type: _Optional[_Union[QualType, _Mapping]] = ..., conversion_type: _Optional[_Union[QualType, _Mapping]] = ..., overloaded_operator: _Optional[_Union[_operators_pb2.OverloadedOperatorKind, str]] = ..., literal_operator_suffix: _Optional[str] = ..., deduction_guide_template: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., using_directive: _Optional[_Union[_common_pb2.Empty, _Mapping]] = ..., empty_name: _Optional[_Union[_common_pb2.Empty, _Mapping]] = ...) -> None: ...

class NestedNamespaceName(_message.Message):
    __slots__ = ("declaration", "prefix")
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    PREFIX_FIELD_NUMBER: _ClassVar[int]
    declaration: DeclarationSymbol
    prefix: NestedNameSpecifier
    def __init__(self, declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., prefix: _Optional[_Union[NestedNameSpecifier, _Mapping]] = ...) -> None: ...

class NestedNameSpecifier(_message.Message):
    __slots__ = ("null_specifier", "namespace_name", "type", "microsoft_super_record")
    NULL_SPECIFIER_FIELD_NUMBER: _ClassVar[int]
    GLOBAL_FIELD_NUMBER: _ClassVar[int]
    NAMESPACE_NAME_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    MICROSOFT_SUPER_RECORD_FIELD_NUMBER: _ClassVar[int]
    null_specifier: _common_pb2.Empty
    namespace_name: NestedNamespaceName
    type: QualType
    microsoft_super_record: DeclarationSymbol
    def __init__(self, null_specifier: _Optional[_Union[_common_pb2.Empty, _Mapping]] = ..., namespace_name: _Optional[_Union[NestedNamespaceName, _Mapping]] = ..., type: _Optional[_Union[QualType, _Mapping]] = ..., microsoft_super_record: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., **kwargs) -> None: ...

class OverloadedTemplateName(_message.Message):
    __slots__ = ("declarations",)
    DECLARATIONS_FIELD_NUMBER: _ClassVar[int]
    declarations: _containers.RepeatedCompositeFieldContainer[DeclarationSymbol]
    def __init__(self, declarations: _Optional[_Iterable[_Union[DeclarationSymbol, _Mapping]]] = ...) -> None: ...

class QualifiedTemplateName(_message.Message):
    __slots__ = ("qualifier", "unqualified")
    QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    UNQUALIFIED_FIELD_NUMBER: _ClassVar[int]
    qualifier: NestedNameSpecifier
    unqualified: TemplateName
    def __init__(self, qualifier: _Optional[_Union[NestedNameSpecifier, _Mapping]] = ..., unqualified: _Optional[_Union[TemplateName, _Mapping]] = ...) -> None: ...

class DependentTemplateName(_message.Message):
    __slots__ = ("qualifier", "name")
    QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    qualifier: NestedNameSpecifier
    name: DeclarationName
    def __init__(self, qualifier: _Optional[_Union[NestedNameSpecifier, _Mapping]] = ..., name: _Optional[_Union[DeclarationName, _Mapping]] = ...) -> None: ...

class SubstitutedTemplateName(_message.Message):
    __slots__ = ("parameter", "replacement", "parameter_index", "pack_index", "is_final")
    PARAMETER_FIELD_NUMBER: _ClassVar[int]
    REPLACEMENT_FIELD_NUMBER: _ClassVar[int]
    PARAMETER_INDEX_FIELD_NUMBER: _ClassVar[int]
    PACK_INDEX_FIELD_NUMBER: _ClassVar[int]
    IS_FINAL_FIELD_NUMBER: _ClassVar[int]
    parameter: DeclarationSymbol
    replacement: TemplateName
    parameter_index: int
    pack_index: int
    is_final: bool
    def __init__(self, parameter: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., replacement: _Optional[_Union[TemplateName, _Mapping]] = ..., parameter_index: _Optional[int] = ..., pack_index: _Optional[int] = ..., is_final: _Optional[bool] = ...) -> None: ...

class SubstitutedTemplatePack(_message.Message):
    __slots__ = ("parameter", "arguments", "parameter_index", "is_final")
    PARAMETER_FIELD_NUMBER: _ClassVar[int]
    ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    PARAMETER_INDEX_FIELD_NUMBER: _ClassVar[int]
    IS_FINAL_FIELD_NUMBER: _ClassVar[int]
    parameter: DeclarationSymbol
    arguments: _containers.RepeatedCompositeFieldContainer[TemplateArgument]
    parameter_index: int
    is_final: bool
    def __init__(self, parameter: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., arguments: _Optional[_Iterable[_Union[TemplateArgument, _Mapping]]] = ..., parameter_index: _Optional[int] = ..., is_final: _Optional[bool] = ...) -> None: ...

class DeducedTemplateName(_message.Message):
    __slots__ = ("underlying", "default_arguments", "default_argument_start")
    UNDERLYING_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_ARGUMENT_START_FIELD_NUMBER: _ClassVar[int]
    underlying: TemplateName
    default_arguments: _containers.RepeatedCompositeFieldContainer[TemplateArgument]
    default_argument_start: int
    def __init__(self, underlying: _Optional[_Union[TemplateName, _Mapping]] = ..., default_arguments: _Optional[_Iterable[_Union[TemplateArgument, _Mapping]]] = ..., default_argument_start: _Optional[int] = ...) -> None: ...

class TemplateName(_message.Message):
    __slots__ = ("declaration", "overload", "assumed", "qualified", "dependent", "substituted", "substituted_pack", "using_shadow", "deduced", "null_name")
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    OVERLOAD_FIELD_NUMBER: _ClassVar[int]
    ASSUMED_FIELD_NUMBER: _ClassVar[int]
    QUALIFIED_FIELD_NUMBER: _ClassVar[int]
    DEPENDENT_FIELD_NUMBER: _ClassVar[int]
    SUBSTITUTED_FIELD_NUMBER: _ClassVar[int]
    SUBSTITUTED_PACK_FIELD_NUMBER: _ClassVar[int]
    USING_SHADOW_FIELD_NUMBER: _ClassVar[int]
    DEDUCED_FIELD_NUMBER: _ClassVar[int]
    NULL_NAME_FIELD_NUMBER: _ClassVar[int]
    declaration: DeclarationSymbol
    overload: OverloadedTemplateName
    assumed: DeclarationName
    qualified: QualifiedTemplateName
    dependent: DependentTemplateName
    substituted: SubstitutedTemplateName
    substituted_pack: SubstitutedTemplatePack
    using_shadow: DeclarationSymbol
    deduced: DeducedTemplateName
    null_name: _common_pb2.Empty
    def __init__(self, declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., overload: _Optional[_Union[OverloadedTemplateName, _Mapping]] = ..., assumed: _Optional[_Union[DeclarationName, _Mapping]] = ..., qualified: _Optional[_Union[QualifiedTemplateName, _Mapping]] = ..., dependent: _Optional[_Union[DependentTemplateName, _Mapping]] = ..., substituted: _Optional[_Union[SubstitutedTemplateName, _Mapping]] = ..., substituted_pack: _Optional[_Union[SubstitutedTemplatePack, _Mapping]] = ..., using_shadow: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., deduced: _Optional[_Union[DeducedTemplateName, _Mapping]] = ..., null_name: _Optional[_Union[_common_pb2.Empty, _Mapping]] = ...) -> None: ...

class IntegralTemplateArgument(_message.Message):
    __slots__ = ("value", "type")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    value: APSIntBits
    type: QualType
    def __init__(self, value: _Optional[_Union[APSIntBits, _Mapping]] = ..., type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class DeclarationTemplateArgument(_message.Message):
    __slots__ = ("declaration", "parameter_type")
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    PARAMETER_TYPE_FIELD_NUMBER: _ClassVar[int]
    declaration: DeclarationSymbol
    parameter_type: QualType
    def __init__(self, declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., parameter_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class StructuralTemplateArgument(_message.Message):
    __slots__ = ("value", "type")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    value: APValue
    type: QualType
    def __init__(self, value: _Optional[_Union[APValue, _Mapping]] = ..., type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class TemplateExpansionArgument(_message.Message):
    __slots__ = ("pattern", "expansion_count")
    PATTERN_FIELD_NUMBER: _ClassVar[int]
    EXPANSION_COUNT_FIELD_NUMBER: _ClassVar[int]
    pattern: TemplateName
    expansion_count: int
    def __init__(self, pattern: _Optional[_Union[TemplateName, _Mapping]] = ..., expansion_count: _Optional[int] = ...) -> None: ...

class TemplateArgumentPack(_message.Message):
    __slots__ = ("elements",)
    ELEMENTS_FIELD_NUMBER: _ClassVar[int]
    elements: _containers.RepeatedCompositeFieldContainer[TemplateArgument]
    def __init__(self, elements: _Optional[_Iterable[_Union[TemplateArgument, _Mapping]]] = ...) -> None: ...

class TemplateArgument(_message.Message):
    __slots__ = ("null_argument", "type", "declaration", "null_pointer_type", "integral", "structural_value", "template_name", "template_expansion", "expression", "pack")
    NULL_ARGUMENT_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    NULL_POINTER_TYPE_FIELD_NUMBER: _ClassVar[int]
    INTEGRAL_FIELD_NUMBER: _ClassVar[int]
    STRUCTURAL_VALUE_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_NAME_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_EXPANSION_FIELD_NUMBER: _ClassVar[int]
    EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    PACK_FIELD_NUMBER: _ClassVar[int]
    null_argument: _common_pb2.Empty
    type: QualType
    declaration: DeclarationTemplateArgument
    null_pointer_type: QualType
    integral: IntegralTemplateArgument
    structural_value: StructuralTemplateArgument
    template_name: TemplateName
    template_expansion: TemplateExpansionArgument
    expression: ExpressionValue
    pack: TemplateArgumentPack
    def __init__(self, null_argument: _Optional[_Union[_common_pb2.Empty, _Mapping]] = ..., type: _Optional[_Union[QualType, _Mapping]] = ..., declaration: _Optional[_Union[DeclarationTemplateArgument, _Mapping]] = ..., null_pointer_type: _Optional[_Union[QualType, _Mapping]] = ..., integral: _Optional[_Union[IntegralTemplateArgument, _Mapping]] = ..., structural_value: _Optional[_Union[StructuralTemplateArgument, _Mapping]] = ..., template_name: _Optional[_Union[TemplateName, _Mapping]] = ..., template_expansion: _Optional[_Union[TemplateExpansionArgument, _Mapping]] = ..., expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., pack: _Optional[_Union[TemplateArgumentPack, _Mapping]] = ...) -> None: ...

class TemplateParameterList(_message.Message):
    __slots__ = ("parameters", "requires_clause")
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    REQUIRES_CLAUSE_FIELD_NUMBER: _ClassVar[int]
    parameters: _containers.RepeatedCompositeFieldContainer[DeclarationValue]
    requires_clause: ExpressionValue
    def __init__(self, parameters: _Optional[_Iterable[_Union[DeclarationValue, _Mapping]]] = ..., requires_clause: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class CXXBaseSpecifier(_message.Message):
    __slots__ = ("type", "access", "is_virtual", "is_pack_expansion")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    ACCESS_FIELD_NUMBER: _ClassVar[int]
    IS_VIRTUAL_FIELD_NUMBER: _ClassVar[int]
    IS_PACK_EXPANSION_FIELD_NUMBER: _ClassVar[int]
    type: QualType
    access: _common_pb2.AccessSpecifier
    is_virtual: bool
    is_pack_expansion: bool
    def __init__(self, type: _Optional[_Union[QualType, _Mapping]] = ..., access: _Optional[_Union[_common_pb2.AccessSpecifier, str]] = ..., is_virtual: _Optional[bool] = ..., is_pack_expansion: _Optional[bool] = ...) -> None: ...

class CXXCtorInitializer(_message.Message):
    __slots__ = ("initializer", "is_virtual_base", "is_pack_expansion", "base_type", "member", "indirect_member", "delegating_type")
    INITIALIZER_FIELD_NUMBER: _ClassVar[int]
    IS_VIRTUAL_BASE_FIELD_NUMBER: _ClassVar[int]
    IS_PACK_EXPANSION_FIELD_NUMBER: _ClassVar[int]
    BASE_TYPE_FIELD_NUMBER: _ClassVar[int]
    MEMBER_FIELD_NUMBER: _ClassVar[int]
    INDIRECT_MEMBER_FIELD_NUMBER: _ClassVar[int]
    DELEGATING_TYPE_FIELD_NUMBER: _ClassVar[int]
    initializer: ExpressionValue
    is_virtual_base: bool
    is_pack_expansion: bool
    base_type: QualType
    member: DeclarationSymbol
    indirect_member: DeclarationSymbol
    delegating_type: QualType
    def __init__(self, initializer: _Optional[_Union[ExpressionValue, _Mapping]] = ..., is_virtual_base: _Optional[bool] = ..., is_pack_expansion: _Optional[bool] = ..., base_type: _Optional[_Union[QualType, _Mapping]] = ..., member: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., indirect_member: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., delegating_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class LambdaCapture(_message.Message):
    __slots__ = ("kind", "variable", "is_implicit", "is_pack_expansion")
    KIND_FIELD_NUMBER: _ClassVar[int]
    VARIABLE_FIELD_NUMBER: _ClassVar[int]
    IS_IMPLICIT_FIELD_NUMBER: _ClassVar[int]
    IS_PACK_EXPANSION_FIELD_NUMBER: _ClassVar[int]
    kind: LambdaCaptureKind
    variable: DeclarationSymbol
    is_implicit: bool
    is_pack_expansion: bool
    def __init__(self, kind: _Optional[_Union[LambdaCaptureKind, str]] = ..., variable: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., is_implicit: _Optional[bool] = ..., is_pack_expansion: _Optional[bool] = ...) -> None: ...

class CXXTemporary(_message.Message):
    __slots__ = ("destructor",)
    DESTRUCTOR_FIELD_NUMBER: _ClassVar[int]
    destructor: DeclarationSymbol
    def __init__(self, destructor: _Optional[_Union[DeclarationSymbol, _Mapping]] = ...) -> None: ...

class ConceptReference(_message.Message):
    __slots__ = ("concept_declaration", "found_declaration", "qualifier", "name", "arguments")
    CONCEPT_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    FOUND_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    concept_declaration: DeclarationSymbol
    found_declaration: DeclarationSymbol
    qualifier: NestedNameSpecifier
    name: DeclarationName
    arguments: _containers.RepeatedCompositeFieldContainer[TemplateArgument]
    def __init__(self, concept_declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., found_declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., qualifier: _Optional[_Union[NestedNameSpecifier, _Mapping]] = ..., name: _Optional[_Union[DeclarationName, _Mapping]] = ..., arguments: _Optional[_Iterable[_Union[TemplateArgument, _Mapping]]] = ...) -> None: ...

class TypeConstraint(_message.Message):
    __slots__ = ("concept_reference", "immediately_declared_constraint", "argument_pack_substitution_index")
    CONCEPT_REFERENCE_FIELD_NUMBER: _ClassVar[int]
    IMMEDIATELY_DECLARED_CONSTRAINT_FIELD_NUMBER: _ClassVar[int]
    ARGUMENT_PACK_SUBSTITUTION_INDEX_FIELD_NUMBER: _ClassVar[int]
    concept_reference: ConceptReference
    immediately_declared_constraint: ExpressionValue
    argument_pack_substitution_index: int
    def __init__(self, concept_reference: _Optional[_Union[ConceptReference, _Mapping]] = ..., immediately_declared_constraint: _Optional[_Union[ExpressionValue, _Mapping]] = ..., argument_pack_substitution_index: _Optional[int] = ...) -> None: ...

class SubstitutionDiagnostic(_message.Message):
    __slots__ = ("message",)
    MESSAGE_FIELD_NUMBER: _ClassVar[int]
    message: str
    def __init__(self, message: _Optional[str] = ...) -> None: ...

class ConstraintDetail(_message.Message):
    __slots__ = ("substituted_constraint", "diagnostic", "concept_reference")
    SUBSTITUTED_CONSTRAINT_FIELD_NUMBER: _ClassVar[int]
    DIAGNOSTIC_FIELD_NUMBER: _ClassVar[int]
    CONCEPT_REFERENCE_FIELD_NUMBER: _ClassVar[int]
    substituted_constraint: ExpressionValue
    diagnostic: SubstitutionDiagnostic
    concept_reference: ConceptReference
    def __init__(self, substituted_constraint: _Optional[_Union[ExpressionValue, _Mapping]] = ..., diagnostic: _Optional[_Union[SubstitutionDiagnostic, _Mapping]] = ..., concept_reference: _Optional[_Union[ConceptReference, _Mapping]] = ...) -> None: ...

class ConstraintSatisfaction(_message.Message):
    __slots__ = ("is_satisfied", "contains_errors", "details")
    IS_SATISFIED_FIELD_NUMBER: _ClassVar[int]
    CONTAINS_ERRORS_FIELD_NUMBER: _ClassVar[int]
    DETAILS_FIELD_NUMBER: _ClassVar[int]
    is_satisfied: bool
    contains_errors: bool
    details: _containers.RepeatedCompositeFieldContainer[ConstraintDetail]
    def __init__(self, is_satisfied: _Optional[bool] = ..., contains_errors: _Optional[bool] = ..., details: _Optional[_Iterable[_Union[ConstraintDetail, _Mapping]]] = ...) -> None: ...

class RequirementInfo(_message.Message):
    __slots__ = ("is_dependent", "contains_unexpanded_parameter_pack", "is_satisfied")
    IS_DEPENDENT_FIELD_NUMBER: _ClassVar[int]
    CONTAINS_UNEXPANDED_PARAMETER_PACK_FIELD_NUMBER: _ClassVar[int]
    IS_SATISFIED_FIELD_NUMBER: _ClassVar[int]
    is_dependent: bool
    contains_unexpanded_parameter_pack: bool
    is_satisfied: bool
    def __init__(self, is_dependent: _Optional[bool] = ..., contains_unexpanded_parameter_pack: _Optional[bool] = ..., is_satisfied: _Optional[bool] = ...) -> None: ...

class TypeRequirement(_message.Message):
    __slots__ = ("requirement", "required_type", "substitution_error")
    REQUIREMENT_FIELD_NUMBER: _ClassVar[int]
    REQUIRED_TYPE_FIELD_NUMBER: _ClassVar[int]
    SUBSTITUTION_ERROR_FIELD_NUMBER: _ClassVar[int]
    requirement: RequirementInfo
    required_type: QualType
    substitution_error: SubstitutionDiagnostic
    def __init__(self, requirement: _Optional[_Union[RequirementInfo, _Mapping]] = ..., required_type: _Optional[_Union[QualType, _Mapping]] = ..., substitution_error: _Optional[_Union[SubstitutionDiagnostic, _Mapping]] = ...) -> None: ...

class ReturnTypeRequirement(_message.Message):
    __slots__ = ("is_dependent", "unconstrained", "constraint_parameters", "substitution_error", "contains_unexpanded_parameter_pack")
    IS_DEPENDENT_FIELD_NUMBER: _ClassVar[int]
    UNCONSTRAINED_FIELD_NUMBER: _ClassVar[int]
    CONSTRAINT_PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    SUBSTITUTION_ERROR_FIELD_NUMBER: _ClassVar[int]
    CONTAINS_UNEXPANDED_PARAMETER_PACK_FIELD_NUMBER: _ClassVar[int]
    is_dependent: bool
    unconstrained: _common_pb2.Empty
    constraint_parameters: TemplateParameterList
    substitution_error: SubstitutionDiagnostic
    contains_unexpanded_parameter_pack: bool
    def __init__(self, is_dependent: _Optional[bool] = ..., unconstrained: _Optional[_Union[_common_pb2.Empty, _Mapping]] = ..., constraint_parameters: _Optional[_Union[TemplateParameterList, _Mapping]] = ..., substitution_error: _Optional[_Union[SubstitutionDiagnostic, _Mapping]] = ..., contains_unexpanded_parameter_pack: _Optional[bool] = ...) -> None: ...

class ExprRequirement(_message.Message):
    __slots__ = ("requirement", "is_simple", "return_type", "satisfaction_status", "substituted_return_type_constraint", "expression", "substitution_error")
    REQUIREMENT_FIELD_NUMBER: _ClassVar[int]
    IS_SIMPLE_FIELD_NUMBER: _ClassVar[int]
    RETURN_TYPE_FIELD_NUMBER: _ClassVar[int]
    SATISFACTION_STATUS_FIELD_NUMBER: _ClassVar[int]
    SUBSTITUTED_RETURN_TYPE_CONSTRAINT_FIELD_NUMBER: _ClassVar[int]
    EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    SUBSTITUTION_ERROR_FIELD_NUMBER: _ClassVar[int]
    requirement: RequirementInfo
    is_simple: bool
    return_type: ReturnTypeRequirement
    satisfaction_status: ExprRequirementSatisfactionStatus
    substituted_return_type_constraint: ExpressionValue
    expression: ExpressionValue
    substitution_error: SubstitutionDiagnostic
    def __init__(self, requirement: _Optional[_Union[RequirementInfo, _Mapping]] = ..., is_simple: _Optional[bool] = ..., return_type: _Optional[_Union[ReturnTypeRequirement, _Mapping]] = ..., satisfaction_status: _Optional[_Union[ExprRequirementSatisfactionStatus, str]] = ..., substituted_return_type_constraint: _Optional[_Union[ExpressionValue, _Mapping]] = ..., expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., substitution_error: _Optional[_Union[SubstitutionDiagnostic, _Mapping]] = ...) -> None: ...

class NestedRequirement(_message.Message):
    __slots__ = ("requirement", "constraint_expression", "satisfaction", "has_invalid_constraint", "invalid_constraint_entity")
    REQUIREMENT_FIELD_NUMBER: _ClassVar[int]
    CONSTRAINT_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    SATISFACTION_FIELD_NUMBER: _ClassVar[int]
    HAS_INVALID_CONSTRAINT_FIELD_NUMBER: _ClassVar[int]
    INVALID_CONSTRAINT_ENTITY_FIELD_NUMBER: _ClassVar[int]
    requirement: RequirementInfo
    constraint_expression: ExpressionValue
    satisfaction: ConstraintSatisfaction
    has_invalid_constraint: bool
    invalid_constraint_entity: str
    def __init__(self, requirement: _Optional[_Union[RequirementInfo, _Mapping]] = ..., constraint_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., satisfaction: _Optional[_Union[ConstraintSatisfaction, _Mapping]] = ..., has_invalid_constraint: _Optional[bool] = ..., invalid_constraint_entity: _Optional[str] = ...) -> None: ...

class ConceptRequirement(_message.Message):
    __slots__ = ("type", "expression", "nested")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    NESTED_FIELD_NUMBER: _ClassVar[int]
    type: TypeRequirement
    expression: ExprRequirement
    nested: NestedRequirement
    def __init__(self, type: _Optional[_Union[TypeRequirement, _Mapping]] = ..., expression: _Optional[_Union[ExprRequirement, _Mapping]] = ..., nested: _Optional[_Union[NestedRequirement, _Mapping]] = ...) -> None: ...

class ComplexIntValue(_message.Message):
    __slots__ = ("real", "imaginary")
    REAL_FIELD_NUMBER: _ClassVar[int]
    IMAGINARY_FIELD_NUMBER: _ClassVar[int]
    real: APSIntBits
    imaginary: APSIntBits
    def __init__(self, real: _Optional[_Union[APSIntBits, _Mapping]] = ..., imaginary: _Optional[_Union[APSIntBits, _Mapping]] = ...) -> None: ...

class ComplexFloatValue(_message.Message):
    __slots__ = ("real", "imaginary")
    REAL_FIELD_NUMBER: _ClassVar[int]
    IMAGINARY_FIELD_NUMBER: _ClassVar[int]
    real: APFloatBits
    imaginary: APFloatBits
    def __init__(self, real: _Optional[_Union[APFloatBits, _Mapping]] = ..., imaginary: _Optional[_Union[APFloatBits, _Mapping]] = ...) -> None: ...

class APValueSequence(_message.Message):
    __slots__ = ("elements",)
    ELEMENTS_FIELD_NUMBER: _ClassVar[int]
    elements: _containers.RepeatedCompositeFieldContainer[APValue]
    def __init__(self, elements: _Optional[_Iterable[_Union[APValue, _Mapping]]] = ...) -> None: ...

class APArrayValue(_message.Message):
    __slots__ = ("initialized_elements", "filler", "size")
    INITIALIZED_ELEMENTS_FIELD_NUMBER: _ClassVar[int]
    FILLER_FIELD_NUMBER: _ClassVar[int]
    SIZE_FIELD_NUMBER: _ClassVar[int]
    initialized_elements: _containers.RepeatedCompositeFieldContainer[APValue]
    filler: APValue
    size: int
    def __init__(self, initialized_elements: _Optional[_Iterable[_Union[APValue, _Mapping]]] = ..., filler: _Optional[_Union[APValue, _Mapping]] = ..., size: _Optional[int] = ...) -> None: ...

class APStructBaseValue(_message.Message):
    __slots__ = ("type", "value")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    type: TypeDescription
    value: APValue
    def __init__(self, type: _Optional[_Union[TypeDescription, _Mapping]] = ..., value: _Optional[_Union[APValue, _Mapping]] = ...) -> None: ...

class APStructFieldValue(_message.Message):
    __slots__ = ("field", "value")
    FIELD_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    field: DeclarationSymbol
    value: APValue
    def __init__(self, field: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., value: _Optional[_Union[APValue, _Mapping]] = ...) -> None: ...

class APStructValue(_message.Message):
    __slots__ = ("base_values", "field_values")
    BASE_VALUES_FIELD_NUMBER: _ClassVar[int]
    FIELD_VALUES_FIELD_NUMBER: _ClassVar[int]
    base_values: _containers.RepeatedCompositeFieldContainer[APStructBaseValue]
    field_values: _containers.RepeatedCompositeFieldContainer[APStructFieldValue]
    def __init__(self, base_values: _Optional[_Iterable[_Union[APStructBaseValue, _Mapping]]] = ..., field_values: _Optional[_Iterable[_Union[APStructFieldValue, _Mapping]]] = ...) -> None: ...

class APUnionValue(_message.Message):
    __slots__ = ("active_field", "value")
    ACTIVE_FIELD_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    active_field: DeclarationSymbol
    value: APValue
    def __init__(self, active_field: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., value: _Optional[_Union[APValue, _Mapping]] = ...) -> None: ...

class APTypeInfoLValue(_message.Message):
    __slots__ = ("type",)
    TYPE_FIELD_NUMBER: _ClassVar[int]
    type: QualType
    def __init__(self, type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class APDynamicAllocation(_message.Message):
    __slots__ = ("type",)
    TYPE_FIELD_NUMBER: _ClassVar[int]
    type: QualType
    def __init__(self, type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class APLValueBase(_message.Message):
    __slots__ = ("null_base", "declaration", "expression", "type_info", "dynamic_allocation")
    NULL_BASE_FIELD_NUMBER: _ClassVar[int]
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    TYPE_INFO_FIELD_NUMBER: _ClassVar[int]
    DYNAMIC_ALLOCATION_FIELD_NUMBER: _ClassVar[int]
    null_base: _common_pb2.Empty
    declaration: DeclarationSymbol
    expression: ExpressionValue
    type_info: APTypeInfoLValue
    dynamic_allocation: APDynamicAllocation
    def __init__(self, null_base: _Optional[_Union[_common_pb2.Empty, _Mapping]] = ..., declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., type_info: _Optional[_Union[APTypeInfoLValue, _Mapping]] = ..., dynamic_allocation: _Optional[_Union[APDynamicAllocation, _Mapping]] = ...) -> None: ...

class APLValuePathEntry(_message.Message):
    __slots__ = ("is_virtual_base", "array_index", "declaration")
    IS_VIRTUAL_BASE_FIELD_NUMBER: _ClassVar[int]
    ARRAY_INDEX_FIELD_NUMBER: _ClassVar[int]
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    is_virtual_base: bool
    array_index: int
    declaration: DeclarationSymbol
    def __init__(self, is_virtual_base: _Optional[bool] = ..., array_index: _Optional[int] = ..., declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ...) -> None: ...

class APLValue(_message.Message):
    __slots__ = ("base", "offset_bytes", "path", "is_one_past_end", "is_null_pointer")
    BASE_FIELD_NUMBER: _ClassVar[int]
    OFFSET_BYTES_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    IS_ONE_PAST_END_FIELD_NUMBER: _ClassVar[int]
    IS_NULL_POINTER_FIELD_NUMBER: _ClassVar[int]
    base: APLValueBase
    offset_bytes: int
    path: _containers.RepeatedCompositeFieldContainer[APLValuePathEntry]
    is_one_past_end: bool
    is_null_pointer: bool
    def __init__(self, base: _Optional[_Union[APLValueBase, _Mapping]] = ..., offset_bytes: _Optional[int] = ..., path: _Optional[_Iterable[_Union[APLValuePathEntry, _Mapping]]] = ..., is_one_past_end: _Optional[bool] = ..., is_null_pointer: _Optional[bool] = ...) -> None: ...

class APMemberPointer(_message.Message):
    __slots__ = ("declaration", "path", "is_derived_member")
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    PATH_FIELD_NUMBER: _ClassVar[int]
    IS_DERIVED_MEMBER_FIELD_NUMBER: _ClassVar[int]
    declaration: DeclarationSymbol
    path: _containers.RepeatedCompositeFieldContainer[DeclarationSymbol]
    is_derived_member: bool
    def __init__(self, declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., path: _Optional[_Iterable[_Union[DeclarationSymbol, _Mapping]]] = ..., is_derived_member: _Optional[bool] = ...) -> None: ...

class APAddrLabelDiff(_message.Message):
    __slots__ = ("left_expression", "right_expression")
    LEFT_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    RIGHT_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    left_expression: ExpressionValue
    right_expression: ExpressionValue
    def __init__(self, left_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., right_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class APValue(_message.Message):
    __slots__ = ("no_object", "indeterminate", "integer", "floating", "fixed_point", "complex_integer", "complex_floating", "lvalue", "vector", "array", "structure", "union_value", "member_pointer", "address_label_difference")
    NO_OBJECT_FIELD_NUMBER: _ClassVar[int]
    INDETERMINATE_FIELD_NUMBER: _ClassVar[int]
    INTEGER_FIELD_NUMBER: _ClassVar[int]
    FLOATING_FIELD_NUMBER: _ClassVar[int]
    FIXED_POINT_FIELD_NUMBER: _ClassVar[int]
    COMPLEX_INTEGER_FIELD_NUMBER: _ClassVar[int]
    COMPLEX_FLOATING_FIELD_NUMBER: _ClassVar[int]
    LVALUE_FIELD_NUMBER: _ClassVar[int]
    VECTOR_FIELD_NUMBER: _ClassVar[int]
    ARRAY_FIELD_NUMBER: _ClassVar[int]
    STRUCTURE_FIELD_NUMBER: _ClassVar[int]
    UNION_VALUE_FIELD_NUMBER: _ClassVar[int]
    MEMBER_POINTER_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_LABEL_DIFFERENCE_FIELD_NUMBER: _ClassVar[int]
    no_object: _common_pb2.Empty
    indeterminate: _common_pb2.Empty
    integer: APSIntBits
    floating: APFloatBits
    fixed_point: APFixedPointBits
    complex_integer: ComplexIntValue
    complex_floating: ComplexFloatValue
    lvalue: APLValue
    vector: APValueSequence
    array: APArrayValue
    structure: APStructValue
    union_value: APUnionValue
    member_pointer: APMemberPointer
    address_label_difference: APAddrLabelDiff
    def __init__(self, no_object: _Optional[_Union[_common_pb2.Empty, _Mapping]] = ..., indeterminate: _Optional[_Union[_common_pb2.Empty, _Mapping]] = ..., integer: _Optional[_Union[APSIntBits, _Mapping]] = ..., floating: _Optional[_Union[APFloatBits, _Mapping]] = ..., fixed_point: _Optional[_Union[APFixedPointBits, _Mapping]] = ..., complex_integer: _Optional[_Union[ComplexIntValue, _Mapping]] = ..., complex_floating: _Optional[_Union[ComplexFloatValue, _Mapping]] = ..., lvalue: _Optional[_Union[APLValue, _Mapping]] = ..., vector: _Optional[_Union[APValueSequence, _Mapping]] = ..., array: _Optional[_Union[APArrayValue, _Mapping]] = ..., structure: _Optional[_Union[APStructValue, _Mapping]] = ..., union_value: _Optional[_Union[APUnionValue, _Mapping]] = ..., member_pointer: _Optional[_Union[APMemberPointer, _Mapping]] = ..., address_label_difference: _Optional[_Union[APAddrLabelDiff, _Mapping]] = ...) -> None: ...

class DeclInfo(_message.Message):
    __slots__ = ("containing_scope", "attributes", "is_implicit", "is_invalid")
    CONTAINING_SCOPE_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    IS_IMPLICIT_FIELD_NUMBER: _ClassVar[int]
    IS_INVALID_FIELD_NUMBER: _ClassVar[int]
    containing_scope: DeclarationSymbol
    attributes: _containers.RepeatedCompositeFieldContainer[AttributeValue]
    is_implicit: bool
    is_invalid: bool
    def __init__(self, containing_scope: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., attributes: _Optional[_Iterable[_Union[AttributeValue, _Mapping]]] = ..., is_implicit: _Optional[bool] = ..., is_invalid: _Optional[bool] = ...) -> None: ...

class NamedDeclInfo(_message.Message):
    __slots__ = ("declaration", "name", "qualified_name")
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    QUALIFIED_NAME_FIELD_NUMBER: _ClassVar[int]
    declaration: DeclInfo
    name: DeclarationName
    qualified_name: str
    def __init__(self, declaration: _Optional[_Union[DeclInfo, _Mapping]] = ..., name: _Optional[_Union[DeclarationName, _Mapping]] = ..., qualified_name: _Optional[str] = ...) -> None: ...

class TypeDeclInfo(_message.Message):
    __slots__ = ("named", "declared_type")
    NAMED_FIELD_NUMBER: _ClassVar[int]
    DECLARED_TYPE_FIELD_NUMBER: _ClassVar[int]
    named: NamedDeclInfo
    declared_type: TypeValue
    def __init__(self, named: _Optional[_Union[NamedDeclInfo, _Mapping]] = ..., declared_type: _Optional[_Union[TypeValue, _Mapping]] = ...) -> None: ...

class TagDeclInfo(_message.Message):
    __slots__ = ("type_declaration", "tag_kind", "is_complete_definition")
    TYPE_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    TAG_KIND_FIELD_NUMBER: _ClassVar[int]
    IS_COMPLETE_DEFINITION_FIELD_NUMBER: _ClassVar[int]
    type_declaration: TypeDeclInfo
    tag_kind: _common_pb2.TagKind
    is_complete_definition: bool
    def __init__(self, type_declaration: _Optional[_Union[TypeDeclInfo, _Mapping]] = ..., tag_kind: _Optional[_Union[_common_pb2.TagKind, str]] = ..., is_complete_definition: _Optional[bool] = ...) -> None: ...

class RecordDeclInfo(_message.Message):
    __slots__ = ("tag", "members")
    TAG_FIELD_NUMBER: _ClassVar[int]
    MEMBERS_FIELD_NUMBER: _ClassVar[int]
    tag: TagDeclInfo
    members: _containers.RepeatedCompositeFieldContainer[DeclarationValue]
    def __init__(self, tag: _Optional[_Union[TagDeclInfo, _Mapping]] = ..., members: _Optional[_Iterable[_Union[DeclarationValue, _Mapping]]] = ...) -> None: ...

class ValueDeclInfo(_message.Message):
    __slots__ = ("named", "type")
    NAMED_FIELD_NUMBER: _ClassVar[int]
    TYPE_FIELD_NUMBER: _ClassVar[int]
    named: NamedDeclInfo
    type: QualType
    def __init__(self, named: _Optional[_Union[NamedDeclInfo, _Mapping]] = ..., type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class DeclaratorDeclInfo(_message.Message):
    __slots__ = ("value", "declared_type")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    DECLARED_TYPE_FIELD_NUMBER: _ClassVar[int]
    value: ValueDeclInfo
    declared_type: QualType
    def __init__(self, value: _Optional[_Union[ValueDeclInfo, _Mapping]] = ..., declared_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class FunctionDeclInfo(_message.Message):
    __slots__ = ("declarator", "return_type", "parameters", "body", "is_this_declaration_a_definition", "is_variadic", "is_constexpr", "storage_class")
    DECLARATOR_FIELD_NUMBER: _ClassVar[int]
    RETURN_TYPE_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    IS_THIS_DECLARATION_A_DEFINITION_FIELD_NUMBER: _ClassVar[int]
    IS_VARIADIC_FIELD_NUMBER: _ClassVar[int]
    IS_CONSTEXPR_FIELD_NUMBER: _ClassVar[int]
    STORAGE_CLASS_FIELD_NUMBER: _ClassVar[int]
    declarator: DeclaratorDeclInfo
    return_type: QualType
    parameters: _containers.RepeatedCompositeFieldContainer[DeclarationValue]
    body: StatementValue
    is_this_declaration_a_definition: bool
    is_variadic: bool
    is_constexpr: bool
    storage_class: _common_pb2.StorageClass
    def __init__(self, declarator: _Optional[_Union[DeclaratorDeclInfo, _Mapping]] = ..., return_type: _Optional[_Union[QualType, _Mapping]] = ..., parameters: _Optional[_Iterable[_Union[DeclarationValue, _Mapping]]] = ..., body: _Optional[_Union[StatementValue, _Mapping]] = ..., is_this_declaration_a_definition: _Optional[bool] = ..., is_variadic: _Optional[bool] = ..., is_constexpr: _Optional[bool] = ..., storage_class: _Optional[_Union[_common_pb2.StorageClass, str]] = ...) -> None: ...

class CXXMethodDeclInfo(_message.Message):
    __slots__ = ("function", "parent_record", "is_static", "is_virtual", "is_const", "is_volatile", "ref_qualifier", "overridden_methods")
    FUNCTION_FIELD_NUMBER: _ClassVar[int]
    PARENT_RECORD_FIELD_NUMBER: _ClassVar[int]
    IS_STATIC_FIELD_NUMBER: _ClassVar[int]
    IS_VIRTUAL_FIELD_NUMBER: _ClassVar[int]
    IS_CONST_FIELD_NUMBER: _ClassVar[int]
    IS_VOLATILE_FIELD_NUMBER: _ClassVar[int]
    REF_QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    OVERRIDDEN_METHODS_FIELD_NUMBER: _ClassVar[int]
    function: FunctionDeclInfo
    parent_record: DeclarationSymbol
    is_static: bool
    is_virtual: bool
    is_const: bool
    is_volatile: bool
    ref_qualifier: _common_pb2.RefQualifier
    overridden_methods: _containers.RepeatedCompositeFieldContainer[DeclarationSymbol]
    def __init__(self, function: _Optional[_Union[FunctionDeclInfo, _Mapping]] = ..., parent_record: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., is_static: _Optional[bool] = ..., is_virtual: _Optional[bool] = ..., is_const: _Optional[bool] = ..., is_volatile: _Optional[bool] = ..., ref_qualifier: _Optional[_Union[_common_pb2.RefQualifier, str]] = ..., overridden_methods: _Optional[_Iterable[_Union[DeclarationSymbol, _Mapping]]] = ...) -> None: ...

class VarDeclInfo(_message.Message):
    __slots__ = ("declarator", "initializer", "storage_class", "is_constexpr")
    DECLARATOR_FIELD_NUMBER: _ClassVar[int]
    INITIALIZER_FIELD_NUMBER: _ClassVar[int]
    STORAGE_CLASS_FIELD_NUMBER: _ClassVar[int]
    IS_CONSTEXPR_FIELD_NUMBER: _ClassVar[int]
    declarator: DeclaratorDeclInfo
    initializer: ExpressionValue
    storage_class: _common_pb2.StorageClass
    is_constexpr: bool
    def __init__(self, declarator: _Optional[_Union[DeclaratorDeclInfo, _Mapping]] = ..., initializer: _Optional[_Union[ExpressionValue, _Mapping]] = ..., storage_class: _Optional[_Union[_common_pb2.StorageClass, str]] = ..., is_constexpr: _Optional[bool] = ...) -> None: ...

class ExprInfo(_message.Message):
    __slots__ = ("type", "value_category", "object_kind", "is_type_dependent", "is_value_dependent", "is_instantiation_dependent", "contains_unexpanded_parameter_pack", "contains_errors")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    VALUE_CATEGORY_FIELD_NUMBER: _ClassVar[int]
    OBJECT_KIND_FIELD_NUMBER: _ClassVar[int]
    IS_TYPE_DEPENDENT_FIELD_NUMBER: _ClassVar[int]
    IS_VALUE_DEPENDENT_FIELD_NUMBER: _ClassVar[int]
    IS_INSTANTIATION_DEPENDENT_FIELD_NUMBER: _ClassVar[int]
    CONTAINS_UNEXPANDED_PARAMETER_PACK_FIELD_NUMBER: _ClassVar[int]
    CONTAINS_ERRORS_FIELD_NUMBER: _ClassVar[int]
    type: QualType
    value_category: _common_pb2.ValueCategory
    object_kind: _common_pb2.ObjectKind
    is_type_dependent: bool
    is_value_dependent: bool
    is_instantiation_dependent: bool
    contains_unexpanded_parameter_pack: bool
    contains_errors: bool
    def __init__(self, type: _Optional[_Union[QualType, _Mapping]] = ..., value_category: _Optional[_Union[_common_pb2.ValueCategory, str]] = ..., object_kind: _Optional[_Union[_common_pb2.ObjectKind, str]] = ..., is_type_dependent: _Optional[bool] = ..., is_value_dependent: _Optional[bool] = ..., is_instantiation_dependent: _Optional[bool] = ..., contains_unexpanded_parameter_pack: _Optional[bool] = ..., contains_errors: _Optional[bool] = ...) -> None: ...

class CallExprInfo(_message.Message):
    __slots__ = ("expression", "callee_expression", "direct_callee", "arguments")
    EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    CALLEE_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    DIRECT_CALLEE_FIELD_NUMBER: _ClassVar[int]
    ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    expression: ExprInfo
    callee_expression: ExpressionValue
    direct_callee: DeclarationSymbol
    arguments: _containers.RepeatedCompositeFieldContainer[ExpressionValue]
    def __init__(self, expression: _Optional[_Union[ExprInfo, _Mapping]] = ..., callee_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., direct_callee: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., arguments: _Optional[_Iterable[_Union[ExpressionValue, _Mapping]]] = ...) -> None: ...

class CastExprInfo(_message.Message):
    __slots__ = ("expression", "operand", "kind", "base_path")
    EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    OPERAND_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    BASE_PATH_FIELD_NUMBER: _ClassVar[int]
    expression: ExprInfo
    operand: ExpressionValue
    kind: _operators_pb2.CastKind
    base_path: _containers.RepeatedCompositeFieldContainer[CXXBaseSpecifier]
    def __init__(self, expression: _Optional[_Union[ExprInfo, _Mapping]] = ..., operand: _Optional[_Union[ExpressionValue, _Mapping]] = ..., kind: _Optional[_Union[_operators_pb2.CastKind, str]] = ..., base_path: _Optional[_Iterable[_Union[CXXBaseSpecifier, _Mapping]]] = ...) -> None: ...

class CXXConstructExprInfo(_message.Message):
    __slots__ = ("expression", "constructor", "arguments", "construction_kind", "is_elidable", "is_list_initialization", "is_std_initializer_list_initialization", "requires_zero_initialization", "had_multiple_candidates")
    EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    CONSTRUCTOR_FIELD_NUMBER: _ClassVar[int]
    ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    CONSTRUCTION_KIND_FIELD_NUMBER: _ClassVar[int]
    IS_ELIDABLE_FIELD_NUMBER: _ClassVar[int]
    IS_LIST_INITIALIZATION_FIELD_NUMBER: _ClassVar[int]
    IS_STD_INITIALIZER_LIST_INITIALIZATION_FIELD_NUMBER: _ClassVar[int]
    REQUIRES_ZERO_INITIALIZATION_FIELD_NUMBER: _ClassVar[int]
    HAD_MULTIPLE_CANDIDATES_FIELD_NUMBER: _ClassVar[int]
    expression: ExprInfo
    constructor: DeclarationSymbol
    arguments: _containers.RepeatedCompositeFieldContainer[ExpressionValue]
    construction_kind: _common_pb2.ConstructionKind
    is_elidable: bool
    is_list_initialization: bool
    is_std_initializer_list_initialization: bool
    requires_zero_initialization: bool
    had_multiple_candidates: bool
    def __init__(self, expression: _Optional[_Union[ExprInfo, _Mapping]] = ..., constructor: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., arguments: _Optional[_Iterable[_Union[ExpressionValue, _Mapping]]] = ..., construction_kind: _Optional[_Union[_common_pb2.ConstructionKind, str]] = ..., is_elidable: _Optional[bool] = ..., is_list_initialization: _Optional[bool] = ..., is_std_initializer_list_initialization: _Optional[bool] = ..., requires_zero_initialization: _Optional[bool] = ..., had_multiple_candidates: _Optional[bool] = ...) -> None: ...

class TypeInfo(_message.Message):
    __slots__ = ("canonical_spelling", "is_dependent", "is_instantiation_dependent", "contains_unexpanded_parameter_pack", "spelling")
    CANONICAL_SPELLING_FIELD_NUMBER: _ClassVar[int]
    IS_DEPENDENT_FIELD_NUMBER: _ClassVar[int]
    IS_INSTANTIATION_DEPENDENT_FIELD_NUMBER: _ClassVar[int]
    CONTAINS_UNEXPANDED_PARAMETER_PACK_FIELD_NUMBER: _ClassVar[int]
    SPELLING_FIELD_NUMBER: _ClassVar[int]
    canonical_spelling: str
    is_dependent: bool
    is_instantiation_dependent: bool
    contains_unexpanded_parameter_pack: bool
    spelling: str
    def __init__(self, canonical_spelling: _Optional[str] = ..., is_dependent: _Optional[bool] = ..., is_instantiation_dependent: _Optional[bool] = ..., contains_unexpanded_parameter_pack: _Optional[bool] = ..., spelling: _Optional[str] = ...) -> None: ...

class BlockCaptureInfo(_message.Message):
    __slots__ = ("variable", "is_by_ref", "is_nested", "copy_expression")
    VARIABLE_FIELD_NUMBER: _ClassVar[int]
    IS_BY_REF_FIELD_NUMBER: _ClassVar[int]
    IS_NESTED_FIELD_NUMBER: _ClassVar[int]
    COPY_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    variable: DeclarationSymbol
    is_by_ref: bool
    is_nested: bool
    copy_expression: ExpressionValue
    def __init__(self, variable: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., is_by_ref: _Optional[bool] = ..., is_nested: _Optional[bool] = ..., copy_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class Designator(_message.Message):
    __slots__ = ("array_range_end", "field_declaration", "array_index", "array_range_start")
    ARRAY_RANGE_END_FIELD_NUMBER: _ClassVar[int]
    FIELD_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    ARRAY_INDEX_FIELD_NUMBER: _ClassVar[int]
    ARRAY_RANGE_START_FIELD_NUMBER: _ClassVar[int]
    array_range_end: ExpressionValue
    field_declaration: DeclarationSymbol
    array_index: ExpressionValue
    array_range_start: ExpressionValue
    def __init__(self, array_range_end: _Optional[_Union[ExpressionValue, _Mapping]] = ..., field_declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., array_index: _Optional[_Union[ExpressionValue, _Mapping]] = ..., array_range_start: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class GenericAssociation(_message.Message):
    __slots__ = ("type", "expression", "is_default", "is_selected")
    TYPE_FIELD_NUMBER: _ClassVar[int]
    EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    IS_DEFAULT_FIELD_NUMBER: _ClassVar[int]
    IS_SELECTED_FIELD_NUMBER: _ClassVar[int]
    type: QualType
    expression: ExpressionValue
    is_default: bool
    is_selected: bool
    def __init__(self, type: _Optional[_Union[QualType, _Mapping]] = ..., expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., is_default: _Optional[bool] = ..., is_selected: _Optional[bool] = ...) -> None: ...

class OffsetOfComponent(_message.Message):
    __slots__ = ("field", "array_index", "identifier", "base", "identifier_name", "index_expression")
    FIELD_FIELD_NUMBER: _ClassVar[int]
    ARRAY_INDEX_FIELD_NUMBER: _ClassVar[int]
    IDENTIFIER_FIELD_NUMBER: _ClassVar[int]
    BASE_FIELD_NUMBER: _ClassVar[int]
    IDENTIFIER_NAME_FIELD_NUMBER: _ClassVar[int]
    INDEX_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    field: DeclarationSymbol
    array_index: int
    identifier: DeclarationSymbol
    base: CXXBaseSpecifier
    identifier_name: str
    index_expression: ExpressionValue
    def __init__(self, field: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., array_index: _Optional[int] = ..., identifier: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., base: _Optional[_Union[CXXBaseSpecifier, _Mapping]] = ..., identifier_name: _Optional[str] = ..., index_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class EmbedParameter(_message.Message):
    __slots__ = ("name", "value")
    NAME_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    name: str
    value: int
    def __init__(self, name: _Optional[str] = ..., value: _Optional[int] = ...) -> None: ...

class AsmOperand(_message.Message):
    __slots__ = ("symbolic_name", "constraint", "expression")
    SYMBOLIC_NAME_FIELD_NUMBER: _ClassVar[int]
    CONSTRAINT_FIELD_NUMBER: _ClassVar[int]
    EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    symbolic_name: str
    constraint: str
    expression: ExpressionValue
    def __init__(self, symbolic_name: _Optional[str] = ..., constraint: _Optional[str] = ..., expression: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class FunctionExtInfo(_message.Message):
    __slots__ = ("calling_convention", "target_convention_name", "no_return", "produces_result", "regparm", "no_caller_saved_registers", "no_cf_check", "cmse_nonsecure_call")
    CALLING_CONVENTION_FIELD_NUMBER: _ClassVar[int]
    TARGET_CONVENTION_NAME_FIELD_NUMBER: _ClassVar[int]
    NO_RETURN_FIELD_NUMBER: _ClassVar[int]
    PRODUCES_RESULT_FIELD_NUMBER: _ClassVar[int]
    REGPARM_FIELD_NUMBER: _ClassVar[int]
    NO_CALLER_SAVED_REGISTERS_FIELD_NUMBER: _ClassVar[int]
    NO_CF_CHECK_FIELD_NUMBER: _ClassVar[int]
    CMSE_NONSECURE_CALL_FIELD_NUMBER: _ClassVar[int]
    calling_convention: FunctionCallingConvention
    target_convention_name: str
    no_return: bool
    produces_result: bool
    regparm: int
    no_caller_saved_registers: bool
    no_cf_check: bool
    cmse_nonsecure_call: bool
    def __init__(self, calling_convention: _Optional[_Union[FunctionCallingConvention, str]] = ..., target_convention_name: _Optional[str] = ..., no_return: _Optional[bool] = ..., produces_result: _Optional[bool] = ..., regparm: _Optional[int] = ..., no_caller_saved_registers: _Optional[bool] = ..., no_cf_check: _Optional[bool] = ..., cmse_nonsecure_call: _Optional[bool] = ...) -> None: ...

class FunctionProtoExtInfo(_message.Message):
    __slots__ = ("exception_specification", "exception_types", "ref_qualifier", "noexcept_expression", "exception_specification_declaration", "exception_specification_template", "type_qualifiers", "is_cfi_unchecked_callee")
    EXCEPTION_SPECIFICATION_FIELD_NUMBER: _ClassVar[int]
    EXCEPTION_TYPES_FIELD_NUMBER: _ClassVar[int]
    REF_QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    NOEXCEPT_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    EXCEPTION_SPECIFICATION_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    EXCEPTION_SPECIFICATION_TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    TYPE_QUALIFIERS_FIELD_NUMBER: _ClassVar[int]
    IS_CFI_UNCHECKED_CALLEE_FIELD_NUMBER: _ClassVar[int]
    exception_specification: ExceptionSpecification
    exception_types: _containers.RepeatedCompositeFieldContainer[QualType]
    ref_qualifier: _common_pb2.RefQualifier
    noexcept_expression: ExpressionValue
    exception_specification_declaration: DeclarationSymbol
    exception_specification_template: DeclarationSymbol
    type_qualifiers: _common_pb2.Qualifiers
    is_cfi_unchecked_callee: bool
    def __init__(self, exception_specification: _Optional[_Union[ExceptionSpecification, str]] = ..., exception_types: _Optional[_Iterable[_Union[QualType, _Mapping]]] = ..., ref_qualifier: _Optional[_Union[_common_pb2.RefQualifier, str]] = ..., noexcept_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., exception_specification_declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., exception_specification_template: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., type_qualifiers: _Optional[_Union[_common_pb2.Qualifiers, _Mapping]] = ..., is_cfi_unchecked_callee: _Optional[bool] = ...) -> None: ...

class DeclarationValue(_message.Message):
    __slots__ = ("is_complete", "access_spec_decl", "binding_decl", "block_decl", "builtin_template_decl", "cxx_constructor_decl", "cxx_conversion_decl", "cxx_deduction_guide_decl", "cxx_destructor_decl", "cxx_method_decl", "cxx_record_decl", "class_template_decl", "class_template_partial_specialization_decl", "class_template_specialization_decl", "concept_decl", "constructor_using_shadow_decl", "decomposition_decl", "empty_decl", "enum_constant_decl", "enum_decl", "export_decl", "extern_c_context_decl", "field_decl", "file_scope_asm_decl", "friend_decl", "friend_template_decl", "function_decl", "function_template_decl", "implicit_concept_specialization_decl", "implicit_param_decl", "import_decl", "indirect_field_decl", "label_decl", "lifetime_extended_temporary_decl", "linkage_spec_decl", "ms_guid_decl", "ms_property_decl", "namespace_alias_decl", "namespace_decl", "non_type_template_parm_decl", "parm_var_decl", "pragma_comment_decl", "pragma_detect_mismatch_decl", "record_decl", "requires_expr_body_decl", "static_assert_decl", "template_param_object_decl", "template_template_parm_decl", "template_type_parm_decl", "top_level_stmt_decl", "translation_unit_decl", "type_alias_decl", "type_alias_template_decl", "typedef_decl", "unnamed_global_constant_decl", "unresolved_using_if_exists_decl", "unresolved_using_typename_decl", "unresolved_using_value_decl", "using_decl", "using_directive_decl", "using_enum_decl", "using_pack_decl", "using_shadow_decl", "var_decl", "var_template_decl", "var_template_partial_specialization_decl", "var_template_specialization_decl")
    IS_COMPLETE_FIELD_NUMBER: _ClassVar[int]
    ACCESS_SPEC_DECL_FIELD_NUMBER: _ClassVar[int]
    BINDING_DECL_FIELD_NUMBER: _ClassVar[int]
    BLOCK_DECL_FIELD_NUMBER: _ClassVar[int]
    BUILTIN_TEMPLATE_DECL_FIELD_NUMBER: _ClassVar[int]
    CXX_CONSTRUCTOR_DECL_FIELD_NUMBER: _ClassVar[int]
    CXX_CONVERSION_DECL_FIELD_NUMBER: _ClassVar[int]
    CXX_DEDUCTION_GUIDE_DECL_FIELD_NUMBER: _ClassVar[int]
    CXX_DESTRUCTOR_DECL_FIELD_NUMBER: _ClassVar[int]
    CXX_METHOD_DECL_FIELD_NUMBER: _ClassVar[int]
    CXX_RECORD_DECL_FIELD_NUMBER: _ClassVar[int]
    CLASS_TEMPLATE_DECL_FIELD_NUMBER: _ClassVar[int]
    CLASS_TEMPLATE_PARTIAL_SPECIALIZATION_DECL_FIELD_NUMBER: _ClassVar[int]
    CLASS_TEMPLATE_SPECIALIZATION_DECL_FIELD_NUMBER: _ClassVar[int]
    CONCEPT_DECL_FIELD_NUMBER: _ClassVar[int]
    CONSTRUCTOR_USING_SHADOW_DECL_FIELD_NUMBER: _ClassVar[int]
    DECOMPOSITION_DECL_FIELD_NUMBER: _ClassVar[int]
    EMPTY_DECL_FIELD_NUMBER: _ClassVar[int]
    ENUM_CONSTANT_DECL_FIELD_NUMBER: _ClassVar[int]
    ENUM_DECL_FIELD_NUMBER: _ClassVar[int]
    EXPORT_DECL_FIELD_NUMBER: _ClassVar[int]
    EXTERN_C_CONTEXT_DECL_FIELD_NUMBER: _ClassVar[int]
    FIELD_DECL_FIELD_NUMBER: _ClassVar[int]
    FILE_SCOPE_ASM_DECL_FIELD_NUMBER: _ClassVar[int]
    FRIEND_DECL_FIELD_NUMBER: _ClassVar[int]
    FRIEND_TEMPLATE_DECL_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_DECL_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_TEMPLATE_DECL_FIELD_NUMBER: _ClassVar[int]
    IMPLICIT_CONCEPT_SPECIALIZATION_DECL_FIELD_NUMBER: _ClassVar[int]
    IMPLICIT_PARAM_DECL_FIELD_NUMBER: _ClassVar[int]
    IMPORT_DECL_FIELD_NUMBER: _ClassVar[int]
    INDIRECT_FIELD_DECL_FIELD_NUMBER: _ClassVar[int]
    LABEL_DECL_FIELD_NUMBER: _ClassVar[int]
    LIFETIME_EXTENDED_TEMPORARY_DECL_FIELD_NUMBER: _ClassVar[int]
    LINKAGE_SPEC_DECL_FIELD_NUMBER: _ClassVar[int]
    MS_GUID_DECL_FIELD_NUMBER: _ClassVar[int]
    MS_PROPERTY_DECL_FIELD_NUMBER: _ClassVar[int]
    NAMESPACE_ALIAS_DECL_FIELD_NUMBER: _ClassVar[int]
    NAMESPACE_DECL_FIELD_NUMBER: _ClassVar[int]
    NON_TYPE_TEMPLATE_PARM_DECL_FIELD_NUMBER: _ClassVar[int]
    PARM_VAR_DECL_FIELD_NUMBER: _ClassVar[int]
    PRAGMA_COMMENT_DECL_FIELD_NUMBER: _ClassVar[int]
    PRAGMA_DETECT_MISMATCH_DECL_FIELD_NUMBER: _ClassVar[int]
    RECORD_DECL_FIELD_NUMBER: _ClassVar[int]
    REQUIRES_EXPR_BODY_DECL_FIELD_NUMBER: _ClassVar[int]
    STATIC_ASSERT_DECL_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_PARAM_OBJECT_DECL_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_TEMPLATE_PARM_DECL_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_TYPE_PARM_DECL_FIELD_NUMBER: _ClassVar[int]
    TOP_LEVEL_STMT_DECL_FIELD_NUMBER: _ClassVar[int]
    TRANSLATION_UNIT_DECL_FIELD_NUMBER: _ClassVar[int]
    TYPE_ALIAS_DECL_FIELD_NUMBER: _ClassVar[int]
    TYPE_ALIAS_TEMPLATE_DECL_FIELD_NUMBER: _ClassVar[int]
    TYPEDEF_DECL_FIELD_NUMBER: _ClassVar[int]
    UNNAMED_GLOBAL_CONSTANT_DECL_FIELD_NUMBER: _ClassVar[int]
    UNRESOLVED_USING_IF_EXISTS_DECL_FIELD_NUMBER: _ClassVar[int]
    UNRESOLVED_USING_TYPENAME_DECL_FIELD_NUMBER: _ClassVar[int]
    UNRESOLVED_USING_VALUE_DECL_FIELD_NUMBER: _ClassVar[int]
    USING_DECL_FIELD_NUMBER: _ClassVar[int]
    USING_DIRECTIVE_DECL_FIELD_NUMBER: _ClassVar[int]
    USING_ENUM_DECL_FIELD_NUMBER: _ClassVar[int]
    USING_PACK_DECL_FIELD_NUMBER: _ClassVar[int]
    USING_SHADOW_DECL_FIELD_NUMBER: _ClassVar[int]
    VAR_DECL_FIELD_NUMBER: _ClassVar[int]
    VAR_TEMPLATE_DECL_FIELD_NUMBER: _ClassVar[int]
    VAR_TEMPLATE_PARTIAL_SPECIALIZATION_DECL_FIELD_NUMBER: _ClassVar[int]
    VAR_TEMPLATE_SPECIALIZATION_DECL_FIELD_NUMBER: _ClassVar[int]
    is_complete: bool
    access_spec_decl: AccessSpecDecl
    binding_decl: BindingDecl
    block_decl: BlockDecl
    builtin_template_decl: BuiltinTemplateDecl
    cxx_constructor_decl: CXXConstructorDecl
    cxx_conversion_decl: CXXConversionDecl
    cxx_deduction_guide_decl: CXXDeductionGuideDecl
    cxx_destructor_decl: CXXDestructorDecl
    cxx_method_decl: CXXMethodDecl
    cxx_record_decl: CXXRecordDecl
    class_template_decl: ClassTemplateDecl
    class_template_partial_specialization_decl: ClassTemplatePartialSpecializationDecl
    class_template_specialization_decl: ClassTemplateSpecializationDecl
    concept_decl: ConceptDecl
    constructor_using_shadow_decl: ConstructorUsingShadowDecl
    decomposition_decl: DecompositionDecl
    empty_decl: EmptyDecl
    enum_constant_decl: EnumConstantDecl
    enum_decl: EnumDecl
    export_decl: ExportDecl
    extern_c_context_decl: ExternCContextDecl
    field_decl: FieldDecl
    file_scope_asm_decl: FileScopeAsmDecl
    friend_decl: FriendDecl
    friend_template_decl: FriendTemplateDecl
    function_decl: FunctionDecl
    function_template_decl: FunctionTemplateDecl
    implicit_concept_specialization_decl: ImplicitConceptSpecializationDecl
    implicit_param_decl: ImplicitParamDecl
    import_decl: ImportDecl
    indirect_field_decl: IndirectFieldDecl
    label_decl: LabelDecl
    lifetime_extended_temporary_decl: LifetimeExtendedTemporaryDecl
    linkage_spec_decl: LinkageSpecDecl
    ms_guid_decl: MSGuidDecl
    ms_property_decl: MSPropertyDecl
    namespace_alias_decl: NamespaceAliasDecl
    namespace_decl: NamespaceDecl
    non_type_template_parm_decl: NonTypeTemplateParmDecl
    parm_var_decl: ParmVarDecl
    pragma_comment_decl: PragmaCommentDecl
    pragma_detect_mismatch_decl: PragmaDetectMismatchDecl
    record_decl: RecordDecl
    requires_expr_body_decl: RequiresExprBodyDecl
    static_assert_decl: StaticAssertDecl
    template_param_object_decl: TemplateParamObjectDecl
    template_template_parm_decl: TemplateTemplateParmDecl
    template_type_parm_decl: TemplateTypeParmDecl
    top_level_stmt_decl: TopLevelStmtDecl
    translation_unit_decl: TranslationUnitDecl
    type_alias_decl: TypeAliasDecl
    type_alias_template_decl: TypeAliasTemplateDecl
    typedef_decl: TypedefDecl
    unnamed_global_constant_decl: UnnamedGlobalConstantDecl
    unresolved_using_if_exists_decl: UnresolvedUsingIfExistsDecl
    unresolved_using_typename_decl: UnresolvedUsingTypenameDecl
    unresolved_using_value_decl: UnresolvedUsingValueDecl
    using_decl: UsingDecl
    using_directive_decl: UsingDirectiveDecl
    using_enum_decl: UsingEnumDecl
    using_pack_decl: UsingPackDecl
    using_shadow_decl: UsingShadowDecl
    var_decl: VarDecl
    var_template_decl: VarTemplateDecl
    var_template_partial_specialization_decl: VarTemplatePartialSpecializationDecl
    var_template_specialization_decl: VarTemplateSpecializationDecl
    def __init__(self, is_complete: _Optional[bool] = ..., access_spec_decl: _Optional[_Union[AccessSpecDecl, _Mapping]] = ..., binding_decl: _Optional[_Union[BindingDecl, _Mapping]] = ..., block_decl: _Optional[_Union[BlockDecl, _Mapping]] = ..., builtin_template_decl: _Optional[_Union[BuiltinTemplateDecl, _Mapping]] = ..., cxx_constructor_decl: _Optional[_Union[CXXConstructorDecl, _Mapping]] = ..., cxx_conversion_decl: _Optional[_Union[CXXConversionDecl, _Mapping]] = ..., cxx_deduction_guide_decl: _Optional[_Union[CXXDeductionGuideDecl, _Mapping]] = ..., cxx_destructor_decl: _Optional[_Union[CXXDestructorDecl, _Mapping]] = ..., cxx_method_decl: _Optional[_Union[CXXMethodDecl, _Mapping]] = ..., cxx_record_decl: _Optional[_Union[CXXRecordDecl, _Mapping]] = ..., class_template_decl: _Optional[_Union[ClassTemplateDecl, _Mapping]] = ..., class_template_partial_specialization_decl: _Optional[_Union[ClassTemplatePartialSpecializationDecl, _Mapping]] = ..., class_template_specialization_decl: _Optional[_Union[ClassTemplateSpecializationDecl, _Mapping]] = ..., concept_decl: _Optional[_Union[ConceptDecl, _Mapping]] = ..., constructor_using_shadow_decl: _Optional[_Union[ConstructorUsingShadowDecl, _Mapping]] = ..., decomposition_decl: _Optional[_Union[DecompositionDecl, _Mapping]] = ..., empty_decl: _Optional[_Union[EmptyDecl, _Mapping]] = ..., enum_constant_decl: _Optional[_Union[EnumConstantDecl, _Mapping]] = ..., enum_decl: _Optional[_Union[EnumDecl, _Mapping]] = ..., export_decl: _Optional[_Union[ExportDecl, _Mapping]] = ..., extern_c_context_decl: _Optional[_Union[ExternCContextDecl, _Mapping]] = ..., field_decl: _Optional[_Union[FieldDecl, _Mapping]] = ..., file_scope_asm_decl: _Optional[_Union[FileScopeAsmDecl, _Mapping]] = ..., friend_decl: _Optional[_Union[FriendDecl, _Mapping]] = ..., friend_template_decl: _Optional[_Union[FriendTemplateDecl, _Mapping]] = ..., function_decl: _Optional[_Union[FunctionDecl, _Mapping]] = ..., function_template_decl: _Optional[_Union[FunctionTemplateDecl, _Mapping]] = ..., implicit_concept_specialization_decl: _Optional[_Union[ImplicitConceptSpecializationDecl, _Mapping]] = ..., implicit_param_decl: _Optional[_Union[ImplicitParamDecl, _Mapping]] = ..., import_decl: _Optional[_Union[ImportDecl, _Mapping]] = ..., indirect_field_decl: _Optional[_Union[IndirectFieldDecl, _Mapping]] = ..., label_decl: _Optional[_Union[LabelDecl, _Mapping]] = ..., lifetime_extended_temporary_decl: _Optional[_Union[LifetimeExtendedTemporaryDecl, _Mapping]] = ..., linkage_spec_decl: _Optional[_Union[LinkageSpecDecl, _Mapping]] = ..., ms_guid_decl: _Optional[_Union[MSGuidDecl, _Mapping]] = ..., ms_property_decl: _Optional[_Union[MSPropertyDecl, _Mapping]] = ..., namespace_alias_decl: _Optional[_Union[NamespaceAliasDecl, _Mapping]] = ..., namespace_decl: _Optional[_Union[NamespaceDecl, _Mapping]] = ..., non_type_template_parm_decl: _Optional[_Union[NonTypeTemplateParmDecl, _Mapping]] = ..., parm_var_decl: _Optional[_Union[ParmVarDecl, _Mapping]] = ..., pragma_comment_decl: _Optional[_Union[PragmaCommentDecl, _Mapping]] = ..., pragma_detect_mismatch_decl: _Optional[_Union[PragmaDetectMismatchDecl, _Mapping]] = ..., record_decl: _Optional[_Union[RecordDecl, _Mapping]] = ..., requires_expr_body_decl: _Optional[_Union[RequiresExprBodyDecl, _Mapping]] = ..., static_assert_decl: _Optional[_Union[StaticAssertDecl, _Mapping]] = ..., template_param_object_decl: _Optional[_Union[TemplateParamObjectDecl, _Mapping]] = ..., template_template_parm_decl: _Optional[_Union[TemplateTemplateParmDecl, _Mapping]] = ..., template_type_parm_decl: _Optional[_Union[TemplateTypeParmDecl, _Mapping]] = ..., top_level_stmt_decl: _Optional[_Union[TopLevelStmtDecl, _Mapping]] = ..., translation_unit_decl: _Optional[_Union[TranslationUnitDecl, _Mapping]] = ..., type_alias_decl: _Optional[_Union[TypeAliasDecl, _Mapping]] = ..., type_alias_template_decl: _Optional[_Union[TypeAliasTemplateDecl, _Mapping]] = ..., typedef_decl: _Optional[_Union[TypedefDecl, _Mapping]] = ..., unnamed_global_constant_decl: _Optional[_Union[UnnamedGlobalConstantDecl, _Mapping]] = ..., unresolved_using_if_exists_decl: _Optional[_Union[UnresolvedUsingIfExistsDecl, _Mapping]] = ..., unresolved_using_typename_decl: _Optional[_Union[UnresolvedUsingTypenameDecl, _Mapping]] = ..., unresolved_using_value_decl: _Optional[_Union[UnresolvedUsingValueDecl, _Mapping]] = ..., using_decl: _Optional[_Union[UsingDecl, _Mapping]] = ..., using_directive_decl: _Optional[_Union[UsingDirectiveDecl, _Mapping]] = ..., using_enum_decl: _Optional[_Union[UsingEnumDecl, _Mapping]] = ..., using_pack_decl: _Optional[_Union[UsingPackDecl, _Mapping]] = ..., using_shadow_decl: _Optional[_Union[UsingShadowDecl, _Mapping]] = ..., var_decl: _Optional[_Union[VarDecl, _Mapping]] = ..., var_template_decl: _Optional[_Union[VarTemplateDecl, _Mapping]] = ..., var_template_partial_specialization_decl: _Optional[_Union[VarTemplatePartialSpecializationDecl, _Mapping]] = ..., var_template_specialization_decl: _Optional[_Union[VarTemplateSpecializationDecl, _Mapping]] = ...) -> None: ...

class ExpressionValue(_message.Message):
    __slots__ = ("is_complete", "addr_label_expr", "array_init_index_expr", "array_init_loop_expr", "array_subscript_expr", "array_type_trait_expr", "atomic_expr", "binary_conditional_operator", "binary_operator", "block_expr", "builtin_bit_cast_expr", "c_style_cast_expr", "cxx_addrspace_cast_expr", "cxx_bind_temporary_expr", "cxx_bool_literal_expr", "cxx_const_cast_expr", "cxx_construct_expr", "cxx_default_arg_expr", "cxx_default_init_expr", "cxx_delete_expr", "cxx_dependent_scope_member_expr", "cxx_dynamic_cast_expr", "cxx_fold_expr", "cxx_functional_cast_expr", "cxx_inherited_ctor_init_expr", "cxx_member_call_expr", "cxx_new_expr", "cxx_noexcept_expr", "cxx_null_ptr_literal_expr", "cxx_operator_call_expr", "cxx_paren_list_init_expr", "cxx_pseudo_destructor_expr", "cxx_reinterpret_cast_expr", "cxx_rewritten_binary_operator", "cxx_scalar_value_init_expr", "cxx_static_cast_expr", "cxx_std_initializer_list_expr", "cxx_temporary_object_expr", "cxx_this_expr", "cxx_throw_expr", "cxx_typeid_expr", "cxx_unresolved_construct_expr", "cxx_uuidof_expr", "call_expr", "character_literal", "choose_expr", "coawait_expr", "compound_assign_operator", "compound_literal_expr", "concept_specialization_expr", "conditional_operator", "constant_expr", "convert_vector_expr", "coyield_expr", "decl_ref_expr", "dependent_coawait_expr", "dependent_scope_decl_ref_expr", "designated_init_expr", "designated_init_update_expr", "embed_expr", "expr_with_cleanups", "expression_trait_expr", "ext_vector_element_expr", "fixed_point_literal", "floating_literal", "function_parm_pack_expr", "gnu_null_expr", "generic_selection_expr", "imaginary_literal", "implicit_cast_expr", "implicit_value_init_expr", "init_list_expr", "integer_literal", "lambda_expr", "ms_property_ref_expr", "ms_property_subscript_expr", "materialize_temporary_expr", "matrix_single_subscript_expr", "matrix_subscript_expr", "member_expr", "no_init_expr", "offset_of_expr", "opaque_value_expr", "pack_expansion_expr", "pack_indexing_expr", "paren_expr", "paren_list_expr", "predefined_expr", "pseudo_object_expr", "recovery_expr", "requires_expr", "shuffle_vector_expr", "size_of_pack_expr", "source_loc_expr", "stmt_expr", "string_literal", "subst_non_type_template_parm_expr", "subst_non_type_template_parm_pack_expr", "type_trait_expr", "unary_expr_or_type_trait_expr", "unary_operator", "unresolved_lookup_expr", "unresolved_member_expr", "user_defined_literal", "va_arg_expr")
    IS_COMPLETE_FIELD_NUMBER: _ClassVar[int]
    ADDR_LABEL_EXPR_FIELD_NUMBER: _ClassVar[int]
    ARRAY_INIT_INDEX_EXPR_FIELD_NUMBER: _ClassVar[int]
    ARRAY_INIT_LOOP_EXPR_FIELD_NUMBER: _ClassVar[int]
    ARRAY_SUBSCRIPT_EXPR_FIELD_NUMBER: _ClassVar[int]
    ARRAY_TYPE_TRAIT_EXPR_FIELD_NUMBER: _ClassVar[int]
    ATOMIC_EXPR_FIELD_NUMBER: _ClassVar[int]
    BINARY_CONDITIONAL_OPERATOR_FIELD_NUMBER: _ClassVar[int]
    BINARY_OPERATOR_FIELD_NUMBER: _ClassVar[int]
    BLOCK_EXPR_FIELD_NUMBER: _ClassVar[int]
    BUILTIN_BIT_CAST_EXPR_FIELD_NUMBER: _ClassVar[int]
    C_STYLE_CAST_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_ADDRSPACE_CAST_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_BIND_TEMPORARY_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_BOOL_LITERAL_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_CONST_CAST_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_CONSTRUCT_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_DEFAULT_ARG_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_DEFAULT_INIT_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_DELETE_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_DEPENDENT_SCOPE_MEMBER_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_DYNAMIC_CAST_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_FOLD_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_FUNCTIONAL_CAST_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_INHERITED_CTOR_INIT_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_MEMBER_CALL_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_NEW_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_NOEXCEPT_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_NULL_PTR_LITERAL_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_OPERATOR_CALL_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_PAREN_LIST_INIT_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_PSEUDO_DESTRUCTOR_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_REINTERPRET_CAST_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_REWRITTEN_BINARY_OPERATOR_FIELD_NUMBER: _ClassVar[int]
    CXX_SCALAR_VALUE_INIT_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_STATIC_CAST_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_STD_INITIALIZER_LIST_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_TEMPORARY_OBJECT_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_THIS_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_THROW_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_TYPEID_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_UNRESOLVED_CONSTRUCT_EXPR_FIELD_NUMBER: _ClassVar[int]
    CXX_UUIDOF_EXPR_FIELD_NUMBER: _ClassVar[int]
    CALL_EXPR_FIELD_NUMBER: _ClassVar[int]
    CHARACTER_LITERAL_FIELD_NUMBER: _ClassVar[int]
    CHOOSE_EXPR_FIELD_NUMBER: _ClassVar[int]
    COAWAIT_EXPR_FIELD_NUMBER: _ClassVar[int]
    COMPOUND_ASSIGN_OPERATOR_FIELD_NUMBER: _ClassVar[int]
    COMPOUND_LITERAL_EXPR_FIELD_NUMBER: _ClassVar[int]
    CONCEPT_SPECIALIZATION_EXPR_FIELD_NUMBER: _ClassVar[int]
    CONDITIONAL_OPERATOR_FIELD_NUMBER: _ClassVar[int]
    CONSTANT_EXPR_FIELD_NUMBER: _ClassVar[int]
    CONVERT_VECTOR_EXPR_FIELD_NUMBER: _ClassVar[int]
    COYIELD_EXPR_FIELD_NUMBER: _ClassVar[int]
    DECL_REF_EXPR_FIELD_NUMBER: _ClassVar[int]
    DEPENDENT_COAWAIT_EXPR_FIELD_NUMBER: _ClassVar[int]
    DEPENDENT_SCOPE_DECL_REF_EXPR_FIELD_NUMBER: _ClassVar[int]
    DESIGNATED_INIT_EXPR_FIELD_NUMBER: _ClassVar[int]
    DESIGNATED_INIT_UPDATE_EXPR_FIELD_NUMBER: _ClassVar[int]
    EMBED_EXPR_FIELD_NUMBER: _ClassVar[int]
    EXPR_WITH_CLEANUPS_FIELD_NUMBER: _ClassVar[int]
    EXPRESSION_TRAIT_EXPR_FIELD_NUMBER: _ClassVar[int]
    EXT_VECTOR_ELEMENT_EXPR_FIELD_NUMBER: _ClassVar[int]
    FIXED_POINT_LITERAL_FIELD_NUMBER: _ClassVar[int]
    FLOATING_LITERAL_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_PARM_PACK_EXPR_FIELD_NUMBER: _ClassVar[int]
    GNU_NULL_EXPR_FIELD_NUMBER: _ClassVar[int]
    GENERIC_SELECTION_EXPR_FIELD_NUMBER: _ClassVar[int]
    IMAGINARY_LITERAL_FIELD_NUMBER: _ClassVar[int]
    IMPLICIT_CAST_EXPR_FIELD_NUMBER: _ClassVar[int]
    IMPLICIT_VALUE_INIT_EXPR_FIELD_NUMBER: _ClassVar[int]
    INIT_LIST_EXPR_FIELD_NUMBER: _ClassVar[int]
    INTEGER_LITERAL_FIELD_NUMBER: _ClassVar[int]
    LAMBDA_EXPR_FIELD_NUMBER: _ClassVar[int]
    MS_PROPERTY_REF_EXPR_FIELD_NUMBER: _ClassVar[int]
    MS_PROPERTY_SUBSCRIPT_EXPR_FIELD_NUMBER: _ClassVar[int]
    MATERIALIZE_TEMPORARY_EXPR_FIELD_NUMBER: _ClassVar[int]
    MATRIX_SINGLE_SUBSCRIPT_EXPR_FIELD_NUMBER: _ClassVar[int]
    MATRIX_SUBSCRIPT_EXPR_FIELD_NUMBER: _ClassVar[int]
    MEMBER_EXPR_FIELD_NUMBER: _ClassVar[int]
    NO_INIT_EXPR_FIELD_NUMBER: _ClassVar[int]
    OFFSET_OF_EXPR_FIELD_NUMBER: _ClassVar[int]
    OPAQUE_VALUE_EXPR_FIELD_NUMBER: _ClassVar[int]
    PACK_EXPANSION_EXPR_FIELD_NUMBER: _ClassVar[int]
    PACK_INDEXING_EXPR_FIELD_NUMBER: _ClassVar[int]
    PAREN_EXPR_FIELD_NUMBER: _ClassVar[int]
    PAREN_LIST_EXPR_FIELD_NUMBER: _ClassVar[int]
    PREDEFINED_EXPR_FIELD_NUMBER: _ClassVar[int]
    PSEUDO_OBJECT_EXPR_FIELD_NUMBER: _ClassVar[int]
    RECOVERY_EXPR_FIELD_NUMBER: _ClassVar[int]
    REQUIRES_EXPR_FIELD_NUMBER: _ClassVar[int]
    SHUFFLE_VECTOR_EXPR_FIELD_NUMBER: _ClassVar[int]
    SIZE_OF_PACK_EXPR_FIELD_NUMBER: _ClassVar[int]
    SOURCE_LOC_EXPR_FIELD_NUMBER: _ClassVar[int]
    STMT_EXPR_FIELD_NUMBER: _ClassVar[int]
    STRING_LITERAL_FIELD_NUMBER: _ClassVar[int]
    SUBST_NON_TYPE_TEMPLATE_PARM_EXPR_FIELD_NUMBER: _ClassVar[int]
    SUBST_NON_TYPE_TEMPLATE_PARM_PACK_EXPR_FIELD_NUMBER: _ClassVar[int]
    TYPE_TRAIT_EXPR_FIELD_NUMBER: _ClassVar[int]
    UNARY_EXPR_OR_TYPE_TRAIT_EXPR_FIELD_NUMBER: _ClassVar[int]
    UNARY_OPERATOR_FIELD_NUMBER: _ClassVar[int]
    UNRESOLVED_LOOKUP_EXPR_FIELD_NUMBER: _ClassVar[int]
    UNRESOLVED_MEMBER_EXPR_FIELD_NUMBER: _ClassVar[int]
    USER_DEFINED_LITERAL_FIELD_NUMBER: _ClassVar[int]
    VA_ARG_EXPR_FIELD_NUMBER: _ClassVar[int]
    is_complete: bool
    addr_label_expr: AddrLabelExpr
    array_init_index_expr: ArrayInitIndexExpr
    array_init_loop_expr: ArrayInitLoopExpr
    array_subscript_expr: ArraySubscriptExpr
    array_type_trait_expr: ArrayTypeTraitExpr
    atomic_expr: AtomicExpr
    binary_conditional_operator: BinaryConditionalOperator
    binary_operator: BinaryOperator
    block_expr: BlockExpr
    builtin_bit_cast_expr: BuiltinBitCastExpr
    c_style_cast_expr: CStyleCastExpr
    cxx_addrspace_cast_expr: CXXAddrspaceCastExpr
    cxx_bind_temporary_expr: CXXBindTemporaryExpr
    cxx_bool_literal_expr: CXXBoolLiteralExpr
    cxx_const_cast_expr: CXXConstCastExpr
    cxx_construct_expr: CXXConstructExpr
    cxx_default_arg_expr: CXXDefaultArgExpr
    cxx_default_init_expr: CXXDefaultInitExpr
    cxx_delete_expr: CXXDeleteExpr
    cxx_dependent_scope_member_expr: CXXDependentScopeMemberExpr
    cxx_dynamic_cast_expr: CXXDynamicCastExpr
    cxx_fold_expr: CXXFoldExpr
    cxx_functional_cast_expr: CXXFunctionalCastExpr
    cxx_inherited_ctor_init_expr: CXXInheritedCtorInitExpr
    cxx_member_call_expr: CXXMemberCallExpr
    cxx_new_expr: CXXNewExpr
    cxx_noexcept_expr: CXXNoexceptExpr
    cxx_null_ptr_literal_expr: CXXNullPtrLiteralExpr
    cxx_operator_call_expr: CXXOperatorCallExpr
    cxx_paren_list_init_expr: CXXParenListInitExpr
    cxx_pseudo_destructor_expr: CXXPseudoDestructorExpr
    cxx_reinterpret_cast_expr: CXXReinterpretCastExpr
    cxx_rewritten_binary_operator: CXXRewrittenBinaryOperator
    cxx_scalar_value_init_expr: CXXScalarValueInitExpr
    cxx_static_cast_expr: CXXStaticCastExpr
    cxx_std_initializer_list_expr: CXXStdInitializerListExpr
    cxx_temporary_object_expr: CXXTemporaryObjectExpr
    cxx_this_expr: CXXThisExpr
    cxx_throw_expr: CXXThrowExpr
    cxx_typeid_expr: CXXTypeidExpr
    cxx_unresolved_construct_expr: CXXUnresolvedConstructExpr
    cxx_uuidof_expr: CXXUuidofExpr
    call_expr: CallExpr
    character_literal: CharacterLiteral
    choose_expr: ChooseExpr
    coawait_expr: CoawaitExpr
    compound_assign_operator: CompoundAssignOperator
    compound_literal_expr: CompoundLiteralExpr
    concept_specialization_expr: ConceptSpecializationExpr
    conditional_operator: ConditionalOperator
    constant_expr: ConstantExpr
    convert_vector_expr: ConvertVectorExpr
    coyield_expr: CoyieldExpr
    decl_ref_expr: DeclRefExpr
    dependent_coawait_expr: DependentCoawaitExpr
    dependent_scope_decl_ref_expr: DependentScopeDeclRefExpr
    designated_init_expr: DesignatedInitExpr
    designated_init_update_expr: DesignatedInitUpdateExpr
    embed_expr: EmbedExpr
    expr_with_cleanups: ExprWithCleanups
    expression_trait_expr: ExpressionTraitExpr
    ext_vector_element_expr: ExtVectorElementExpr
    fixed_point_literal: FixedPointLiteral
    floating_literal: FloatingLiteral
    function_parm_pack_expr: FunctionParmPackExpr
    gnu_null_expr: GNUNullExpr
    generic_selection_expr: GenericSelectionExpr
    imaginary_literal: ImaginaryLiteral
    implicit_cast_expr: ImplicitCastExpr
    implicit_value_init_expr: ImplicitValueInitExpr
    init_list_expr: InitListExpr
    integer_literal: IntegerLiteral
    lambda_expr: LambdaExpr
    ms_property_ref_expr: MSPropertyRefExpr
    ms_property_subscript_expr: MSPropertySubscriptExpr
    materialize_temporary_expr: MaterializeTemporaryExpr
    matrix_single_subscript_expr: MatrixSingleSubscriptExpr
    matrix_subscript_expr: MatrixSubscriptExpr
    member_expr: MemberExpr
    no_init_expr: NoInitExpr
    offset_of_expr: OffsetOfExpr
    opaque_value_expr: OpaqueValueExpr
    pack_expansion_expr: PackExpansionExpr
    pack_indexing_expr: PackIndexingExpr
    paren_expr: ParenExpr
    paren_list_expr: ParenListExpr
    predefined_expr: PredefinedExpr
    pseudo_object_expr: PseudoObjectExpr
    recovery_expr: RecoveryExpr
    requires_expr: RequiresExpr
    shuffle_vector_expr: ShuffleVectorExpr
    size_of_pack_expr: SizeOfPackExpr
    source_loc_expr: SourceLocExpr
    stmt_expr: StmtExpr
    string_literal: StringLiteral
    subst_non_type_template_parm_expr: SubstNonTypeTemplateParmExpr
    subst_non_type_template_parm_pack_expr: SubstNonTypeTemplateParmPackExpr
    type_trait_expr: TypeTraitExpr
    unary_expr_or_type_trait_expr: UnaryExprOrTypeTraitExpr
    unary_operator: UnaryOperator
    unresolved_lookup_expr: UnresolvedLookupExpr
    unresolved_member_expr: UnresolvedMemberExpr
    user_defined_literal: UserDefinedLiteral
    va_arg_expr: VAArgExpr
    def __init__(self, is_complete: _Optional[bool] = ..., addr_label_expr: _Optional[_Union[AddrLabelExpr, _Mapping]] = ..., array_init_index_expr: _Optional[_Union[ArrayInitIndexExpr, _Mapping]] = ..., array_init_loop_expr: _Optional[_Union[ArrayInitLoopExpr, _Mapping]] = ..., array_subscript_expr: _Optional[_Union[ArraySubscriptExpr, _Mapping]] = ..., array_type_trait_expr: _Optional[_Union[ArrayTypeTraitExpr, _Mapping]] = ..., atomic_expr: _Optional[_Union[AtomicExpr, _Mapping]] = ..., binary_conditional_operator: _Optional[_Union[BinaryConditionalOperator, _Mapping]] = ..., binary_operator: _Optional[_Union[BinaryOperator, _Mapping]] = ..., block_expr: _Optional[_Union[BlockExpr, _Mapping]] = ..., builtin_bit_cast_expr: _Optional[_Union[BuiltinBitCastExpr, _Mapping]] = ..., c_style_cast_expr: _Optional[_Union[CStyleCastExpr, _Mapping]] = ..., cxx_addrspace_cast_expr: _Optional[_Union[CXXAddrspaceCastExpr, _Mapping]] = ..., cxx_bind_temporary_expr: _Optional[_Union[CXXBindTemporaryExpr, _Mapping]] = ..., cxx_bool_literal_expr: _Optional[_Union[CXXBoolLiteralExpr, _Mapping]] = ..., cxx_const_cast_expr: _Optional[_Union[CXXConstCastExpr, _Mapping]] = ..., cxx_construct_expr: _Optional[_Union[CXXConstructExpr, _Mapping]] = ..., cxx_default_arg_expr: _Optional[_Union[CXXDefaultArgExpr, _Mapping]] = ..., cxx_default_init_expr: _Optional[_Union[CXXDefaultInitExpr, _Mapping]] = ..., cxx_delete_expr: _Optional[_Union[CXXDeleteExpr, _Mapping]] = ..., cxx_dependent_scope_member_expr: _Optional[_Union[CXXDependentScopeMemberExpr, _Mapping]] = ..., cxx_dynamic_cast_expr: _Optional[_Union[CXXDynamicCastExpr, _Mapping]] = ..., cxx_fold_expr: _Optional[_Union[CXXFoldExpr, _Mapping]] = ..., cxx_functional_cast_expr: _Optional[_Union[CXXFunctionalCastExpr, _Mapping]] = ..., cxx_inherited_ctor_init_expr: _Optional[_Union[CXXInheritedCtorInitExpr, _Mapping]] = ..., cxx_member_call_expr: _Optional[_Union[CXXMemberCallExpr, _Mapping]] = ..., cxx_new_expr: _Optional[_Union[CXXNewExpr, _Mapping]] = ..., cxx_noexcept_expr: _Optional[_Union[CXXNoexceptExpr, _Mapping]] = ..., cxx_null_ptr_literal_expr: _Optional[_Union[CXXNullPtrLiteralExpr, _Mapping]] = ..., cxx_operator_call_expr: _Optional[_Union[CXXOperatorCallExpr, _Mapping]] = ..., cxx_paren_list_init_expr: _Optional[_Union[CXXParenListInitExpr, _Mapping]] = ..., cxx_pseudo_destructor_expr: _Optional[_Union[CXXPseudoDestructorExpr, _Mapping]] = ..., cxx_reinterpret_cast_expr: _Optional[_Union[CXXReinterpretCastExpr, _Mapping]] = ..., cxx_rewritten_binary_operator: _Optional[_Union[CXXRewrittenBinaryOperator, _Mapping]] = ..., cxx_scalar_value_init_expr: _Optional[_Union[CXXScalarValueInitExpr, _Mapping]] = ..., cxx_static_cast_expr: _Optional[_Union[CXXStaticCastExpr, _Mapping]] = ..., cxx_std_initializer_list_expr: _Optional[_Union[CXXStdInitializerListExpr, _Mapping]] = ..., cxx_temporary_object_expr: _Optional[_Union[CXXTemporaryObjectExpr, _Mapping]] = ..., cxx_this_expr: _Optional[_Union[CXXThisExpr, _Mapping]] = ..., cxx_throw_expr: _Optional[_Union[CXXThrowExpr, _Mapping]] = ..., cxx_typeid_expr: _Optional[_Union[CXXTypeidExpr, _Mapping]] = ..., cxx_unresolved_construct_expr: _Optional[_Union[CXXUnresolvedConstructExpr, _Mapping]] = ..., cxx_uuidof_expr: _Optional[_Union[CXXUuidofExpr, _Mapping]] = ..., call_expr: _Optional[_Union[CallExpr, _Mapping]] = ..., character_literal: _Optional[_Union[CharacterLiteral, _Mapping]] = ..., choose_expr: _Optional[_Union[ChooseExpr, _Mapping]] = ..., coawait_expr: _Optional[_Union[CoawaitExpr, _Mapping]] = ..., compound_assign_operator: _Optional[_Union[CompoundAssignOperator, _Mapping]] = ..., compound_literal_expr: _Optional[_Union[CompoundLiteralExpr, _Mapping]] = ..., concept_specialization_expr: _Optional[_Union[ConceptSpecializationExpr, _Mapping]] = ..., conditional_operator: _Optional[_Union[ConditionalOperator, _Mapping]] = ..., constant_expr: _Optional[_Union[ConstantExpr, _Mapping]] = ..., convert_vector_expr: _Optional[_Union[ConvertVectorExpr, _Mapping]] = ..., coyield_expr: _Optional[_Union[CoyieldExpr, _Mapping]] = ..., decl_ref_expr: _Optional[_Union[DeclRefExpr, _Mapping]] = ..., dependent_coawait_expr: _Optional[_Union[DependentCoawaitExpr, _Mapping]] = ..., dependent_scope_decl_ref_expr: _Optional[_Union[DependentScopeDeclRefExpr, _Mapping]] = ..., designated_init_expr: _Optional[_Union[DesignatedInitExpr, _Mapping]] = ..., designated_init_update_expr: _Optional[_Union[DesignatedInitUpdateExpr, _Mapping]] = ..., embed_expr: _Optional[_Union[EmbedExpr, _Mapping]] = ..., expr_with_cleanups: _Optional[_Union[ExprWithCleanups, _Mapping]] = ..., expression_trait_expr: _Optional[_Union[ExpressionTraitExpr, _Mapping]] = ..., ext_vector_element_expr: _Optional[_Union[ExtVectorElementExpr, _Mapping]] = ..., fixed_point_literal: _Optional[_Union[FixedPointLiteral, _Mapping]] = ..., floating_literal: _Optional[_Union[FloatingLiteral, _Mapping]] = ..., function_parm_pack_expr: _Optional[_Union[FunctionParmPackExpr, _Mapping]] = ..., gnu_null_expr: _Optional[_Union[GNUNullExpr, _Mapping]] = ..., generic_selection_expr: _Optional[_Union[GenericSelectionExpr, _Mapping]] = ..., imaginary_literal: _Optional[_Union[ImaginaryLiteral, _Mapping]] = ..., implicit_cast_expr: _Optional[_Union[ImplicitCastExpr, _Mapping]] = ..., implicit_value_init_expr: _Optional[_Union[ImplicitValueInitExpr, _Mapping]] = ..., init_list_expr: _Optional[_Union[InitListExpr, _Mapping]] = ..., integer_literal: _Optional[_Union[IntegerLiteral, _Mapping]] = ..., lambda_expr: _Optional[_Union[LambdaExpr, _Mapping]] = ..., ms_property_ref_expr: _Optional[_Union[MSPropertyRefExpr, _Mapping]] = ..., ms_property_subscript_expr: _Optional[_Union[MSPropertySubscriptExpr, _Mapping]] = ..., materialize_temporary_expr: _Optional[_Union[MaterializeTemporaryExpr, _Mapping]] = ..., matrix_single_subscript_expr: _Optional[_Union[MatrixSingleSubscriptExpr, _Mapping]] = ..., matrix_subscript_expr: _Optional[_Union[MatrixSubscriptExpr, _Mapping]] = ..., member_expr: _Optional[_Union[MemberExpr, _Mapping]] = ..., no_init_expr: _Optional[_Union[NoInitExpr, _Mapping]] = ..., offset_of_expr: _Optional[_Union[OffsetOfExpr, _Mapping]] = ..., opaque_value_expr: _Optional[_Union[OpaqueValueExpr, _Mapping]] = ..., pack_expansion_expr: _Optional[_Union[PackExpansionExpr, _Mapping]] = ..., pack_indexing_expr: _Optional[_Union[PackIndexingExpr, _Mapping]] = ..., paren_expr: _Optional[_Union[ParenExpr, _Mapping]] = ..., paren_list_expr: _Optional[_Union[ParenListExpr, _Mapping]] = ..., predefined_expr: _Optional[_Union[PredefinedExpr, _Mapping]] = ..., pseudo_object_expr: _Optional[_Union[PseudoObjectExpr, _Mapping]] = ..., recovery_expr: _Optional[_Union[RecoveryExpr, _Mapping]] = ..., requires_expr: _Optional[_Union[RequiresExpr, _Mapping]] = ..., shuffle_vector_expr: _Optional[_Union[ShuffleVectorExpr, _Mapping]] = ..., size_of_pack_expr: _Optional[_Union[SizeOfPackExpr, _Mapping]] = ..., source_loc_expr: _Optional[_Union[SourceLocExpr, _Mapping]] = ..., stmt_expr: _Optional[_Union[StmtExpr, _Mapping]] = ..., string_literal: _Optional[_Union[StringLiteral, _Mapping]] = ..., subst_non_type_template_parm_expr: _Optional[_Union[SubstNonTypeTemplateParmExpr, _Mapping]] = ..., subst_non_type_template_parm_pack_expr: _Optional[_Union[SubstNonTypeTemplateParmPackExpr, _Mapping]] = ..., type_trait_expr: _Optional[_Union[TypeTraitExpr, _Mapping]] = ..., unary_expr_or_type_trait_expr: _Optional[_Union[UnaryExprOrTypeTraitExpr, _Mapping]] = ..., unary_operator: _Optional[_Union[UnaryOperator, _Mapping]] = ..., unresolved_lookup_expr: _Optional[_Union[UnresolvedLookupExpr, _Mapping]] = ..., unresolved_member_expr: _Optional[_Union[UnresolvedMemberExpr, _Mapping]] = ..., user_defined_literal: _Optional[_Union[UserDefinedLiteral, _Mapping]] = ..., va_arg_expr: _Optional[_Union[VAArgExpr, _Mapping]] = ...) -> None: ...

class StatementValue(_message.Message):
    __slots__ = ("is_complete", "expression", "attributed_stmt", "break_stmt", "cxx_catch_stmt", "cxx_for_range_stmt", "cxx_try_stmt", "case_stmt", "compound_stmt", "continue_stmt", "coreturn_stmt", "coroutine_body_stmt", "decl_stmt", "default_stmt", "do_stmt", "for_stmt", "gcc_asm_stmt", "goto_stmt", "if_stmt", "indirect_goto_stmt", "label_stmt", "ms_asm_stmt", "ms_dependent_exists_stmt", "null_stmt", "return_stmt", "seh_except_stmt", "seh_finally_stmt", "seh_leave_stmt", "seh_try_stmt", "switch_stmt", "while_stmt")
    IS_COMPLETE_FIELD_NUMBER: _ClassVar[int]
    EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTED_STMT_FIELD_NUMBER: _ClassVar[int]
    BREAK_STMT_FIELD_NUMBER: _ClassVar[int]
    CXX_CATCH_STMT_FIELD_NUMBER: _ClassVar[int]
    CXX_FOR_RANGE_STMT_FIELD_NUMBER: _ClassVar[int]
    CXX_TRY_STMT_FIELD_NUMBER: _ClassVar[int]
    CASE_STMT_FIELD_NUMBER: _ClassVar[int]
    COMPOUND_STMT_FIELD_NUMBER: _ClassVar[int]
    CONTINUE_STMT_FIELD_NUMBER: _ClassVar[int]
    CORETURN_STMT_FIELD_NUMBER: _ClassVar[int]
    COROUTINE_BODY_STMT_FIELD_NUMBER: _ClassVar[int]
    DECL_STMT_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_STMT_FIELD_NUMBER: _ClassVar[int]
    DO_STMT_FIELD_NUMBER: _ClassVar[int]
    FOR_STMT_FIELD_NUMBER: _ClassVar[int]
    GCC_ASM_STMT_FIELD_NUMBER: _ClassVar[int]
    GOTO_STMT_FIELD_NUMBER: _ClassVar[int]
    IF_STMT_FIELD_NUMBER: _ClassVar[int]
    INDIRECT_GOTO_STMT_FIELD_NUMBER: _ClassVar[int]
    LABEL_STMT_FIELD_NUMBER: _ClassVar[int]
    MS_ASM_STMT_FIELD_NUMBER: _ClassVar[int]
    MS_DEPENDENT_EXISTS_STMT_FIELD_NUMBER: _ClassVar[int]
    NULL_STMT_FIELD_NUMBER: _ClassVar[int]
    RETURN_STMT_FIELD_NUMBER: _ClassVar[int]
    SEH_EXCEPT_STMT_FIELD_NUMBER: _ClassVar[int]
    SEH_FINALLY_STMT_FIELD_NUMBER: _ClassVar[int]
    SEH_LEAVE_STMT_FIELD_NUMBER: _ClassVar[int]
    SEH_TRY_STMT_FIELD_NUMBER: _ClassVar[int]
    SWITCH_STMT_FIELD_NUMBER: _ClassVar[int]
    WHILE_STMT_FIELD_NUMBER: _ClassVar[int]
    is_complete: bool
    expression: ExpressionValue
    attributed_stmt: AttributedStmt
    break_stmt: BreakStmt
    cxx_catch_stmt: CXXCatchStmt
    cxx_for_range_stmt: CXXForRangeStmt
    cxx_try_stmt: CXXTryStmt
    case_stmt: CaseStmt
    compound_stmt: CompoundStmt
    continue_stmt: ContinueStmt
    coreturn_stmt: CoreturnStmt
    coroutine_body_stmt: CoroutineBodyStmt
    decl_stmt: DeclStmt
    default_stmt: DefaultStmt
    do_stmt: DoStmt
    for_stmt: ForStmt
    gcc_asm_stmt: GCCAsmStmt
    goto_stmt: GotoStmt
    if_stmt: IfStmt
    indirect_goto_stmt: IndirectGotoStmt
    label_stmt: LabelStmt
    ms_asm_stmt: MSAsmStmt
    ms_dependent_exists_stmt: MSDependentExistsStmt
    null_stmt: NullStmt
    return_stmt: ReturnStmt
    seh_except_stmt: SEHExceptStmt
    seh_finally_stmt: SEHFinallyStmt
    seh_leave_stmt: SEHLeaveStmt
    seh_try_stmt: SEHTryStmt
    switch_stmt: SwitchStmt
    while_stmt: WhileStmt
    def __init__(self, is_complete: _Optional[bool] = ..., expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., attributed_stmt: _Optional[_Union[AttributedStmt, _Mapping]] = ..., break_stmt: _Optional[_Union[BreakStmt, _Mapping]] = ..., cxx_catch_stmt: _Optional[_Union[CXXCatchStmt, _Mapping]] = ..., cxx_for_range_stmt: _Optional[_Union[CXXForRangeStmt, _Mapping]] = ..., cxx_try_stmt: _Optional[_Union[CXXTryStmt, _Mapping]] = ..., case_stmt: _Optional[_Union[CaseStmt, _Mapping]] = ..., compound_stmt: _Optional[_Union[CompoundStmt, _Mapping]] = ..., continue_stmt: _Optional[_Union[ContinueStmt, _Mapping]] = ..., coreturn_stmt: _Optional[_Union[CoreturnStmt, _Mapping]] = ..., coroutine_body_stmt: _Optional[_Union[CoroutineBodyStmt, _Mapping]] = ..., decl_stmt: _Optional[_Union[DeclStmt, _Mapping]] = ..., default_stmt: _Optional[_Union[DefaultStmt, _Mapping]] = ..., do_stmt: _Optional[_Union[DoStmt, _Mapping]] = ..., for_stmt: _Optional[_Union[ForStmt, _Mapping]] = ..., gcc_asm_stmt: _Optional[_Union[GCCAsmStmt, _Mapping]] = ..., goto_stmt: _Optional[_Union[GotoStmt, _Mapping]] = ..., if_stmt: _Optional[_Union[IfStmt, _Mapping]] = ..., indirect_goto_stmt: _Optional[_Union[IndirectGotoStmt, _Mapping]] = ..., label_stmt: _Optional[_Union[LabelStmt, _Mapping]] = ..., ms_asm_stmt: _Optional[_Union[MSAsmStmt, _Mapping]] = ..., ms_dependent_exists_stmt: _Optional[_Union[MSDependentExistsStmt, _Mapping]] = ..., null_stmt: _Optional[_Union[NullStmt, _Mapping]] = ..., return_stmt: _Optional[_Union[ReturnStmt, _Mapping]] = ..., seh_except_stmt: _Optional[_Union[SEHExceptStmt, _Mapping]] = ..., seh_finally_stmt: _Optional[_Union[SEHFinallyStmt, _Mapping]] = ..., seh_leave_stmt: _Optional[_Union[SEHLeaveStmt, _Mapping]] = ..., seh_try_stmt: _Optional[_Union[SEHTryStmt, _Mapping]] = ..., switch_stmt: _Optional[_Union[SwitchStmt, _Mapping]] = ..., while_stmt: _Optional[_Union[WhileStmt, _Mapping]] = ...) -> None: ...

class TypeValue(_message.Message):
    __slots__ = ("is_complete", "adjusted_type", "atomic_type", "attributed_type", "auto_type", "btf_tag_attributed_type", "bit_int_type", "block_pointer_type", "builtin_type", "complex_type", "constant_array_type", "constant_matrix_type", "count_attributed_type", "decayed_type", "decltype_type", "deduced_template_specialization_type", "dependent_address_space_type", "dependent_bit_int_type", "dependent_decltype_type", "dependent_name_type", "dependent_sized_array_type", "dependent_sized_ext_vector_type", "dependent_sized_matrix_type", "dependent_type_of_expr_type", "dependent_vector_type", "enum_type", "ext_vector_type", "function_proto_type", "incomplete_array_type", "injected_class_name_type", "l_value_reference_type", "macro_qualified_type", "member_pointer_type", "pack_expansion_type", "pack_indexing_type", "paren_type", "pointer_type", "predefined_sugar_type", "r_value_reference_type", "record_type", "subst_builtin_template_pack_type", "subst_template_type_parm_pack_type", "subst_template_type_parm_type", "template_specialization_type", "template_type_parm_type", "type_of_expr_type", "type_of_type", "typedef_type", "unary_transform_type", "unresolved_using_type", "using_type", "variable_array_type", "vector_type")
    IS_COMPLETE_FIELD_NUMBER: _ClassVar[int]
    ADJUSTED_TYPE_FIELD_NUMBER: _ClassVar[int]
    ATOMIC_TYPE_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTED_TYPE_FIELD_NUMBER: _ClassVar[int]
    AUTO_TYPE_FIELD_NUMBER: _ClassVar[int]
    BTF_TAG_ATTRIBUTED_TYPE_FIELD_NUMBER: _ClassVar[int]
    BIT_INT_TYPE_FIELD_NUMBER: _ClassVar[int]
    BLOCK_POINTER_TYPE_FIELD_NUMBER: _ClassVar[int]
    BUILTIN_TYPE_FIELD_NUMBER: _ClassVar[int]
    COMPLEX_TYPE_FIELD_NUMBER: _ClassVar[int]
    CONSTANT_ARRAY_TYPE_FIELD_NUMBER: _ClassVar[int]
    CONSTANT_MATRIX_TYPE_FIELD_NUMBER: _ClassVar[int]
    COUNT_ATTRIBUTED_TYPE_FIELD_NUMBER: _ClassVar[int]
    DECAYED_TYPE_FIELD_NUMBER: _ClassVar[int]
    DECLTYPE_TYPE_FIELD_NUMBER: _ClassVar[int]
    DEDUCED_TEMPLATE_SPECIALIZATION_TYPE_FIELD_NUMBER: _ClassVar[int]
    DEPENDENT_ADDRESS_SPACE_TYPE_FIELD_NUMBER: _ClassVar[int]
    DEPENDENT_BIT_INT_TYPE_FIELD_NUMBER: _ClassVar[int]
    DEPENDENT_DECLTYPE_TYPE_FIELD_NUMBER: _ClassVar[int]
    DEPENDENT_NAME_TYPE_FIELD_NUMBER: _ClassVar[int]
    DEPENDENT_SIZED_ARRAY_TYPE_FIELD_NUMBER: _ClassVar[int]
    DEPENDENT_SIZED_EXT_VECTOR_TYPE_FIELD_NUMBER: _ClassVar[int]
    DEPENDENT_SIZED_MATRIX_TYPE_FIELD_NUMBER: _ClassVar[int]
    DEPENDENT_TYPE_OF_EXPR_TYPE_FIELD_NUMBER: _ClassVar[int]
    DEPENDENT_VECTOR_TYPE_FIELD_NUMBER: _ClassVar[int]
    ENUM_TYPE_FIELD_NUMBER: _ClassVar[int]
    EXT_VECTOR_TYPE_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_PROTO_TYPE_FIELD_NUMBER: _ClassVar[int]
    INCOMPLETE_ARRAY_TYPE_FIELD_NUMBER: _ClassVar[int]
    INJECTED_CLASS_NAME_TYPE_FIELD_NUMBER: _ClassVar[int]
    L_VALUE_REFERENCE_TYPE_FIELD_NUMBER: _ClassVar[int]
    MACRO_QUALIFIED_TYPE_FIELD_NUMBER: _ClassVar[int]
    MEMBER_POINTER_TYPE_FIELD_NUMBER: _ClassVar[int]
    PACK_EXPANSION_TYPE_FIELD_NUMBER: _ClassVar[int]
    PACK_INDEXING_TYPE_FIELD_NUMBER: _ClassVar[int]
    PAREN_TYPE_FIELD_NUMBER: _ClassVar[int]
    POINTER_TYPE_FIELD_NUMBER: _ClassVar[int]
    PREDEFINED_SUGAR_TYPE_FIELD_NUMBER: _ClassVar[int]
    R_VALUE_REFERENCE_TYPE_FIELD_NUMBER: _ClassVar[int]
    RECORD_TYPE_FIELD_NUMBER: _ClassVar[int]
    SUBST_BUILTIN_TEMPLATE_PACK_TYPE_FIELD_NUMBER: _ClassVar[int]
    SUBST_TEMPLATE_TYPE_PARM_PACK_TYPE_FIELD_NUMBER: _ClassVar[int]
    SUBST_TEMPLATE_TYPE_PARM_TYPE_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_SPECIALIZATION_TYPE_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_TYPE_PARM_TYPE_FIELD_NUMBER: _ClassVar[int]
    TYPE_OF_EXPR_TYPE_FIELD_NUMBER: _ClassVar[int]
    TYPE_OF_TYPE_FIELD_NUMBER: _ClassVar[int]
    TYPEDEF_TYPE_FIELD_NUMBER: _ClassVar[int]
    UNARY_TRANSFORM_TYPE_FIELD_NUMBER: _ClassVar[int]
    UNRESOLVED_USING_TYPE_FIELD_NUMBER: _ClassVar[int]
    USING_TYPE_FIELD_NUMBER: _ClassVar[int]
    VARIABLE_ARRAY_TYPE_FIELD_NUMBER: _ClassVar[int]
    VECTOR_TYPE_FIELD_NUMBER: _ClassVar[int]
    is_complete: bool
    adjusted_type: AdjustedType
    atomic_type: AtomicType
    attributed_type: AttributedType
    auto_type: AutoType
    btf_tag_attributed_type: BTFTagAttributedType
    bit_int_type: BitIntType
    block_pointer_type: BlockPointerType
    builtin_type: BuiltinType
    complex_type: ComplexType
    constant_array_type: ConstantArrayType
    constant_matrix_type: ConstantMatrixType
    count_attributed_type: CountAttributedType
    decayed_type: DecayedType
    decltype_type: DecltypeType
    deduced_template_specialization_type: DeducedTemplateSpecializationType
    dependent_address_space_type: DependentAddressSpaceType
    dependent_bit_int_type: DependentBitIntType
    dependent_decltype_type: DependentDecltypeType
    dependent_name_type: DependentNameType
    dependent_sized_array_type: DependentSizedArrayType
    dependent_sized_ext_vector_type: DependentSizedExtVectorType
    dependent_sized_matrix_type: DependentSizedMatrixType
    dependent_type_of_expr_type: DependentTypeOfExprType
    dependent_vector_type: DependentVectorType
    enum_type: EnumType
    ext_vector_type: ExtVectorType
    function_proto_type: FunctionProtoType
    incomplete_array_type: IncompleteArrayType
    injected_class_name_type: InjectedClassNameType
    l_value_reference_type: LValueReferenceType
    macro_qualified_type: MacroQualifiedType
    member_pointer_type: MemberPointerType
    pack_expansion_type: PackExpansionType
    pack_indexing_type: PackIndexingType
    paren_type: ParenType
    pointer_type: PointerType
    predefined_sugar_type: PredefinedSugarType
    r_value_reference_type: RValueReferenceType
    record_type: RecordType
    subst_builtin_template_pack_type: SubstBuiltinTemplatePackType
    subst_template_type_parm_pack_type: SubstTemplateTypeParmPackType
    subst_template_type_parm_type: SubstTemplateTypeParmType
    template_specialization_type: TemplateSpecializationType
    template_type_parm_type: TemplateTypeParmType
    type_of_expr_type: TypeOfExprType
    type_of_type: TypeOfType
    typedef_type: TypedefType
    unary_transform_type: UnaryTransformType
    unresolved_using_type: UnresolvedUsingType
    using_type: UsingType
    variable_array_type: VariableArrayType
    vector_type: VectorType
    def __init__(self, is_complete: _Optional[bool] = ..., adjusted_type: _Optional[_Union[AdjustedType, _Mapping]] = ..., atomic_type: _Optional[_Union[AtomicType, _Mapping]] = ..., attributed_type: _Optional[_Union[AttributedType, _Mapping]] = ..., auto_type: _Optional[_Union[AutoType, _Mapping]] = ..., btf_tag_attributed_type: _Optional[_Union[BTFTagAttributedType, _Mapping]] = ..., bit_int_type: _Optional[_Union[BitIntType, _Mapping]] = ..., block_pointer_type: _Optional[_Union[BlockPointerType, _Mapping]] = ..., builtin_type: _Optional[_Union[BuiltinType, _Mapping]] = ..., complex_type: _Optional[_Union[ComplexType, _Mapping]] = ..., constant_array_type: _Optional[_Union[ConstantArrayType, _Mapping]] = ..., constant_matrix_type: _Optional[_Union[ConstantMatrixType, _Mapping]] = ..., count_attributed_type: _Optional[_Union[CountAttributedType, _Mapping]] = ..., decayed_type: _Optional[_Union[DecayedType, _Mapping]] = ..., decltype_type: _Optional[_Union[DecltypeType, _Mapping]] = ..., deduced_template_specialization_type: _Optional[_Union[DeducedTemplateSpecializationType, _Mapping]] = ..., dependent_address_space_type: _Optional[_Union[DependentAddressSpaceType, _Mapping]] = ..., dependent_bit_int_type: _Optional[_Union[DependentBitIntType, _Mapping]] = ..., dependent_decltype_type: _Optional[_Union[DependentDecltypeType, _Mapping]] = ..., dependent_name_type: _Optional[_Union[DependentNameType, _Mapping]] = ..., dependent_sized_array_type: _Optional[_Union[DependentSizedArrayType, _Mapping]] = ..., dependent_sized_ext_vector_type: _Optional[_Union[DependentSizedExtVectorType, _Mapping]] = ..., dependent_sized_matrix_type: _Optional[_Union[DependentSizedMatrixType, _Mapping]] = ..., dependent_type_of_expr_type: _Optional[_Union[DependentTypeOfExprType, _Mapping]] = ..., dependent_vector_type: _Optional[_Union[DependentVectorType, _Mapping]] = ..., enum_type: _Optional[_Union[EnumType, _Mapping]] = ..., ext_vector_type: _Optional[_Union[ExtVectorType, _Mapping]] = ..., function_proto_type: _Optional[_Union[FunctionProtoType, _Mapping]] = ..., incomplete_array_type: _Optional[_Union[IncompleteArrayType, _Mapping]] = ..., injected_class_name_type: _Optional[_Union[InjectedClassNameType, _Mapping]] = ..., l_value_reference_type: _Optional[_Union[LValueReferenceType, _Mapping]] = ..., macro_qualified_type: _Optional[_Union[MacroQualifiedType, _Mapping]] = ..., member_pointer_type: _Optional[_Union[MemberPointerType, _Mapping]] = ..., pack_expansion_type: _Optional[_Union[PackExpansionType, _Mapping]] = ..., pack_indexing_type: _Optional[_Union[PackIndexingType, _Mapping]] = ..., paren_type: _Optional[_Union[ParenType, _Mapping]] = ..., pointer_type: _Optional[_Union[PointerType, _Mapping]] = ..., predefined_sugar_type: _Optional[_Union[PredefinedSugarType, _Mapping]] = ..., r_value_reference_type: _Optional[_Union[RValueReferenceType, _Mapping]] = ..., record_type: _Optional[_Union[RecordType, _Mapping]] = ..., subst_builtin_template_pack_type: _Optional[_Union[SubstBuiltinTemplatePackType, _Mapping]] = ..., subst_template_type_parm_pack_type: _Optional[_Union[SubstTemplateTypeParmPackType, _Mapping]] = ..., subst_template_type_parm_type: _Optional[_Union[SubstTemplateTypeParmType, _Mapping]] = ..., template_specialization_type: _Optional[_Union[TemplateSpecializationType, _Mapping]] = ..., template_type_parm_type: _Optional[_Union[TemplateTypeParmType, _Mapping]] = ..., type_of_expr_type: _Optional[_Union[TypeOfExprType, _Mapping]] = ..., type_of_type: _Optional[_Union[TypeOfType, _Mapping]] = ..., typedef_type: _Optional[_Union[TypedefType, _Mapping]] = ..., unary_transform_type: _Optional[_Union[UnaryTransformType, _Mapping]] = ..., unresolved_using_type: _Optional[_Union[UnresolvedUsingType, _Mapping]] = ..., using_type: _Optional[_Union[UsingType, _Mapping]] = ..., variable_array_type: _Optional[_Union[VariableArrayType, _Mapping]] = ..., vector_type: _Optional[_Union[VectorType, _Mapping]] = ...) -> None: ...

class TranslationUnitDecl(_message.Message):
    __slots__ = ("declaration", "declarations", "anonymous_namespace")
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    DECLARATIONS_FIELD_NUMBER: _ClassVar[int]
    ANONYMOUS_NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    declaration: DeclInfo
    declarations: _containers.RepeatedCompositeFieldContainer[DeclarationValue]
    anonymous_namespace: DeclarationSymbol
    def __init__(self, declaration: _Optional[_Union[DeclInfo, _Mapping]] = ..., declarations: _Optional[_Iterable[_Union[DeclarationValue, _Mapping]]] = ..., anonymous_namespace: _Optional[_Union[DeclarationSymbol, _Mapping]] = ...) -> None: ...

class TopLevelStmtDecl(_message.Message):
    __slots__ = ("declaration", "statement")
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    STATEMENT_FIELD_NUMBER: _ClassVar[int]
    declaration: DeclInfo
    statement: StatementValue
    def __init__(self, declaration: _Optional[_Union[DeclInfo, _Mapping]] = ..., statement: _Optional[_Union[StatementValue, _Mapping]] = ...) -> None: ...

class RequiresExprBodyDecl(_message.Message):
    __slots__ = ("declaration", "local_parameters")
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    LOCAL_PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    declaration: DeclInfo
    local_parameters: _containers.RepeatedCompositeFieldContainer[DeclarationValue]
    def __init__(self, declaration: _Optional[_Union[DeclInfo, _Mapping]] = ..., local_parameters: _Optional[_Iterable[_Union[DeclarationValue, _Mapping]]] = ...) -> None: ...

class LinkageSpecDecl(_message.Message):
    __slots__ = ("declaration", "language", "declarations")
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    LANGUAGE_FIELD_NUMBER: _ClassVar[int]
    DECLARATIONS_FIELD_NUMBER: _ClassVar[int]
    declaration: DeclInfo
    language: DeclLinkageLanguage
    declarations: _containers.RepeatedCompositeFieldContainer[DeclarationValue]
    def __init__(self, declaration: _Optional[_Union[DeclInfo, _Mapping]] = ..., language: _Optional[_Union[DeclLinkageLanguage, str]] = ..., declarations: _Optional[_Iterable[_Union[DeclarationValue, _Mapping]]] = ...) -> None: ...

class ExternCContextDecl(_message.Message):
    __slots__ = ("declaration", "declarations")
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    DECLARATIONS_FIELD_NUMBER: _ClassVar[int]
    declaration: DeclInfo
    declarations: _containers.RepeatedCompositeFieldContainer[DeclarationValue]
    def __init__(self, declaration: _Optional[_Union[DeclInfo, _Mapping]] = ..., declarations: _Optional[_Iterable[_Union[DeclarationValue, _Mapping]]] = ...) -> None: ...

class ExportDecl(_message.Message):
    __slots__ = ("declaration", "declarations")
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    DECLARATIONS_FIELD_NUMBER: _ClassVar[int]
    declaration: DeclInfo
    declarations: _containers.RepeatedCompositeFieldContainer[DeclarationValue]
    def __init__(self, declaration: _Optional[_Union[DeclInfo, _Mapping]] = ..., declarations: _Optional[_Iterable[_Union[DeclarationValue, _Mapping]]] = ...) -> None: ...

class BlockDecl(_message.Message):
    __slots__ = ("declaration", "parameters", "body", "captures", "is_variadic", "signature")
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    CAPTURES_FIELD_NUMBER: _ClassVar[int]
    IS_VARIADIC_FIELD_NUMBER: _ClassVar[int]
    SIGNATURE_FIELD_NUMBER: _ClassVar[int]
    declaration: DeclInfo
    parameters: _containers.RepeatedCompositeFieldContainer[DeclarationValue]
    body: StatementValue
    captures: _containers.RepeatedCompositeFieldContainer[BlockCaptureInfo]
    is_variadic: bool
    signature: QualType
    def __init__(self, declaration: _Optional[_Union[DeclInfo, _Mapping]] = ..., parameters: _Optional[_Iterable[_Union[DeclarationValue, _Mapping]]] = ..., body: _Optional[_Union[StatementValue, _Mapping]] = ..., captures: _Optional[_Iterable[_Union[BlockCaptureInfo, _Mapping]]] = ..., is_variadic: _Optional[bool] = ..., signature: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class StaticAssertDecl(_message.Message):
    __slots__ = ("declaration", "assertion_expression", "message_expression", "is_failed")
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    ASSERTION_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    MESSAGE_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    IS_FAILED_FIELD_NUMBER: _ClassVar[int]
    declaration: DeclInfo
    assertion_expression: ExpressionValue
    message_expression: ExpressionValue
    is_failed: bool
    def __init__(self, declaration: _Optional[_Union[DeclInfo, _Mapping]] = ..., assertion_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., message_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., is_failed: _Optional[bool] = ...) -> None: ...

class PragmaDetectMismatchDecl(_message.Message):
    __slots__ = ("declaration", "name", "value")
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    declaration: DeclInfo
    name: str
    value: str
    def __init__(self, declaration: _Optional[_Union[DeclInfo, _Mapping]] = ..., name: _Optional[str] = ..., value: _Optional[str] = ...) -> None: ...

class PragmaCommentDecl(_message.Message):
    __slots__ = ("declaration", "comment_kind", "text")
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    COMMENT_KIND_FIELD_NUMBER: _ClassVar[int]
    TEXT_FIELD_NUMBER: _ClassVar[int]
    declaration: DeclInfo
    comment_kind: DeclPragmaCommentKind
    text: str
    def __init__(self, declaration: _Optional[_Union[DeclInfo, _Mapping]] = ..., comment_kind: _Optional[_Union[DeclPragmaCommentKind, str]] = ..., text: _Optional[str] = ...) -> None: ...

class UnresolvedUsingValueDecl(_message.Message):
    __slots__ = ("value", "qualifier", "target_name")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    TARGET_NAME_FIELD_NUMBER: _ClassVar[int]
    value: ValueDeclInfo
    qualifier: NestedNameSpecifier
    target_name: DeclarationName
    def __init__(self, value: _Optional[_Union[ValueDeclInfo, _Mapping]] = ..., qualifier: _Optional[_Union[NestedNameSpecifier, _Mapping]] = ..., target_name: _Optional[_Union[DeclarationName, _Mapping]] = ...) -> None: ...

class UnnamedGlobalConstantDecl(_message.Message):
    __slots__ = ("value", "value_as_constant")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    VALUE_AS_CONSTANT_FIELD_NUMBER: _ClassVar[int]
    value: ValueDeclInfo
    value_as_constant: APValue
    def __init__(self, value: _Optional[_Union[ValueDeclInfo, _Mapping]] = ..., value_as_constant: _Optional[_Union[APValue, _Mapping]] = ...) -> None: ...

class TemplateParamObjectDecl(_message.Message):
    __slots__ = ("value", "value_as_constant")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    VALUE_AS_CONSTANT_FIELD_NUMBER: _ClassVar[int]
    value: ValueDeclInfo
    value_as_constant: APValue
    def __init__(self, value: _Optional[_Union[ValueDeclInfo, _Mapping]] = ..., value_as_constant: _Optional[_Union[APValue, _Mapping]] = ...) -> None: ...

class MSGuidDecl(_message.Message):
    __slots__ = ("value", "data1", "data2", "data3", "data4", "value_as_constant")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    DATA1_FIELD_NUMBER: _ClassVar[int]
    DATA2_FIELD_NUMBER: _ClassVar[int]
    DATA3_FIELD_NUMBER: _ClassVar[int]
    DATA4_FIELD_NUMBER: _ClassVar[int]
    VALUE_AS_CONSTANT_FIELD_NUMBER: _ClassVar[int]
    value: ValueDeclInfo
    data1: int
    data2: int
    data3: int
    data4: bytes
    value_as_constant: APValue
    def __init__(self, value: _Optional[_Union[ValueDeclInfo, _Mapping]] = ..., data1: _Optional[int] = ..., data2: _Optional[int] = ..., data3: _Optional[int] = ..., data4: _Optional[bytes] = ..., value_as_constant: _Optional[_Union[APValue, _Mapping]] = ...) -> None: ...

class IndirectFieldDecl(_message.Message):
    __slots__ = ("value", "chain")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    CHAIN_FIELD_NUMBER: _ClassVar[int]
    value: ValueDeclInfo
    chain: _containers.RepeatedCompositeFieldContainer[DeclarationSymbol]
    def __init__(self, value: _Optional[_Union[ValueDeclInfo, _Mapping]] = ..., chain: _Optional[_Iterable[_Union[DeclarationSymbol, _Mapping]]] = ...) -> None: ...

class EnumConstantDecl(_message.Message):
    __slots__ = ("value", "initializer", "evaluated_value")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    INITIALIZER_FIELD_NUMBER: _ClassVar[int]
    EVALUATED_VALUE_FIELD_NUMBER: _ClassVar[int]
    value: ValueDeclInfo
    initializer: ExpressionValue
    evaluated_value: APSIntBits
    def __init__(self, value: _Optional[_Union[ValueDeclInfo, _Mapping]] = ..., initializer: _Optional[_Union[ExpressionValue, _Mapping]] = ..., evaluated_value: _Optional[_Union[APSIntBits, _Mapping]] = ...) -> None: ...

class FunctionDecl(_message.Message):
    __slots__ = ("function", "is_deleted", "is_defaulted", "is_explicitly_defaulted", "is_pure_virtual", "is_trivial", "is_trivial_for_call", "is_inline_specified")
    FUNCTION_FIELD_NUMBER: _ClassVar[int]
    IS_DELETED_FIELD_NUMBER: _ClassVar[int]
    IS_DEFAULTED_FIELD_NUMBER: _ClassVar[int]
    IS_EXPLICITLY_DEFAULTED_FIELD_NUMBER: _ClassVar[int]
    IS_PURE_VIRTUAL_FIELD_NUMBER: _ClassVar[int]
    IS_TRIVIAL_FIELD_NUMBER: _ClassVar[int]
    IS_TRIVIAL_FOR_CALL_FIELD_NUMBER: _ClassVar[int]
    IS_INLINE_SPECIFIED_FIELD_NUMBER: _ClassVar[int]
    function: FunctionDeclInfo
    is_deleted: bool
    is_defaulted: bool
    is_explicitly_defaulted: bool
    is_pure_virtual: bool
    is_trivial: bool
    is_trivial_for_call: bool
    is_inline_specified: bool
    def __init__(self, function: _Optional[_Union[FunctionDeclInfo, _Mapping]] = ..., is_deleted: _Optional[bool] = ..., is_defaulted: _Optional[bool] = ..., is_explicitly_defaulted: _Optional[bool] = ..., is_pure_virtual: _Optional[bool] = ..., is_trivial: _Optional[bool] = ..., is_trivial_for_call: _Optional[bool] = ..., is_inline_specified: _Optional[bool] = ...) -> None: ...

class CXXMethodDecl(_message.Message):
    __slots__ = ("method",)
    METHOD_FIELD_NUMBER: _ClassVar[int]
    method: CXXMethodDeclInfo
    def __init__(self, method: _Optional[_Union[CXXMethodDeclInfo, _Mapping]] = ...) -> None: ...

class CXXDestructorDecl(_message.Message):
    __slots__ = ("method", "is_trivial")
    METHOD_FIELD_NUMBER: _ClassVar[int]
    IS_TRIVIAL_FIELD_NUMBER: _ClassVar[int]
    method: CXXMethodDeclInfo
    is_trivial: bool
    def __init__(self, method: _Optional[_Union[CXXMethodDeclInfo, _Mapping]] = ..., is_trivial: _Optional[bool] = ...) -> None: ...

class CXXConversionDecl(_message.Message):
    __slots__ = ("method", "is_explicit", "is_explicit_specifier_value", "explicit_specifier_expression")
    METHOD_FIELD_NUMBER: _ClassVar[int]
    IS_EXPLICIT_FIELD_NUMBER: _ClassVar[int]
    IS_EXPLICIT_SPECIFIER_VALUE_FIELD_NUMBER: _ClassVar[int]
    EXPLICIT_SPECIFIER_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    method: CXXMethodDeclInfo
    is_explicit: bool
    is_explicit_specifier_value: bool
    explicit_specifier_expression: ExpressionValue
    def __init__(self, method: _Optional[_Union[CXXMethodDeclInfo, _Mapping]] = ..., is_explicit: _Optional[bool] = ..., is_explicit_specifier_value: _Optional[bool] = ..., explicit_specifier_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class CXXConstructorDecl(_message.Message):
    __slots__ = ("method", "initializers", "is_explicit", "is_explicit_specifier_value", "is_converting_constructor", "is_copy_constructor", "is_move_constructor", "is_default_constructor", "is_delegating_constructor", "explicit_specifier_expression")
    METHOD_FIELD_NUMBER: _ClassVar[int]
    INITIALIZERS_FIELD_NUMBER: _ClassVar[int]
    IS_EXPLICIT_FIELD_NUMBER: _ClassVar[int]
    IS_EXPLICIT_SPECIFIER_VALUE_FIELD_NUMBER: _ClassVar[int]
    IS_CONVERTING_CONSTRUCTOR_FIELD_NUMBER: _ClassVar[int]
    IS_COPY_CONSTRUCTOR_FIELD_NUMBER: _ClassVar[int]
    IS_MOVE_CONSTRUCTOR_FIELD_NUMBER: _ClassVar[int]
    IS_DEFAULT_CONSTRUCTOR_FIELD_NUMBER: _ClassVar[int]
    IS_DELEGATING_CONSTRUCTOR_FIELD_NUMBER: _ClassVar[int]
    EXPLICIT_SPECIFIER_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    method: CXXMethodDeclInfo
    initializers: _containers.RepeatedCompositeFieldContainer[CXXCtorInitializer]
    is_explicit: bool
    is_explicit_specifier_value: bool
    is_converting_constructor: bool
    is_copy_constructor: bool
    is_move_constructor: bool
    is_default_constructor: bool
    is_delegating_constructor: bool
    explicit_specifier_expression: ExpressionValue
    def __init__(self, method: _Optional[_Union[CXXMethodDeclInfo, _Mapping]] = ..., initializers: _Optional[_Iterable[_Union[CXXCtorInitializer, _Mapping]]] = ..., is_explicit: _Optional[bool] = ..., is_explicit_specifier_value: _Optional[bool] = ..., is_converting_constructor: _Optional[bool] = ..., is_copy_constructor: _Optional[bool] = ..., is_move_constructor: _Optional[bool] = ..., is_default_constructor: _Optional[bool] = ..., is_delegating_constructor: _Optional[bool] = ..., explicit_specifier_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class CXXDeductionGuideDecl(_message.Message):
    __slots__ = ("function", "deduced_template", "deduction_candidate_kind", "corresponding_constructor", "source_deduction_guide", "source_kind")
    FUNCTION_FIELD_NUMBER: _ClassVar[int]
    DEDUCED_TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    DEDUCTION_CANDIDATE_KIND_FIELD_NUMBER: _ClassVar[int]
    CORRESPONDING_CONSTRUCTOR_FIELD_NUMBER: _ClassVar[int]
    SOURCE_DEDUCTION_GUIDE_FIELD_NUMBER: _ClassVar[int]
    SOURCE_KIND_FIELD_NUMBER: _ClassVar[int]
    function: FunctionDeclInfo
    deduced_template: DeclarationSymbol
    deduction_candidate_kind: DeclDeductionCandidateKind
    corresponding_constructor: DeclarationSymbol
    source_deduction_guide: DeclarationSymbol
    source_kind: DeclSourceDeductionGuideKind
    def __init__(self, function: _Optional[_Union[FunctionDeclInfo, _Mapping]] = ..., deduced_template: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., deduction_candidate_kind: _Optional[_Union[DeclDeductionCandidateKind, str]] = ..., corresponding_constructor: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., source_deduction_guide: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., source_kind: _Optional[_Union[DeclSourceDeductionGuideKind, str]] = ...) -> None: ...

class VarDecl(_message.Message):
    __slots__ = ("variable", "tls_kind", "initialization_style", "is_static_data_member", "initializer_from_any_declaration")
    VARIABLE_FIELD_NUMBER: _ClassVar[int]
    TLS_KIND_FIELD_NUMBER: _ClassVar[int]
    INITIALIZATION_STYLE_FIELD_NUMBER: _ClassVar[int]
    IS_STATIC_DATA_MEMBER_FIELD_NUMBER: _ClassVar[int]
    INITIALIZER_FROM_ANY_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    variable: VarDeclInfo
    tls_kind: DeclVariableTLSKind
    initialization_style: DeclVariableInitializationStyle
    is_static_data_member: bool
    initializer_from_any_declaration: ExpressionValue
    def __init__(self, variable: _Optional[_Union[VarDeclInfo, _Mapping]] = ..., tls_kind: _Optional[_Union[DeclVariableTLSKind, str]] = ..., initialization_style: _Optional[_Union[DeclVariableInitializationStyle, str]] = ..., is_static_data_member: _Optional[bool] = ..., initializer_from_any_declaration: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class VarTemplateSpecializationDecl(_message.Message):
    __slots__ = ("variable", "template_arguments", "specialized_template", "specialization_kind")
    VARIABLE_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    SPECIALIZED_TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    SPECIALIZATION_KIND_FIELD_NUMBER: _ClassVar[int]
    variable: VarDeclInfo
    template_arguments: _containers.RepeatedCompositeFieldContainer[TemplateArgument]
    specialized_template: DeclarationSymbol
    specialization_kind: DeclTemplateSpecializationKind
    def __init__(self, variable: _Optional[_Union[VarDeclInfo, _Mapping]] = ..., template_arguments: _Optional[_Iterable[_Union[TemplateArgument, _Mapping]]] = ..., specialized_template: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., specialization_kind: _Optional[_Union[DeclTemplateSpecializationKind, str]] = ...) -> None: ...

class VarTemplatePartialSpecializationDecl(_message.Message):
    __slots__ = ("variable", "template_arguments", "template_parameters", "specialized_template", "specialized_template_or_partial")
    VARIABLE_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    SPECIALIZED_TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    SPECIALIZED_TEMPLATE_OR_PARTIAL_FIELD_NUMBER: _ClassVar[int]
    variable: VarDeclInfo
    template_arguments: _containers.RepeatedCompositeFieldContainer[TemplateArgument]
    template_parameters: TemplateParameterList
    specialized_template: DeclarationSymbol
    specialized_template_or_partial: DeclarationSymbol
    def __init__(self, variable: _Optional[_Union[VarDeclInfo, _Mapping]] = ..., template_arguments: _Optional[_Iterable[_Union[TemplateArgument, _Mapping]]] = ..., template_parameters: _Optional[_Union[TemplateParameterList, _Mapping]] = ..., specialized_template: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., specialized_template_or_partial: _Optional[_Union[DeclarationSymbol, _Mapping]] = ...) -> None: ...

class ParmVarDecl(_message.Message):
    __slots__ = ("variable", "default_argument", "function_scope_index", "function_scope_depth", "is_parameter_pack", "is_explicit_object_parameter")
    VARIABLE_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_ARGUMENT_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_SCOPE_INDEX_FIELD_NUMBER: _ClassVar[int]
    FUNCTION_SCOPE_DEPTH_FIELD_NUMBER: _ClassVar[int]
    IS_PARAMETER_PACK_FIELD_NUMBER: _ClassVar[int]
    IS_EXPLICIT_OBJECT_PARAMETER_FIELD_NUMBER: _ClassVar[int]
    variable: VarDeclInfo
    default_argument: ExpressionValue
    function_scope_index: int
    function_scope_depth: int
    is_parameter_pack: bool
    is_explicit_object_parameter: bool
    def __init__(self, variable: _Optional[_Union[VarDeclInfo, _Mapping]] = ..., default_argument: _Optional[_Union[ExpressionValue, _Mapping]] = ..., function_scope_index: _Optional[int] = ..., function_scope_depth: _Optional[int] = ..., is_parameter_pack: _Optional[bool] = ..., is_explicit_object_parameter: _Optional[bool] = ...) -> None: ...

class ImplicitParamDecl(_message.Message):
    __slots__ = ("variable", "parameter_index")
    VARIABLE_FIELD_NUMBER: _ClassVar[int]
    PARAMETER_INDEX_FIELD_NUMBER: _ClassVar[int]
    variable: VarDeclInfo
    parameter_index: int
    def __init__(self, variable: _Optional[_Union[VarDeclInfo, _Mapping]] = ..., parameter_index: _Optional[int] = ...) -> None: ...

class DecompositionDecl(_message.Message):
    __slots__ = ("variable", "bindings")
    VARIABLE_FIELD_NUMBER: _ClassVar[int]
    BINDINGS_FIELD_NUMBER: _ClassVar[int]
    variable: VarDeclInfo
    bindings: _containers.RepeatedCompositeFieldContainer[DeclarationValue]
    def __init__(self, variable: _Optional[_Union[VarDeclInfo, _Mapping]] = ..., bindings: _Optional[_Iterable[_Union[DeclarationValue, _Mapping]]] = ...) -> None: ...

class NonTypeTemplateParmDecl(_message.Message):
    __slots__ = ("declarator", "depth", "position", "is_parameter_pack", "default_argument", "default_argument_was_inherited", "is_pack_expansion", "expanded_parameter_types", "type_constraint")
    DECLARATOR_FIELD_NUMBER: _ClassVar[int]
    DEPTH_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    IS_PARAMETER_PACK_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_ARGUMENT_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_ARGUMENT_WAS_INHERITED_FIELD_NUMBER: _ClassVar[int]
    IS_PACK_EXPANSION_FIELD_NUMBER: _ClassVar[int]
    EXPANDED_PARAMETER_TYPES_FIELD_NUMBER: _ClassVar[int]
    TYPE_CONSTRAINT_FIELD_NUMBER: _ClassVar[int]
    declarator: DeclaratorDeclInfo
    depth: int
    position: int
    is_parameter_pack: bool
    default_argument: TemplateArgument
    default_argument_was_inherited: bool
    is_pack_expansion: bool
    expanded_parameter_types: _containers.RepeatedCompositeFieldContainer[QualType]
    type_constraint: TypeConstraint
    def __init__(self, declarator: _Optional[_Union[DeclaratorDeclInfo, _Mapping]] = ..., depth: _Optional[int] = ..., position: _Optional[int] = ..., is_parameter_pack: _Optional[bool] = ..., default_argument: _Optional[_Union[TemplateArgument, _Mapping]] = ..., default_argument_was_inherited: _Optional[bool] = ..., is_pack_expansion: _Optional[bool] = ..., expanded_parameter_types: _Optional[_Iterable[_Union[QualType, _Mapping]]] = ..., type_constraint: _Optional[_Union[TypeConstraint, _Mapping]] = ...) -> None: ...

class MSPropertyDecl(_message.Message):
    __slots__ = ("declarator", "getter_identifier", "setter_identifier")
    DECLARATOR_FIELD_NUMBER: _ClassVar[int]
    GETTER_IDENTIFIER_FIELD_NUMBER: _ClassVar[int]
    SETTER_IDENTIFIER_FIELD_NUMBER: _ClassVar[int]
    declarator: DeclaratorDeclInfo
    getter_identifier: str
    setter_identifier: str
    def __init__(self, declarator: _Optional[_Union[DeclaratorDeclInfo, _Mapping]] = ..., getter_identifier: _Optional[str] = ..., setter_identifier: _Optional[str] = ...) -> None: ...

class FieldDecl(_message.Message):
    __slots__ = ("declarator", "bit_width", "in_class_initializer", "is_mutable", "is_bit_field", "is_anonymous_struct_or_union")
    DECLARATOR_FIELD_NUMBER: _ClassVar[int]
    BIT_WIDTH_FIELD_NUMBER: _ClassVar[int]
    IN_CLASS_INITIALIZER_FIELD_NUMBER: _ClassVar[int]
    IS_MUTABLE_FIELD_NUMBER: _ClassVar[int]
    IS_BIT_FIELD_FIELD_NUMBER: _ClassVar[int]
    IS_ANONYMOUS_STRUCT_OR_UNION_FIELD_NUMBER: _ClassVar[int]
    declarator: DeclaratorDeclInfo
    bit_width: ExpressionValue
    in_class_initializer: ExpressionValue
    is_mutable: bool
    is_bit_field: bool
    is_anonymous_struct_or_union: bool
    def __init__(self, declarator: _Optional[_Union[DeclaratorDeclInfo, _Mapping]] = ..., bit_width: _Optional[_Union[ExpressionValue, _Mapping]] = ..., in_class_initializer: _Optional[_Union[ExpressionValue, _Mapping]] = ..., is_mutable: _Optional[bool] = ..., is_bit_field: _Optional[bool] = ..., is_anonymous_struct_or_union: _Optional[bool] = ...) -> None: ...

class BindingDecl(_message.Message):
    __slots__ = ("value", "holding_variable", "binding")
    VALUE_FIELD_NUMBER: _ClassVar[int]
    HOLDING_VARIABLE_FIELD_NUMBER: _ClassVar[int]
    BINDING_FIELD_NUMBER: _ClassVar[int]
    value: ValueDeclInfo
    holding_variable: DeclarationSymbol
    binding: ExpressionValue
    def __init__(self, value: _Optional[_Union[ValueDeclInfo, _Mapping]] = ..., holding_variable: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., binding: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class UsingShadowDecl(_message.Message):
    __slots__ = ("named", "target_declaration", "introducer")
    NAMED_FIELD_NUMBER: _ClassVar[int]
    TARGET_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    INTRODUCER_FIELD_NUMBER: _ClassVar[int]
    named: NamedDeclInfo
    target_declaration: DeclarationSymbol
    introducer: DeclarationSymbol
    def __init__(self, named: _Optional[_Union[NamedDeclInfo, _Mapping]] = ..., target_declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., introducer: _Optional[_Union[DeclarationSymbol, _Mapping]] = ...) -> None: ...

class ConstructorUsingShadowDecl(_message.Message):
    __slots__ = ("using_shadow", "nominated_base_class", "constructed_base_class", "constructs_virtual_base")
    USING_SHADOW_FIELD_NUMBER: _ClassVar[int]
    NOMINATED_BASE_CLASS_FIELD_NUMBER: _ClassVar[int]
    CONSTRUCTED_BASE_CLASS_FIELD_NUMBER: _ClassVar[int]
    CONSTRUCTS_VIRTUAL_BASE_FIELD_NUMBER: _ClassVar[int]
    using_shadow: UsingShadowDecl
    nominated_base_class: DeclarationSymbol
    constructed_base_class: DeclarationSymbol
    constructs_virtual_base: bool
    def __init__(self, using_shadow: _Optional[_Union[UsingShadowDecl, _Mapping]] = ..., nominated_base_class: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., constructed_base_class: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., constructs_virtual_base: _Optional[bool] = ...) -> None: ...

class UsingPackDecl(_message.Message):
    __slots__ = ("named", "using_declaration", "expansions")
    NAMED_FIELD_NUMBER: _ClassVar[int]
    USING_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    EXPANSIONS_FIELD_NUMBER: _ClassVar[int]
    named: NamedDeclInfo
    using_declaration: DeclarationSymbol
    expansions: _containers.RepeatedCompositeFieldContainer[DeclarationSymbol]
    def __init__(self, named: _Optional[_Union[NamedDeclInfo, _Mapping]] = ..., using_declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., expansions: _Optional[_Iterable[_Union[DeclarationSymbol, _Mapping]]] = ...) -> None: ...

class UsingDirectiveDecl(_message.Message):
    __slots__ = ("named", "nominated_namespace", "nominated_namespace_alias", "common_ancestor")
    NAMED_FIELD_NUMBER: _ClassVar[int]
    NOMINATED_NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    NOMINATED_NAMESPACE_ALIAS_FIELD_NUMBER: _ClassVar[int]
    COMMON_ANCESTOR_FIELD_NUMBER: _ClassVar[int]
    named: NamedDeclInfo
    nominated_namespace: DeclarationSymbol
    nominated_namespace_alias: DeclarationSymbol
    common_ancestor: DeclarationSymbol
    def __init__(self, named: _Optional[_Union[NamedDeclInfo, _Mapping]] = ..., nominated_namespace: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., nominated_namespace_alias: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., common_ancestor: _Optional[_Union[DeclarationSymbol, _Mapping]] = ...) -> None: ...

class UnresolvedUsingIfExistsDecl(_message.Message):
    __slots__ = ("named", "qualifier", "target_name")
    NAMED_FIELD_NUMBER: _ClassVar[int]
    QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    TARGET_NAME_FIELD_NUMBER: _ClassVar[int]
    named: NamedDeclInfo
    qualifier: NestedNameSpecifier
    target_name: DeclarationName
    def __init__(self, named: _Optional[_Union[NamedDeclInfo, _Mapping]] = ..., qualifier: _Optional[_Union[NestedNameSpecifier, _Mapping]] = ..., target_name: _Optional[_Union[DeclarationName, _Mapping]] = ...) -> None: ...

class RecordDecl(_message.Message):
    __slots__ = ("record",)
    RECORD_FIELD_NUMBER: _ClassVar[int]
    record: RecordDeclInfo
    def __init__(self, record: _Optional[_Union[RecordDeclInfo, _Mapping]] = ...) -> None: ...

class CXXRecordDecl(_message.Message):
    __slots__ = ("record", "definition_bases", "friends", "is_lambda", "is_structural")
    RECORD_FIELD_NUMBER: _ClassVar[int]
    DEFINITION_BASES_FIELD_NUMBER: _ClassVar[int]
    FRIENDS_FIELD_NUMBER: _ClassVar[int]
    IS_LAMBDA_FIELD_NUMBER: _ClassVar[int]
    IS_STRUCTURAL_FIELD_NUMBER: _ClassVar[int]
    record: RecordDeclInfo
    definition_bases: _containers.RepeatedCompositeFieldContainer[CXXBaseSpecifier]
    friends: _containers.RepeatedCompositeFieldContainer[DeclarationValue]
    is_lambda: bool
    is_structural: bool
    def __init__(self, record: _Optional[_Union[RecordDeclInfo, _Mapping]] = ..., definition_bases: _Optional[_Iterable[_Union[CXXBaseSpecifier, _Mapping]]] = ..., friends: _Optional[_Iterable[_Union[DeclarationValue, _Mapping]]] = ..., is_lambda: _Optional[bool] = ..., is_structural: _Optional[bool] = ...) -> None: ...

class ClassTemplateSpecializationDecl(_message.Message):
    __slots__ = ("record", "template_arguments", "specialized_template", "specialization_kind")
    RECORD_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    SPECIALIZED_TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    SPECIALIZATION_KIND_FIELD_NUMBER: _ClassVar[int]
    record: RecordDeclInfo
    template_arguments: _containers.RepeatedCompositeFieldContainer[TemplateArgument]
    specialized_template: DeclarationSymbol
    specialization_kind: DeclTemplateSpecializationKind
    def __init__(self, record: _Optional[_Union[RecordDeclInfo, _Mapping]] = ..., template_arguments: _Optional[_Iterable[_Union[TemplateArgument, _Mapping]]] = ..., specialized_template: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., specialization_kind: _Optional[_Union[DeclTemplateSpecializationKind, str]] = ...) -> None: ...

class ClassTemplatePartialSpecializationDecl(_message.Message):
    __slots__ = ("record", "template_arguments", "template_parameters", "specialized_template", "specialized_template_or_partial")
    RECORD_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    SPECIALIZED_TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    SPECIALIZED_TEMPLATE_OR_PARTIAL_FIELD_NUMBER: _ClassVar[int]
    record: RecordDeclInfo
    template_arguments: _containers.RepeatedCompositeFieldContainer[TemplateArgument]
    template_parameters: TemplateParameterList
    specialized_template: DeclarationSymbol
    specialized_template_or_partial: DeclarationSymbol
    def __init__(self, record: _Optional[_Union[RecordDeclInfo, _Mapping]] = ..., template_arguments: _Optional[_Iterable[_Union[TemplateArgument, _Mapping]]] = ..., template_parameters: _Optional[_Union[TemplateParameterList, _Mapping]] = ..., specialized_template: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., specialized_template_or_partial: _Optional[_Union[DeclarationSymbol, _Mapping]] = ...) -> None: ...

class EnumDecl(_message.Message):
    __slots__ = ("tag", "integer_type", "promotion_type", "is_scoped", "is_fixed")
    TAG_FIELD_NUMBER: _ClassVar[int]
    INTEGER_TYPE_FIELD_NUMBER: _ClassVar[int]
    PROMOTION_TYPE_FIELD_NUMBER: _ClassVar[int]
    IS_SCOPED_FIELD_NUMBER: _ClassVar[int]
    IS_FIXED_FIELD_NUMBER: _ClassVar[int]
    tag: TagDeclInfo
    integer_type: QualType
    promotion_type: QualType
    is_scoped: bool
    is_fixed: bool
    def __init__(self, tag: _Optional[_Union[TagDeclInfo, _Mapping]] = ..., integer_type: _Optional[_Union[QualType, _Mapping]] = ..., promotion_type: _Optional[_Union[QualType, _Mapping]] = ..., is_scoped: _Optional[bool] = ..., is_fixed: _Optional[bool] = ...) -> None: ...

class UnresolvedUsingTypenameDecl(_message.Message):
    __slots__ = ("type_declaration", "qualifier", "target_name")
    TYPE_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    TARGET_NAME_FIELD_NUMBER: _ClassVar[int]
    type_declaration: TypeDeclInfo
    qualifier: NestedNameSpecifier
    target_name: DeclarationName
    def __init__(self, type_declaration: _Optional[_Union[TypeDeclInfo, _Mapping]] = ..., qualifier: _Optional[_Union[NestedNameSpecifier, _Mapping]] = ..., target_name: _Optional[_Union[DeclarationName, _Mapping]] = ...) -> None: ...

class TypedefDecl(_message.Message):
    __slots__ = ("type_declaration", "underlying_type")
    TYPE_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    UNDERLYING_TYPE_FIELD_NUMBER: _ClassVar[int]
    type_declaration: TypeDeclInfo
    underlying_type: QualType
    def __init__(self, type_declaration: _Optional[_Union[TypeDeclInfo, _Mapping]] = ..., underlying_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class TypeAliasDecl(_message.Message):
    __slots__ = ("type_declaration", "underlying_type")
    TYPE_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    UNDERLYING_TYPE_FIELD_NUMBER: _ClassVar[int]
    type_declaration: TypeDeclInfo
    underlying_type: QualType
    def __init__(self, type_declaration: _Optional[_Union[TypeDeclInfo, _Mapping]] = ..., underlying_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class TemplateTypeParmDecl(_message.Message):
    __slots__ = ("type_declaration", "depth", "position", "is_parameter_pack", "default_argument", "default_argument_was_inherited", "type_constraint", "is_pack_expansion")
    TYPE_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    DEPTH_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    IS_PARAMETER_PACK_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_ARGUMENT_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_ARGUMENT_WAS_INHERITED_FIELD_NUMBER: _ClassVar[int]
    TYPE_CONSTRAINT_FIELD_NUMBER: _ClassVar[int]
    IS_PACK_EXPANSION_FIELD_NUMBER: _ClassVar[int]
    type_declaration: TypeDeclInfo
    depth: int
    position: int
    is_parameter_pack: bool
    default_argument: TemplateArgument
    default_argument_was_inherited: bool
    type_constraint: TypeConstraint
    is_pack_expansion: bool
    def __init__(self, type_declaration: _Optional[_Union[TypeDeclInfo, _Mapping]] = ..., depth: _Optional[int] = ..., position: _Optional[int] = ..., is_parameter_pack: _Optional[bool] = ..., default_argument: _Optional[_Union[TemplateArgument, _Mapping]] = ..., default_argument_was_inherited: _Optional[bool] = ..., type_constraint: _Optional[_Union[TypeConstraint, _Mapping]] = ..., is_pack_expansion: _Optional[bool] = ...) -> None: ...

class TemplateTemplateParmDecl(_message.Message):
    __slots__ = ("named", "template_parameters", "depth", "position", "is_parameter_pack", "default_argument", "default_argument_was_inherited", "is_expanded_parameter_pack", "expanded_template_parameters")
    NAMED_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    DEPTH_FIELD_NUMBER: _ClassVar[int]
    POSITION_FIELD_NUMBER: _ClassVar[int]
    IS_PARAMETER_PACK_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_ARGUMENT_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_ARGUMENT_WAS_INHERITED_FIELD_NUMBER: _ClassVar[int]
    IS_EXPANDED_PARAMETER_PACK_FIELD_NUMBER: _ClassVar[int]
    EXPANDED_TEMPLATE_PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    named: NamedDeclInfo
    template_parameters: TemplateParameterList
    depth: int
    position: int
    is_parameter_pack: bool
    default_argument: TemplateArgument
    default_argument_was_inherited: bool
    is_expanded_parameter_pack: bool
    expanded_template_parameters: _containers.RepeatedCompositeFieldContainer[TemplateParameterList]
    def __init__(self, named: _Optional[_Union[NamedDeclInfo, _Mapping]] = ..., template_parameters: _Optional[_Union[TemplateParameterList, _Mapping]] = ..., depth: _Optional[int] = ..., position: _Optional[int] = ..., is_parameter_pack: _Optional[bool] = ..., default_argument: _Optional[_Union[TemplateArgument, _Mapping]] = ..., default_argument_was_inherited: _Optional[bool] = ..., is_expanded_parameter_pack: _Optional[bool] = ..., expanded_template_parameters: _Optional[_Iterable[_Union[TemplateParameterList, _Mapping]]] = ...) -> None: ...

class VarTemplateDecl(_message.Message):
    __slots__ = ("named", "templated_declaration", "template_parameters", "specializations")
    NAMED_FIELD_NUMBER: _ClassVar[int]
    TEMPLATED_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    SPECIALIZATIONS_FIELD_NUMBER: _ClassVar[int]
    named: NamedDeclInfo
    templated_declaration: DeclarationValue
    template_parameters: TemplateParameterList
    specializations: _containers.RepeatedCompositeFieldContainer[DeclarationSymbol]
    def __init__(self, named: _Optional[_Union[NamedDeclInfo, _Mapping]] = ..., templated_declaration: _Optional[_Union[DeclarationValue, _Mapping]] = ..., template_parameters: _Optional[_Union[TemplateParameterList, _Mapping]] = ..., specializations: _Optional[_Iterable[_Union[DeclarationSymbol, _Mapping]]] = ...) -> None: ...

class TypeAliasTemplateDecl(_message.Message):
    __slots__ = ("named", "templated_declaration", "template_parameters")
    NAMED_FIELD_NUMBER: _ClassVar[int]
    TEMPLATED_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    named: NamedDeclInfo
    templated_declaration: DeclarationValue
    template_parameters: TemplateParameterList
    def __init__(self, named: _Optional[_Union[NamedDeclInfo, _Mapping]] = ..., templated_declaration: _Optional[_Union[DeclarationValue, _Mapping]] = ..., template_parameters: _Optional[_Union[TemplateParameterList, _Mapping]] = ...) -> None: ...

class FunctionTemplateDecl(_message.Message):
    __slots__ = ("named", "templated_declaration", "template_parameters", "specializations")
    NAMED_FIELD_NUMBER: _ClassVar[int]
    TEMPLATED_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    SPECIALIZATIONS_FIELD_NUMBER: _ClassVar[int]
    named: NamedDeclInfo
    templated_declaration: DeclarationValue
    template_parameters: TemplateParameterList
    specializations: _containers.RepeatedCompositeFieldContainer[DeclarationSymbol]
    def __init__(self, named: _Optional[_Union[NamedDeclInfo, _Mapping]] = ..., templated_declaration: _Optional[_Union[DeclarationValue, _Mapping]] = ..., template_parameters: _Optional[_Union[TemplateParameterList, _Mapping]] = ..., specializations: _Optional[_Iterable[_Union[DeclarationSymbol, _Mapping]]] = ...) -> None: ...

class ClassTemplateDecl(_message.Message):
    __slots__ = ("named", "templated_declaration", "template_parameters", "specializations")
    NAMED_FIELD_NUMBER: _ClassVar[int]
    TEMPLATED_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    SPECIALIZATIONS_FIELD_NUMBER: _ClassVar[int]
    named: NamedDeclInfo
    templated_declaration: DeclarationValue
    template_parameters: TemplateParameterList
    specializations: _containers.RepeatedCompositeFieldContainer[DeclarationSymbol]
    def __init__(self, named: _Optional[_Union[NamedDeclInfo, _Mapping]] = ..., templated_declaration: _Optional[_Union[DeclarationValue, _Mapping]] = ..., template_parameters: _Optional[_Union[TemplateParameterList, _Mapping]] = ..., specializations: _Optional[_Iterable[_Union[DeclarationSymbol, _Mapping]]] = ...) -> None: ...

class ConceptDecl(_message.Message):
    __slots__ = ("named", "template_parameters", "constraint_expression", "is_type_concept", "has_definition")
    NAMED_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    CONSTRAINT_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    IS_TYPE_CONCEPT_FIELD_NUMBER: _ClassVar[int]
    HAS_DEFINITION_FIELD_NUMBER: _ClassVar[int]
    named: NamedDeclInfo
    template_parameters: TemplateParameterList
    constraint_expression: ExpressionValue
    is_type_concept: bool
    has_definition: bool
    def __init__(self, named: _Optional[_Union[NamedDeclInfo, _Mapping]] = ..., template_parameters: _Optional[_Union[TemplateParameterList, _Mapping]] = ..., constraint_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., is_type_concept: _Optional[bool] = ..., has_definition: _Optional[bool] = ...) -> None: ...

class BuiltinTemplateDecl(_message.Message):
    __slots__ = ("named", "builtin_kind", "template_parameters")
    NAMED_FIELD_NUMBER: _ClassVar[int]
    BUILTIN_KIND_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    named: NamedDeclInfo
    builtin_kind: DeclBuiltinTemplateKind
    template_parameters: TemplateParameterList
    def __init__(self, named: _Optional[_Union[NamedDeclInfo, _Mapping]] = ..., builtin_kind: _Optional[_Union[DeclBuiltinTemplateKind, str]] = ..., template_parameters: _Optional[_Union[TemplateParameterList, _Mapping]] = ...) -> None: ...

class NamespaceDecl(_message.Message):
    __slots__ = ("named", "original_namespace", "anonymous_namespace", "is_inline", "is_anonymous", "declarations")
    NAMED_FIELD_NUMBER: _ClassVar[int]
    ORIGINAL_NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    ANONYMOUS_NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    IS_INLINE_FIELD_NUMBER: _ClassVar[int]
    IS_ANONYMOUS_FIELD_NUMBER: _ClassVar[int]
    DECLARATIONS_FIELD_NUMBER: _ClassVar[int]
    named: NamedDeclInfo
    original_namespace: DeclarationSymbol
    anonymous_namespace: DeclarationSymbol
    is_inline: bool
    is_anonymous: bool
    declarations: _containers.RepeatedCompositeFieldContainer[DeclarationValue]
    def __init__(self, named: _Optional[_Union[NamedDeclInfo, _Mapping]] = ..., original_namespace: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., anonymous_namespace: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., is_inline: _Optional[bool] = ..., is_anonymous: _Optional[bool] = ..., declarations: _Optional[_Iterable[_Union[DeclarationValue, _Mapping]]] = ...) -> None: ...

class NamespaceAliasDecl(_message.Message):
    __slots__ = ("named", "namespace_declaration", "aliased_namespace", "qualifier")
    NAMED_FIELD_NUMBER: _ClassVar[int]
    NAMESPACE_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    ALIASED_NAMESPACE_FIELD_NUMBER: _ClassVar[int]
    QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    named: NamedDeclInfo
    namespace_declaration: DeclarationSymbol
    aliased_namespace: DeclarationSymbol
    qualifier: NestedNameSpecifier
    def __init__(self, named: _Optional[_Union[NamedDeclInfo, _Mapping]] = ..., namespace_declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., aliased_namespace: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., qualifier: _Optional[_Union[NestedNameSpecifier, _Mapping]] = ...) -> None: ...

class LabelDecl(_message.Message):
    __slots__ = ("named", "statement", "is_gnu_local")
    NAMED_FIELD_NUMBER: _ClassVar[int]
    STATEMENT_FIELD_NUMBER: _ClassVar[int]
    IS_GNU_LOCAL_FIELD_NUMBER: _ClassVar[int]
    named: NamedDeclInfo
    statement: StatementValue
    is_gnu_local: bool
    def __init__(self, named: _Optional[_Union[NamedDeclInfo, _Mapping]] = ..., statement: _Optional[_Union[StatementValue, _Mapping]] = ..., is_gnu_local: _Optional[bool] = ...) -> None: ...

class UsingEnumDecl(_message.Message):
    __slots__ = ("named", "enum_declaration")
    NAMED_FIELD_NUMBER: _ClassVar[int]
    ENUM_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    named: NamedDeclInfo
    enum_declaration: DeclarationSymbol
    def __init__(self, named: _Optional[_Union[NamedDeclInfo, _Mapping]] = ..., enum_declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ...) -> None: ...

class UsingDecl(_message.Message):
    __slots__ = ("named", "qualifier", "name", "shadows", "is_access_declaration", "has_typename")
    NAMED_FIELD_NUMBER: _ClassVar[int]
    QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    SHADOWS_FIELD_NUMBER: _ClassVar[int]
    IS_ACCESS_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    HAS_TYPENAME_FIELD_NUMBER: _ClassVar[int]
    named: NamedDeclInfo
    qualifier: NestedNameSpecifier
    name: DeclarationName
    shadows: _containers.RepeatedCompositeFieldContainer[DeclarationSymbol]
    is_access_declaration: bool
    has_typename: bool
    def __init__(self, named: _Optional[_Union[NamedDeclInfo, _Mapping]] = ..., qualifier: _Optional[_Union[NestedNameSpecifier, _Mapping]] = ..., name: _Optional[_Union[DeclarationName, _Mapping]] = ..., shadows: _Optional[_Iterable[_Union[DeclarationSymbol, _Mapping]]] = ..., is_access_declaration: _Optional[bool] = ..., has_typename: _Optional[bool] = ...) -> None: ...

class LifetimeExtendedTemporaryDecl(_message.Message):
    __slots__ = ("declaration", "extending_declaration", "temporary_expression", "mangling_number")
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    EXTENDING_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    TEMPORARY_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    MANGLING_NUMBER_FIELD_NUMBER: _ClassVar[int]
    declaration: DeclInfo
    extending_declaration: DeclarationSymbol
    temporary_expression: ExpressionValue
    mangling_number: int
    def __init__(self, declaration: _Optional[_Union[DeclInfo, _Mapping]] = ..., extending_declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., temporary_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., mangling_number: _Optional[int] = ...) -> None: ...

class ImportDecl(_message.Message):
    __slots__ = ("declaration", "imported_module_name")
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    IMPORTED_MODULE_NAME_FIELD_NUMBER: _ClassVar[int]
    declaration: DeclInfo
    imported_module_name: str
    def __init__(self, declaration: _Optional[_Union[DeclInfo, _Mapping]] = ..., imported_module_name: _Optional[str] = ...) -> None: ...

class ImplicitConceptSpecializationDecl(_message.Message):
    __slots__ = ("declaration", "template_arguments")
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    declaration: DeclInfo
    template_arguments: _containers.RepeatedCompositeFieldContainer[TemplateArgument]
    def __init__(self, declaration: _Optional[_Union[DeclInfo, _Mapping]] = ..., template_arguments: _Optional[_Iterable[_Union[TemplateArgument, _Mapping]]] = ...) -> None: ...

class FriendTemplateDecl(_message.Message):
    __slots__ = ("declaration", "template_parameters", "friend_declaration", "is_described_template", "friend_type")
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_PARAMETERS_FIELD_NUMBER: _ClassVar[int]
    FRIEND_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    IS_DESCRIBED_TEMPLATE_FIELD_NUMBER: _ClassVar[int]
    FRIEND_TYPE_FIELD_NUMBER: _ClassVar[int]
    declaration: DeclInfo
    template_parameters: _containers.RepeatedCompositeFieldContainer[TemplateParameterList]
    friend_declaration: DeclarationSymbol
    is_described_template: bool
    friend_type: QualType
    def __init__(self, declaration: _Optional[_Union[DeclInfo, _Mapping]] = ..., template_parameters: _Optional[_Iterable[_Union[TemplateParameterList, _Mapping]]] = ..., friend_declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., is_described_template: _Optional[bool] = ..., friend_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class FriendDecl(_message.Message):
    __slots__ = ("declaration", "friend_declaration", "friend_type", "is_pack_expansion")
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    FRIEND_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    FRIEND_TYPE_FIELD_NUMBER: _ClassVar[int]
    IS_PACK_EXPANSION_FIELD_NUMBER: _ClassVar[int]
    declaration: DeclInfo
    friend_declaration: DeclarationSymbol
    friend_type: QualType
    is_pack_expansion: bool
    def __init__(self, declaration: _Optional[_Union[DeclInfo, _Mapping]] = ..., friend_declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., friend_type: _Optional[_Union[QualType, _Mapping]] = ..., is_pack_expansion: _Optional[bool] = ...) -> None: ...

class FileScopeAsmDecl(_message.Message):
    __slots__ = ("declaration", "assembly_string")
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    ASSEMBLY_STRING_FIELD_NUMBER: _ClassVar[int]
    declaration: DeclInfo
    assembly_string: ExpressionValue
    def __init__(self, declaration: _Optional[_Union[DeclInfo, _Mapping]] = ..., assembly_string: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class EmptyDecl(_message.Message):
    __slots__ = ("declaration",)
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    declaration: DeclInfo
    def __init__(self, declaration: _Optional[_Union[DeclInfo, _Mapping]] = ...) -> None: ...

class AccessSpecDecl(_message.Message):
    __slots__ = ("declaration", "access")
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    ACCESS_FIELD_NUMBER: _ClassVar[int]
    declaration: DeclInfo
    access: _common_pb2.AccessSpecifier
    def __init__(self, declaration: _Optional[_Union[DeclInfo, _Mapping]] = ..., access: _Optional[_Union[_common_pb2.AccessSpecifier, str]] = ...) -> None: ...

class WhileStmt(_message.Message):
    __slots__ = ("condition_variable", "condition", "body", "is_constexpr", "is_condition_false")
    CONDITION_VARIABLE_FIELD_NUMBER: _ClassVar[int]
    CONDITION_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    IS_CONSTEXPR_FIELD_NUMBER: _ClassVar[int]
    IS_CONDITION_FALSE_FIELD_NUMBER: _ClassVar[int]
    condition_variable: DeclarationValue
    condition: ExpressionValue
    body: StatementValue
    is_constexpr: bool
    is_condition_false: bool
    def __init__(self, condition_variable: _Optional[_Union[DeclarationValue, _Mapping]] = ..., condition: _Optional[_Union[ExpressionValue, _Mapping]] = ..., body: _Optional[_Union[StatementValue, _Mapping]] = ..., is_constexpr: _Optional[bool] = ..., is_condition_false: _Optional[bool] = ...) -> None: ...

class LabelStmt(_message.Message):
    __slots__ = ("declaration", "substatement", "is_gnu_asm_label")
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    SUBSTATEMENT_FIELD_NUMBER: _ClassVar[int]
    IS_GNU_ASM_LABEL_FIELD_NUMBER: _ClassVar[int]
    declaration: DeclarationSymbol
    substatement: StatementValue
    is_gnu_asm_label: bool
    def __init__(self, declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., substatement: _Optional[_Union[StatementValue, _Mapping]] = ..., is_gnu_asm_label: _Optional[bool] = ...) -> None: ...

class VAArgExpr(_message.Message):
    __slots__ = ("info", "subexpression", "result_type")
    INFO_FIELD_NUMBER: _ClassVar[int]
    SUBEXPRESSION_FIELD_NUMBER: _ClassVar[int]
    RESULT_TYPE_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    subexpression: ExpressionValue
    result_type: QualType
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., subexpression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., result_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class UnaryOperator(_message.Message):
    __slots__ = ("info", "operand", "opcode", "is_postfix")
    INFO_FIELD_NUMBER: _ClassVar[int]
    OPERAND_FIELD_NUMBER: _ClassVar[int]
    OPCODE_FIELD_NUMBER: _ClassVar[int]
    IS_POSTFIX_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    operand: ExpressionValue
    opcode: _operators_pb2.UnaryOpcode
    is_postfix: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., operand: _Optional[_Union[ExpressionValue, _Mapping]] = ..., opcode: _Optional[_Union[_operators_pb2.UnaryOpcode, str]] = ..., is_postfix: _Optional[bool] = ...) -> None: ...

class UnaryExprOrTypeTraitExpr(_message.Message):
    __slots__ = ("info", "trait", "argument_expression", "argument_type", "is_type_argument")
    INFO_FIELD_NUMBER: _ClassVar[int]
    TRAIT_FIELD_NUMBER: _ClassVar[int]
    ARGUMENT_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    ARGUMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    IS_TYPE_ARGUMENT_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    trait: UnaryExprTrait
    argument_expression: ExpressionValue
    argument_type: QualType
    is_type_argument: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., trait: _Optional[_Union[UnaryExprTrait, str]] = ..., argument_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., argument_type: _Optional[_Union[QualType, _Mapping]] = ..., is_type_argument: _Optional[bool] = ...) -> None: ...

class TypeTraitExpr(_message.Message):
    __slots__ = ("info", "trait", "queried_types", "trait_value", "result_value", "trait_name")
    INFO_FIELD_NUMBER: _ClassVar[int]
    TRAIT_FIELD_NUMBER: _ClassVar[int]
    QUERIED_TYPES_FIELD_NUMBER: _ClassVar[int]
    TRAIT_VALUE_FIELD_NUMBER: _ClassVar[int]
    RESULT_VALUE_FIELD_NUMBER: _ClassVar[int]
    TRAIT_NAME_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    trait: TypeTrait
    queried_types: _containers.RepeatedCompositeFieldContainer[QualType]
    trait_value: bool
    result_value: APValue
    trait_name: str
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., trait: _Optional[_Union[TypeTrait, str]] = ..., queried_types: _Optional[_Iterable[_Union[QualType, _Mapping]]] = ..., trait_value: _Optional[bool] = ..., result_value: _Optional[_Union[APValue, _Mapping]] = ..., trait_name: _Optional[str] = ...) -> None: ...

class SubstNonTypeTemplateParmPackExpr(_message.Message):
    __slots__ = ("info", "parameter_pack", "arguments", "template_arguments")
    INFO_FIELD_NUMBER: _ClassVar[int]
    PARAMETER_PACK_FIELD_NUMBER: _ClassVar[int]
    ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    parameter_pack: DeclarationSymbol
    arguments: _containers.RepeatedCompositeFieldContainer[ExpressionValue]
    template_arguments: _containers.RepeatedCompositeFieldContainer[TemplateArgument]
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., parameter_pack: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., arguments: _Optional[_Iterable[_Union[ExpressionValue, _Mapping]]] = ..., template_arguments: _Optional[_Iterable[_Union[TemplateArgument, _Mapping]]] = ...) -> None: ...

class SubstNonTypeTemplateParmExpr(_message.Message):
    __slots__ = ("info", "parameter", "replacement", "parameter_index")
    INFO_FIELD_NUMBER: _ClassVar[int]
    PARAMETER_FIELD_NUMBER: _ClassVar[int]
    REPLACEMENT_FIELD_NUMBER: _ClassVar[int]
    PARAMETER_INDEX_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    parameter: DeclarationSymbol
    replacement: ExpressionValue
    parameter_index: int
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., parameter: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., replacement: _Optional[_Union[ExpressionValue, _Mapping]] = ..., parameter_index: _Optional[int] = ...) -> None: ...

class StringLiteral(_message.Message):
    __slots__ = ("info", "value", "code_unit_width", "literal_kind", "code_unit_count")
    INFO_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    CODE_UNIT_WIDTH_FIELD_NUMBER: _ClassVar[int]
    LITERAL_KIND_FIELD_NUMBER: _ClassVar[int]
    CODE_UNIT_COUNT_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    value: bytes
    code_unit_width: int
    literal_kind: StringLiteralKind
    code_unit_count: int
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., value: _Optional[bytes] = ..., code_unit_width: _Optional[int] = ..., literal_kind: _Optional[_Union[StringLiteralKind, str]] = ..., code_unit_count: _Optional[int] = ...) -> None: ...

class StmtExpr(_message.Message):
    __slots__ = ("info", "compound_statement")
    INFO_FIELD_NUMBER: _ClassVar[int]
    COMPOUND_STATEMENT_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    compound_statement: StatementValue
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., compound_statement: _Optional[_Union[StatementValue, _Mapping]] = ...) -> None: ...

class SourceLocExpr(_message.Message):
    __slots__ = ("info", "parent_context", "kind", "builtin_name")
    INFO_FIELD_NUMBER: _ClassVar[int]
    PARENT_CONTEXT_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    BUILTIN_NAME_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    parent_context: DeclarationSymbol
    kind: SourceLocExprKind
    builtin_name: str
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., parent_context: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., kind: _Optional[_Union[SourceLocExprKind, str]] = ..., builtin_name: _Optional[str] = ...) -> None: ...

class SizeOfPackExpr(_message.Message):
    __slots__ = ("info", "pack_declaration", "pack_size")
    INFO_FIELD_NUMBER: _ClassVar[int]
    PACK_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    PACK_SIZE_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    pack_declaration: DeclarationSymbol
    pack_size: int
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., pack_declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., pack_size: _Optional[int] = ...) -> None: ...

class ShuffleVectorExpr(_message.Message):
    __slots__ = ("info", "arguments", "shuffle_mask", "signed_shuffle_mask")
    INFO_FIELD_NUMBER: _ClassVar[int]
    ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    SHUFFLE_MASK_FIELD_NUMBER: _ClassVar[int]
    SIGNED_SHUFFLE_MASK_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    arguments: _containers.RepeatedCompositeFieldContainer[ExpressionValue]
    shuffle_mask: _containers.RepeatedScalarFieldContainer[int]
    signed_shuffle_mask: _containers.RepeatedScalarFieldContainer[int]
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., arguments: _Optional[_Iterable[_Union[ExpressionValue, _Mapping]]] = ..., shuffle_mask: _Optional[_Iterable[int]] = ..., signed_shuffle_mask: _Optional[_Iterable[int]] = ...) -> None: ...

class RequiresExpr(_message.Message):
    __slots__ = ("info", "body_declaration", "requirements", "is_satisfied")
    INFO_FIELD_NUMBER: _ClassVar[int]
    BODY_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    REQUIREMENTS_FIELD_NUMBER: _ClassVar[int]
    IS_SATISFIED_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    body_declaration: DeclarationValue
    requirements: _containers.RepeatedCompositeFieldContainer[ConceptRequirement]
    is_satisfied: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., body_declaration: _Optional[_Union[DeclarationValue, _Mapping]] = ..., requirements: _Optional[_Iterable[_Union[ConceptRequirement, _Mapping]]] = ..., is_satisfied: _Optional[bool] = ...) -> None: ...

class RecoveryExpr(_message.Message):
    __slots__ = ("info", "subexpressions", "candidate_declarations", "is_overloaded")
    INFO_FIELD_NUMBER: _ClassVar[int]
    SUBEXPRESSIONS_FIELD_NUMBER: _ClassVar[int]
    CANDIDATE_DECLARATIONS_FIELD_NUMBER: _ClassVar[int]
    IS_OVERLOADED_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    subexpressions: _containers.RepeatedCompositeFieldContainer[ExpressionValue]
    candidate_declarations: _containers.RepeatedCompositeFieldContainer[DeclarationSymbol]
    is_overloaded: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., subexpressions: _Optional[_Iterable[_Union[ExpressionValue, _Mapping]]] = ..., candidate_declarations: _Optional[_Iterable[_Union[DeclarationSymbol, _Mapping]]] = ..., is_overloaded: _Optional[bool] = ...) -> None: ...

class PseudoObjectExpr(_message.Message):
    __slots__ = ("info", "syntax_expression", "semantic_expressions", "result_expression")
    INFO_FIELD_NUMBER: _ClassVar[int]
    SYNTAX_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    SEMANTIC_EXPRESSIONS_FIELD_NUMBER: _ClassVar[int]
    RESULT_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    syntax_expression: ExpressionValue
    semantic_expressions: _containers.RepeatedCompositeFieldContainer[ExpressionValue]
    result_expression: ExpressionValue
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., syntax_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., semantic_expressions: _Optional[_Iterable[_Union[ExpressionValue, _Mapping]]] = ..., result_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class PredefinedExpr(_message.Message):
    __slots__ = ("info", "identifier_kind", "literal_bytes")
    INFO_FIELD_NUMBER: _ClassVar[int]
    IDENTIFIER_KIND_FIELD_NUMBER: _ClassVar[int]
    LITERAL_BYTES_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    identifier_kind: PredefinedIdentKind
    literal_bytes: bytes
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., identifier_kind: _Optional[_Union[PredefinedIdentKind, str]] = ..., literal_bytes: _Optional[bytes] = ...) -> None: ...

class ParenListExpr(_message.Message):
    __slots__ = ("info", "expressions")
    INFO_FIELD_NUMBER: _ClassVar[int]
    EXPRESSIONS_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    expressions: _containers.RepeatedCompositeFieldContainer[ExpressionValue]
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., expressions: _Optional[_Iterable[_Union[ExpressionValue, _Mapping]]] = ...) -> None: ...

class ParenExpr(_message.Message):
    __slots__ = ("info", "subexpression")
    INFO_FIELD_NUMBER: _ClassVar[int]
    SUBEXPRESSION_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    subexpression: ExpressionValue
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., subexpression: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class PackIndexingExpr(_message.Message):
    __slots__ = ("info", "pack_expression", "pack_declaration", "index_expression", "selected_index", "selected_expression", "substituted_expressions", "is_fully_substituted")
    INFO_FIELD_NUMBER: _ClassVar[int]
    PACK_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    PACK_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    INDEX_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    SELECTED_INDEX_FIELD_NUMBER: _ClassVar[int]
    SELECTED_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    SUBSTITUTED_EXPRESSIONS_FIELD_NUMBER: _ClassVar[int]
    IS_FULLY_SUBSTITUTED_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    pack_expression: ExpressionValue
    pack_declaration: DeclarationSymbol
    index_expression: ExpressionValue
    selected_index: int
    selected_expression: ExpressionValue
    substituted_expressions: _containers.RepeatedCompositeFieldContainer[ExpressionValue]
    is_fully_substituted: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., pack_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., pack_declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., index_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., selected_index: _Optional[int] = ..., selected_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., substituted_expressions: _Optional[_Iterable[_Union[ExpressionValue, _Mapping]]] = ..., is_fully_substituted: _Optional[bool] = ...) -> None: ...

class PackExpansionExpr(_message.Message):
    __slots__ = ("info", "pattern", "num_expansions")
    INFO_FIELD_NUMBER: _ClassVar[int]
    PATTERN_FIELD_NUMBER: _ClassVar[int]
    NUM_EXPANSIONS_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    pattern: ExpressionValue
    num_expansions: int
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., pattern: _Optional[_Union[ExpressionValue, _Mapping]] = ..., num_expansions: _Optional[int] = ...) -> None: ...

class UnresolvedMemberExpr(_message.Message):
    __slots__ = ("info", "base", "name", "qualifier", "candidate_declarations", "is_arrow", "is_unqualified", "template_arguments")
    INFO_FIELD_NUMBER: _ClassVar[int]
    BASE_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    CANDIDATE_DECLARATIONS_FIELD_NUMBER: _ClassVar[int]
    IS_ARROW_FIELD_NUMBER: _ClassVar[int]
    IS_UNQUALIFIED_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    base: ExpressionValue
    name: DeclarationName
    qualifier: NestedNameSpecifier
    candidate_declarations: _containers.RepeatedCompositeFieldContainer[DeclarationSymbol]
    is_arrow: bool
    is_unqualified: bool
    template_arguments: _containers.RepeatedCompositeFieldContainer[TemplateArgument]
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., base: _Optional[_Union[ExpressionValue, _Mapping]] = ..., name: _Optional[_Union[DeclarationName, _Mapping]] = ..., qualifier: _Optional[_Union[NestedNameSpecifier, _Mapping]] = ..., candidate_declarations: _Optional[_Iterable[_Union[DeclarationSymbol, _Mapping]]] = ..., is_arrow: _Optional[bool] = ..., is_unqualified: _Optional[bool] = ..., template_arguments: _Optional[_Iterable[_Union[TemplateArgument, _Mapping]]] = ...) -> None: ...

class UnresolvedLookupExpr(_message.Message):
    __slots__ = ("info", "name", "qualifier", "candidate_declarations", "requires_adl", "template_arguments")
    INFO_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    CANDIDATE_DECLARATIONS_FIELD_NUMBER: _ClassVar[int]
    REQUIRES_ADL_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    name: DeclarationName
    qualifier: NestedNameSpecifier
    candidate_declarations: _containers.RepeatedCompositeFieldContainer[DeclarationSymbol]
    requires_adl: bool
    template_arguments: _containers.RepeatedCompositeFieldContainer[TemplateArgument]
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., name: _Optional[_Union[DeclarationName, _Mapping]] = ..., qualifier: _Optional[_Union[NestedNameSpecifier, _Mapping]] = ..., candidate_declarations: _Optional[_Iterable[_Union[DeclarationSymbol, _Mapping]]] = ..., requires_adl: _Optional[bool] = ..., template_arguments: _Optional[_Iterable[_Union[TemplateArgument, _Mapping]]] = ...) -> None: ...

class OpaqueValueExpr(_message.Message):
    __slots__ = ("info", "source_expression", "opaque_type")
    INFO_FIELD_NUMBER: _ClassVar[int]
    SOURCE_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    OPAQUE_TYPE_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    source_expression: ExpressionValue
    opaque_type: QualType
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., source_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., opaque_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class OffsetOfExpr(_message.Message):
    __slots__ = ("info", "queried_type", "components", "byte_offset")
    INFO_FIELD_NUMBER: _ClassVar[int]
    QUERIED_TYPE_FIELD_NUMBER: _ClassVar[int]
    COMPONENTS_FIELD_NUMBER: _ClassVar[int]
    BYTE_OFFSET_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    queried_type: QualType
    components: _containers.RepeatedCompositeFieldContainer[OffsetOfComponent]
    byte_offset: APIntBits
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., queried_type: _Optional[_Union[QualType, _Mapping]] = ..., components: _Optional[_Iterable[_Union[OffsetOfComponent, _Mapping]]] = ..., byte_offset: _Optional[_Union[APIntBits, _Mapping]] = ...) -> None: ...

class NoInitExpr(_message.Message):
    __slots__ = ("info", "uninitialized_type")
    INFO_FIELD_NUMBER: _ClassVar[int]
    UNINITIALIZED_TYPE_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    uninitialized_type: QualType
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., uninitialized_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class MemberExpr(_message.Message):
    __slots__ = ("info", "base", "member_declaration", "member_name", "qualifier", "is_arrow", "is_virtual_call", "template_arguments")
    INFO_FIELD_NUMBER: _ClassVar[int]
    BASE_FIELD_NUMBER: _ClassVar[int]
    MEMBER_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    MEMBER_NAME_FIELD_NUMBER: _ClassVar[int]
    QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    IS_ARROW_FIELD_NUMBER: _ClassVar[int]
    IS_VIRTUAL_CALL_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    base: ExpressionValue
    member_declaration: DeclarationSymbol
    member_name: DeclarationName
    qualifier: NestedNameSpecifier
    is_arrow: bool
    is_virtual_call: bool
    template_arguments: _containers.RepeatedCompositeFieldContainer[TemplateArgument]
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., base: _Optional[_Union[ExpressionValue, _Mapping]] = ..., member_declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., member_name: _Optional[_Union[DeclarationName, _Mapping]] = ..., qualifier: _Optional[_Union[NestedNameSpecifier, _Mapping]] = ..., is_arrow: _Optional[bool] = ..., is_virtual_call: _Optional[bool] = ..., template_arguments: _Optional[_Iterable[_Union[TemplateArgument, _Mapping]]] = ...) -> None: ...

class MatrixSubscriptExpr(_message.Message):
    __slots__ = ("info", "base", "row_index", "column_index")
    INFO_FIELD_NUMBER: _ClassVar[int]
    BASE_FIELD_NUMBER: _ClassVar[int]
    ROW_INDEX_FIELD_NUMBER: _ClassVar[int]
    COLUMN_INDEX_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    base: ExpressionValue
    row_index: ExpressionValue
    column_index: ExpressionValue
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., base: _Optional[_Union[ExpressionValue, _Mapping]] = ..., row_index: _Optional[_Union[ExpressionValue, _Mapping]] = ..., column_index: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class MatrixSingleSubscriptExpr(_message.Message):
    __slots__ = ("info", "base", "row_index")
    INFO_FIELD_NUMBER: _ClassVar[int]
    BASE_FIELD_NUMBER: _ClassVar[int]
    ROW_INDEX_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    base: ExpressionValue
    row_index: ExpressionValue
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., base: _Optional[_Union[ExpressionValue, _Mapping]] = ..., row_index: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class MaterializeTemporaryExpr(_message.Message):
    __slots__ = ("info", "subexpression", "extending_declaration", "bound_to_lvalue_rank")
    INFO_FIELD_NUMBER: _ClassVar[int]
    SUBEXPRESSION_FIELD_NUMBER: _ClassVar[int]
    EXTENDING_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    BOUND_TO_LVALUE_RANK_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    subexpression: ExpressionValue
    extending_declaration: DeclarationSymbol
    bound_to_lvalue_rank: int
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., subexpression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., extending_declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., bound_to_lvalue_rank: _Optional[int] = ...) -> None: ...

class MSPropertySubscriptExpr(_message.Message):
    __slots__ = ("info", "base", "index")
    INFO_FIELD_NUMBER: _ClassVar[int]
    BASE_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    base: ExpressionValue
    index: ExpressionValue
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., base: _Optional[_Union[ExpressionValue, _Mapping]] = ..., index: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class MSPropertyRefExpr(_message.Message):
    __slots__ = ("info", "base", "property", "is_arrow")
    INFO_FIELD_NUMBER: _ClassVar[int]
    BASE_FIELD_NUMBER: _ClassVar[int]
    PROPERTY_FIELD_NUMBER: _ClassVar[int]
    IS_ARROW_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    base: ExpressionValue
    property: DeclarationSymbol
    is_arrow: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., base: _Optional[_Union[ExpressionValue, _Mapping]] = ..., property: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., is_arrow: _Optional[bool] = ...) -> None: ...

class LambdaExpr(_message.Message):
    __slots__ = ("info", "closure_class", "captures", "capture_initializers", "call_operator", "is_generic_lambda", "is_mutable")
    INFO_FIELD_NUMBER: _ClassVar[int]
    CLOSURE_CLASS_FIELD_NUMBER: _ClassVar[int]
    CAPTURES_FIELD_NUMBER: _ClassVar[int]
    CAPTURE_INITIALIZERS_FIELD_NUMBER: _ClassVar[int]
    CALL_OPERATOR_FIELD_NUMBER: _ClassVar[int]
    IS_GENERIC_LAMBDA_FIELD_NUMBER: _ClassVar[int]
    IS_MUTABLE_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    closure_class: DeclarationSymbol
    captures: _containers.RepeatedCompositeFieldContainer[LambdaCapture]
    capture_initializers: _containers.RepeatedCompositeFieldContainer[ExpressionValue]
    call_operator: DeclarationSymbol
    is_generic_lambda: bool
    is_mutable: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., closure_class: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., captures: _Optional[_Iterable[_Union[LambdaCapture, _Mapping]]] = ..., capture_initializers: _Optional[_Iterable[_Union[ExpressionValue, _Mapping]]] = ..., call_operator: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., is_generic_lambda: _Optional[bool] = ..., is_mutable: _Optional[bool] = ...) -> None: ...

class IntegerLiteral(_message.Message):
    __slots__ = ("info", "value")
    INFO_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    value: APIntBits
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., value: _Optional[_Union[APIntBits, _Mapping]] = ...) -> None: ...

class InitListExpr(_message.Message):
    __slots__ = ("info", "initializers", "syntactic_initializers", "array_filler", "is_union", "is_semantic_form")
    INFO_FIELD_NUMBER: _ClassVar[int]
    INITIALIZERS_FIELD_NUMBER: _ClassVar[int]
    SYNTACTIC_INITIALIZERS_FIELD_NUMBER: _ClassVar[int]
    ARRAY_FILLER_FIELD_NUMBER: _ClassVar[int]
    IS_UNION_FIELD_NUMBER: _ClassVar[int]
    IS_SEMANTIC_FORM_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    initializers: _containers.RepeatedCompositeFieldContainer[ExpressionValue]
    syntactic_initializers: _containers.RepeatedCompositeFieldContainer[ExpressionValue]
    array_filler: ExpressionValue
    is_union: bool
    is_semantic_form: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., initializers: _Optional[_Iterable[_Union[ExpressionValue, _Mapping]]] = ..., syntactic_initializers: _Optional[_Iterable[_Union[ExpressionValue, _Mapping]]] = ..., array_filler: _Optional[_Union[ExpressionValue, _Mapping]] = ..., is_union: _Optional[bool] = ..., is_semantic_form: _Optional[bool] = ...) -> None: ...

class ImplicitValueInitExpr(_message.Message):
    __slots__ = ("info", "initialized_type")
    INFO_FIELD_NUMBER: _ClassVar[int]
    INITIALIZED_TYPE_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    initialized_type: QualType
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., initialized_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class ImaginaryLiteral(_message.Message):
    __slots__ = ("info", "subexpression")
    INFO_FIELD_NUMBER: _ClassVar[int]
    SUBEXPRESSION_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    subexpression: ExpressionValue
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., subexpression: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class GenericSelectionExpr(_message.Message):
    __slots__ = ("info", "controlling_expression", "result_expression", "associations", "selected_index", "controlling_type")
    INFO_FIELD_NUMBER: _ClassVar[int]
    CONTROLLING_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    RESULT_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    ASSOCIATIONS_FIELD_NUMBER: _ClassVar[int]
    SELECTED_INDEX_FIELD_NUMBER: _ClassVar[int]
    CONTROLLING_TYPE_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    controlling_expression: ExpressionValue
    result_expression: ExpressionValue
    associations: _containers.RepeatedCompositeFieldContainer[GenericAssociation]
    selected_index: int
    controlling_type: QualType
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., controlling_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., result_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., associations: _Optional[_Iterable[_Union[GenericAssociation, _Mapping]]] = ..., selected_index: _Optional[int] = ..., controlling_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class GNUNullExpr(_message.Message):
    __slots__ = ("info", "is_gnu_null")
    INFO_FIELD_NUMBER: _ClassVar[int]
    IS_GNU_NULL_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    is_gnu_null: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., is_gnu_null: _Optional[bool] = ...) -> None: ...

class FunctionParmPackExpr(_message.Message):
    __slots__ = ("info", "parameter_pack", "expansions")
    INFO_FIELD_NUMBER: _ClassVar[int]
    PARAMETER_PACK_FIELD_NUMBER: _ClassVar[int]
    EXPANSIONS_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    parameter_pack: DeclarationSymbol
    expansions: _containers.RepeatedCompositeFieldContainer[DeclarationSymbol]
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., parameter_pack: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., expansions: _Optional[_Iterable[_Union[DeclarationSymbol, _Mapping]]] = ...) -> None: ...

class ExprWithCleanups(_message.Message):
    __slots__ = ("info", "subexpression", "cleanups")
    INFO_FIELD_NUMBER: _ClassVar[int]
    SUBEXPRESSION_FIELD_NUMBER: _ClassVar[int]
    CLEANUPS_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    subexpression: ExpressionValue
    cleanups: _containers.RepeatedCompositeFieldContainer[CleanupValue]
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., subexpression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., cleanups: _Optional[_Iterable[_Union[CleanupValue, _Mapping]]] = ...) -> None: ...

class ConstantExpr(_message.Message):
    __slots__ = ("info", "subexpression", "value", "result_kind")
    INFO_FIELD_NUMBER: _ClassVar[int]
    SUBEXPRESSION_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    RESULT_KIND_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    subexpression: ExpressionValue
    value: APValue
    result_kind: ConstantExprResult
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., subexpression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., value: _Optional[_Union[APValue, _Mapping]] = ..., result_kind: _Optional[_Union[ConstantExprResult, str]] = ...) -> None: ...

class FloatingLiteral(_message.Message):
    __slots__ = ("info", "value", "is_exact")
    INFO_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    IS_EXACT_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    value: APFloatBits
    is_exact: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., value: _Optional[_Union[APFloatBits, _Mapping]] = ..., is_exact: _Optional[bool] = ...) -> None: ...

class FixedPointLiteral(_message.Message):
    __slots__ = ("info", "scaled_value", "scale", "integer_bits")
    INFO_FIELD_NUMBER: _ClassVar[int]
    SCALED_VALUE_FIELD_NUMBER: _ClassVar[int]
    SCALE_FIELD_NUMBER: _ClassVar[int]
    INTEGER_BITS_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    scaled_value: APIntBits
    scale: int
    integer_bits: int
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., scaled_value: _Optional[_Union[APIntBits, _Mapping]] = ..., scale: _Optional[int] = ..., integer_bits: _Optional[int] = ...) -> None: ...

class ExtVectorElementExpr(_message.Message):
    __slots__ = ("info", "base", "accessor")
    INFO_FIELD_NUMBER: _ClassVar[int]
    BASE_FIELD_NUMBER: _ClassVar[int]
    ACCESSOR_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    base: ExpressionValue
    accessor: str
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., base: _Optional[_Union[ExpressionValue, _Mapping]] = ..., accessor: _Optional[str] = ...) -> None: ...

class ExpressionTraitExpr(_message.Message):
    __slots__ = ("info", "trait", "queried_expression", "trait_value")
    INFO_FIELD_NUMBER: _ClassVar[int]
    TRAIT_FIELD_NUMBER: _ClassVar[int]
    QUERIED_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    TRAIT_VALUE_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    trait: ExpressionTrait
    queried_expression: ExpressionValue
    trait_value: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., trait: _Optional[_Union[ExpressionTrait, str]] = ..., queried_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., trait_value: _Optional[bool] = ...) -> None: ...

class EmbedExpr(_message.Message):
    __slots__ = ("info", "file_name", "starting_element_position", "data_element_count", "data_string_literal")
    INFO_FIELD_NUMBER: _ClassVar[int]
    FILE_NAME_FIELD_NUMBER: _ClassVar[int]
    STARTING_ELEMENT_POSITION_FIELD_NUMBER: _ClassVar[int]
    DATA_ELEMENT_COUNT_FIELD_NUMBER: _ClassVar[int]
    DATA_STRING_LITERAL_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    file_name: str
    starting_element_position: int
    data_element_count: int
    data_string_literal: ExpressionValue
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., file_name: _Optional[str] = ..., starting_element_position: _Optional[int] = ..., data_element_count: _Optional[int] = ..., data_string_literal: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class DesignatedInitUpdateExpr(_message.Message):
    __slots__ = ("info", "base", "update_expression")
    INFO_FIELD_NUMBER: _ClassVar[int]
    BASE_FIELD_NUMBER: _ClassVar[int]
    UPDATE_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    base: ExpressionValue
    update_expression: ExpressionValue
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., base: _Optional[_Union[ExpressionValue, _Mapping]] = ..., update_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class DesignatedInitExpr(_message.Message):
    __slots__ = ("info", "initializer", "designators")
    INFO_FIELD_NUMBER: _ClassVar[int]
    INITIALIZER_FIELD_NUMBER: _ClassVar[int]
    DESIGNATORS_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    initializer: ExpressionValue
    designators: _containers.RepeatedCompositeFieldContainer[Designator]
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., initializer: _Optional[_Union[ExpressionValue, _Mapping]] = ..., designators: _Optional[_Iterable[_Union[Designator, _Mapping]]] = ...) -> None: ...

class DependentScopeDeclRefExpr(_message.Message):
    __slots__ = ("info", "qualifier", "name", "template_arguments")
    INFO_FIELD_NUMBER: _ClassVar[int]
    QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    qualifier: NestedNameSpecifier
    name: DeclarationName
    template_arguments: _containers.RepeatedCompositeFieldContainer[TemplateArgument]
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., qualifier: _Optional[_Union[NestedNameSpecifier, _Mapping]] = ..., name: _Optional[_Union[DeclarationName, _Mapping]] = ..., template_arguments: _Optional[_Iterable[_Union[TemplateArgument, _Mapping]]] = ...) -> None: ...

class DependentCoawaitExpr(_message.Message):
    __slots__ = ("info", "operand")
    INFO_FIELD_NUMBER: _ClassVar[int]
    OPERAND_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    operand: ExpressionValue
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., operand: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class DeclRefExpr(_message.Message):
    __slots__ = ("info", "declaration", "name", "qualifier", "is_non_odr_use", "has_explicit_template_arguments", "template_arguments")
    INFO_FIELD_NUMBER: _ClassVar[int]
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    NAME_FIELD_NUMBER: _ClassVar[int]
    QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    IS_NON_ODR_USE_FIELD_NUMBER: _ClassVar[int]
    HAS_EXPLICIT_TEMPLATE_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    declaration: DeclarationSymbol
    name: DeclarationName
    qualifier: NestedNameSpecifier
    is_non_odr_use: bool
    has_explicit_template_arguments: bool
    template_arguments: _containers.RepeatedCompositeFieldContainer[TemplateArgument]
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., name: _Optional[_Union[DeclarationName, _Mapping]] = ..., qualifier: _Optional[_Union[NestedNameSpecifier, _Mapping]] = ..., is_non_odr_use: _Optional[bool] = ..., has_explicit_template_arguments: _Optional[bool] = ..., template_arguments: _Optional[_Iterable[_Union[TemplateArgument, _Mapping]]] = ...) -> None: ...

class CoyieldExpr(_message.Message):
    __slots__ = ("info", "operand", "promise_call")
    INFO_FIELD_NUMBER: _ClassVar[int]
    OPERAND_FIELD_NUMBER: _ClassVar[int]
    PROMISE_CALL_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    operand: ExpressionValue
    promise_call: ExpressionValue
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., operand: _Optional[_Union[ExpressionValue, _Mapping]] = ..., promise_call: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class CoawaitExpr(_message.Message):
    __slots__ = ("info", "operand", "ready_call", "suspend_call", "resume_call", "is_ready")
    INFO_FIELD_NUMBER: _ClassVar[int]
    OPERAND_FIELD_NUMBER: _ClassVar[int]
    READY_CALL_FIELD_NUMBER: _ClassVar[int]
    SUSPEND_CALL_FIELD_NUMBER: _ClassVar[int]
    RESUME_CALL_FIELD_NUMBER: _ClassVar[int]
    IS_READY_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    operand: ExpressionValue
    ready_call: ExpressionValue
    suspend_call: ExpressionValue
    resume_call: ExpressionValue
    is_ready: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., operand: _Optional[_Union[ExpressionValue, _Mapping]] = ..., ready_call: _Optional[_Union[ExpressionValue, _Mapping]] = ..., suspend_call: _Optional[_Union[ExpressionValue, _Mapping]] = ..., resume_call: _Optional[_Union[ExpressionValue, _Mapping]] = ..., is_ready: _Optional[bool] = ...) -> None: ...

class ConvertVectorExpr(_message.Message):
    __slots__ = ("info", "operand", "destination_element_type")
    INFO_FIELD_NUMBER: _ClassVar[int]
    OPERAND_FIELD_NUMBER: _ClassVar[int]
    DESTINATION_ELEMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    operand: ExpressionValue
    destination_element_type: QualType
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., operand: _Optional[_Union[ExpressionValue, _Mapping]] = ..., destination_element_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class ConceptSpecializationExpr(_message.Message):
    __slots__ = ("info", "concept_reference", "template_arguments", "is_satisfied")
    INFO_FIELD_NUMBER: _ClassVar[int]
    CONCEPT_REFERENCE_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    IS_SATISFIED_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    concept_reference: ConceptReference
    template_arguments: _containers.RepeatedCompositeFieldContainer[TemplateArgument]
    is_satisfied: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., concept_reference: _Optional[_Union[ConceptReference, _Mapping]] = ..., template_arguments: _Optional[_Iterable[_Union[TemplateArgument, _Mapping]]] = ..., is_satisfied: _Optional[bool] = ...) -> None: ...

class CompoundLiteralExpr(_message.Message):
    __slots__ = ("info", "literal_type", "initializer", "is_file_scope")
    INFO_FIELD_NUMBER: _ClassVar[int]
    LITERAL_TYPE_FIELD_NUMBER: _ClassVar[int]
    INITIALIZER_FIELD_NUMBER: _ClassVar[int]
    IS_FILE_SCOPE_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    literal_type: QualType
    initializer: ExpressionValue
    is_file_scope: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., literal_type: _Optional[_Union[QualType, _Mapping]] = ..., initializer: _Optional[_Union[ExpressionValue, _Mapping]] = ..., is_file_scope: _Optional[bool] = ...) -> None: ...

class ChooseExpr(_message.Message):
    __slots__ = ("info", "condition", "left_expression", "right_expression", "is_condition_true")
    INFO_FIELD_NUMBER: _ClassVar[int]
    CONDITION_FIELD_NUMBER: _ClassVar[int]
    LEFT_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    RIGHT_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    IS_CONDITION_TRUE_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    condition: ExpressionValue
    left_expression: ExpressionValue
    right_expression: ExpressionValue
    is_condition_true: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., condition: _Optional[_Union[ExpressionValue, _Mapping]] = ..., left_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., right_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., is_condition_true: _Optional[bool] = ...) -> None: ...

class CharacterLiteral(_message.Message):
    __slots__ = ("info", "value", "character_kind")
    INFO_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    CHARACTER_KIND_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    value: int
    character_kind: CharacterKind
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., value: _Optional[int] = ..., character_kind: _Optional[_Union[CharacterKind, str]] = ...) -> None: ...

class ImplicitCastExpr(_message.Message):
    __slots__ = ("cast",)
    CAST_FIELD_NUMBER: _ClassVar[int]
    cast: CastExprInfo
    def __init__(self, cast: _Optional[_Union[CastExprInfo, _Mapping]] = ...) -> None: ...

class CXXStaticCastExpr(_message.Message):
    __slots__ = ("cast", "target_type")
    CAST_FIELD_NUMBER: _ClassVar[int]
    TARGET_TYPE_FIELD_NUMBER: _ClassVar[int]
    cast: CastExprInfo
    target_type: QualType
    def __init__(self, cast: _Optional[_Union[CastExprInfo, _Mapping]] = ..., target_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class CXXReinterpretCastExpr(_message.Message):
    __slots__ = ("cast", "target_type")
    CAST_FIELD_NUMBER: _ClassVar[int]
    TARGET_TYPE_FIELD_NUMBER: _ClassVar[int]
    cast: CastExprInfo
    target_type: QualType
    def __init__(self, cast: _Optional[_Union[CastExprInfo, _Mapping]] = ..., target_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class CXXDynamicCastExpr(_message.Message):
    __slots__ = ("cast", "target_type", "is_always_null", "is_always_success")
    CAST_FIELD_NUMBER: _ClassVar[int]
    TARGET_TYPE_FIELD_NUMBER: _ClassVar[int]
    IS_ALWAYS_NULL_FIELD_NUMBER: _ClassVar[int]
    IS_ALWAYS_SUCCESS_FIELD_NUMBER: _ClassVar[int]
    cast: CastExprInfo
    target_type: QualType
    is_always_null: bool
    is_always_success: bool
    def __init__(self, cast: _Optional[_Union[CastExprInfo, _Mapping]] = ..., target_type: _Optional[_Union[QualType, _Mapping]] = ..., is_always_null: _Optional[bool] = ..., is_always_success: _Optional[bool] = ...) -> None: ...

class CXXConstCastExpr(_message.Message):
    __slots__ = ("cast", "target_type")
    CAST_FIELD_NUMBER: _ClassVar[int]
    TARGET_TYPE_FIELD_NUMBER: _ClassVar[int]
    cast: CastExprInfo
    target_type: QualType
    def __init__(self, cast: _Optional[_Union[CastExprInfo, _Mapping]] = ..., target_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class CXXAddrspaceCastExpr(_message.Message):
    __slots__ = ("cast", "target_type")
    CAST_FIELD_NUMBER: _ClassVar[int]
    TARGET_TYPE_FIELD_NUMBER: _ClassVar[int]
    cast: CastExprInfo
    target_type: QualType
    def __init__(self, cast: _Optional[_Union[CastExprInfo, _Mapping]] = ..., target_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class CXXFunctionalCastExpr(_message.Message):
    __slots__ = ("cast", "target_type")
    CAST_FIELD_NUMBER: _ClassVar[int]
    TARGET_TYPE_FIELD_NUMBER: _ClassVar[int]
    cast: CastExprInfo
    target_type: QualType
    def __init__(self, cast: _Optional[_Union[CastExprInfo, _Mapping]] = ..., target_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class CStyleCastExpr(_message.Message):
    __slots__ = ("cast", "target_type")
    CAST_FIELD_NUMBER: _ClassVar[int]
    TARGET_TYPE_FIELD_NUMBER: _ClassVar[int]
    cast: CastExprInfo
    target_type: QualType
    def __init__(self, cast: _Optional[_Union[CastExprInfo, _Mapping]] = ..., target_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class BuiltinBitCastExpr(_message.Message):
    __slots__ = ("cast", "written_destination_type")
    CAST_FIELD_NUMBER: _ClassVar[int]
    WRITTEN_DESTINATION_TYPE_FIELD_NUMBER: _ClassVar[int]
    cast: CastExprInfo
    written_destination_type: QualType
    def __init__(self, cast: _Optional[_Union[CastExprInfo, _Mapping]] = ..., written_destination_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class CallExpr(_message.Message):
    __slots__ = ("call",)
    CALL_FIELD_NUMBER: _ClassVar[int]
    call: CallExprInfo
    def __init__(self, call: _Optional[_Union[CallExprInfo, _Mapping]] = ...) -> None: ...

class UserDefinedLiteral(_message.Message):
    __slots__ = ("call", "literal_suffix")
    CALL_FIELD_NUMBER: _ClassVar[int]
    LITERAL_SUFFIX_FIELD_NUMBER: _ClassVar[int]
    call: CallExprInfo
    literal_suffix: str
    def __init__(self, call: _Optional[_Union[CallExprInfo, _Mapping]] = ..., literal_suffix: _Optional[str] = ...) -> None: ...

class CXXOperatorCallExpr(_message.Message):
    __slots__ = ("call", "operator_kind")
    CALL_FIELD_NUMBER: _ClassVar[int]
    OPERATOR_KIND_FIELD_NUMBER: _ClassVar[int]
    call: CallExprInfo
    operator_kind: _operators_pb2.OverloadedOperatorKind
    def __init__(self, call: _Optional[_Union[CallExprInfo, _Mapping]] = ..., operator_kind: _Optional[_Union[_operators_pb2.OverloadedOperatorKind, str]] = ...) -> None: ...

class CXXMemberCallExpr(_message.Message):
    __slots__ = ("call", "implicit_object_argument", "object_type", "method_declaration", "record_declaration")
    CALL_FIELD_NUMBER: _ClassVar[int]
    IMPLICIT_OBJECT_ARGUMENT_FIELD_NUMBER: _ClassVar[int]
    OBJECT_TYPE_FIELD_NUMBER: _ClassVar[int]
    METHOD_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    RECORD_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    call: CallExprInfo
    implicit_object_argument: ExpressionValue
    object_type: QualType
    method_declaration: DeclarationSymbol
    record_declaration: DeclarationSymbol
    def __init__(self, call: _Optional[_Union[CallExprInfo, _Mapping]] = ..., implicit_object_argument: _Optional[_Union[ExpressionValue, _Mapping]] = ..., object_type: _Optional[_Union[QualType, _Mapping]] = ..., method_declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., record_declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ...) -> None: ...

class CXXUuidofExpr(_message.Message):
    __slots__ = ("info", "operand", "queried_type", "is_type_operand")
    INFO_FIELD_NUMBER: _ClassVar[int]
    OPERAND_FIELD_NUMBER: _ClassVar[int]
    QUERIED_TYPE_FIELD_NUMBER: _ClassVar[int]
    IS_TYPE_OPERAND_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    operand: ExpressionValue
    queried_type: QualType
    is_type_operand: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., operand: _Optional[_Union[ExpressionValue, _Mapping]] = ..., queried_type: _Optional[_Union[QualType, _Mapping]] = ..., is_type_operand: _Optional[bool] = ...) -> None: ...

class CXXUnresolvedConstructExpr(_message.Message):
    __slots__ = ("info", "constructed_type", "arguments")
    INFO_FIELD_NUMBER: _ClassVar[int]
    CONSTRUCTED_TYPE_FIELD_NUMBER: _ClassVar[int]
    ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    constructed_type: QualType
    arguments: _containers.RepeatedCompositeFieldContainer[ExpressionValue]
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., constructed_type: _Optional[_Union[QualType, _Mapping]] = ..., arguments: _Optional[_Iterable[_Union[ExpressionValue, _Mapping]]] = ...) -> None: ...

class CXXTypeidExpr(_message.Message):
    __slots__ = ("info", "operand", "queried_type", "is_type_operand")
    INFO_FIELD_NUMBER: _ClassVar[int]
    OPERAND_FIELD_NUMBER: _ClassVar[int]
    QUERIED_TYPE_FIELD_NUMBER: _ClassVar[int]
    IS_TYPE_OPERAND_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    operand: ExpressionValue
    queried_type: QualType
    is_type_operand: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., operand: _Optional[_Union[ExpressionValue, _Mapping]] = ..., queried_type: _Optional[_Union[QualType, _Mapping]] = ..., is_type_operand: _Optional[bool] = ...) -> None: ...

class CXXThrowExpr(_message.Message):
    __slots__ = ("info", "operand", "is_rethrow")
    INFO_FIELD_NUMBER: _ClassVar[int]
    OPERAND_FIELD_NUMBER: _ClassVar[int]
    IS_RETHROW_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    operand: ExpressionValue
    is_rethrow: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., operand: _Optional[_Union[ExpressionValue, _Mapping]] = ..., is_rethrow: _Optional[bool] = ...) -> None: ...

class CXXThisExpr(_message.Message):
    __slots__ = ("info", "is_implicit", "is_capture")
    INFO_FIELD_NUMBER: _ClassVar[int]
    IS_IMPLICIT_FIELD_NUMBER: _ClassVar[int]
    IS_CAPTURE_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    is_implicit: bool
    is_capture: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., is_implicit: _Optional[bool] = ..., is_capture: _Optional[bool] = ...) -> None: ...

class CXXStdInitializerListExpr(_message.Message):
    __slots__ = ("info", "subexpression")
    INFO_FIELD_NUMBER: _ClassVar[int]
    SUBEXPRESSION_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    subexpression: ExpressionValue
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., subexpression: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class CXXScalarValueInitExpr(_message.Message):
    __slots__ = ("info", "target_type")
    INFO_FIELD_NUMBER: _ClassVar[int]
    TARGET_TYPE_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    target_type: QualType
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., target_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class CXXRewrittenBinaryOperator(_message.Message):
    __slots__ = ("info", "syntactic_form", "semantic_form", "is_reversed")
    INFO_FIELD_NUMBER: _ClassVar[int]
    SYNTACTIC_FORM_FIELD_NUMBER: _ClassVar[int]
    SEMANTIC_FORM_FIELD_NUMBER: _ClassVar[int]
    IS_REVERSED_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    syntactic_form: ExpressionValue
    semantic_form: ExpressionValue
    is_reversed: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., syntactic_form: _Optional[_Union[ExpressionValue, _Mapping]] = ..., semantic_form: _Optional[_Union[ExpressionValue, _Mapping]] = ..., is_reversed: _Optional[bool] = ...) -> None: ...

class CXXPseudoDestructorExpr(_message.Message):
    __slots__ = ("info", "base", "qualifier", "destroyed_type", "is_arrow")
    INFO_FIELD_NUMBER: _ClassVar[int]
    BASE_FIELD_NUMBER: _ClassVar[int]
    QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    DESTROYED_TYPE_FIELD_NUMBER: _ClassVar[int]
    IS_ARROW_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    base: ExpressionValue
    qualifier: NestedNameSpecifier
    destroyed_type: QualType
    is_arrow: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., base: _Optional[_Union[ExpressionValue, _Mapping]] = ..., qualifier: _Optional[_Union[NestedNameSpecifier, _Mapping]] = ..., destroyed_type: _Optional[_Union[QualType, _Mapping]] = ..., is_arrow: _Optional[bool] = ...) -> None: ...

class CXXParenListInitExpr(_message.Message):
    __slots__ = ("info", "initializers", "array_filler_type")
    INFO_FIELD_NUMBER: _ClassVar[int]
    INITIALIZERS_FIELD_NUMBER: _ClassVar[int]
    ARRAY_FILLER_TYPE_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    initializers: _containers.RepeatedCompositeFieldContainer[ExpressionValue]
    array_filler_type: QualType
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., initializers: _Optional[_Iterable[_Union[ExpressionValue, _Mapping]]] = ..., array_filler_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class CXXNullPtrLiteralExpr(_message.Message):
    __slots__ = ("info", "is_null_pointer_constant")
    INFO_FIELD_NUMBER: _ClassVar[int]
    IS_NULL_POINTER_CONSTANT_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    is_null_pointer_constant: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., is_null_pointer_constant: _Optional[bool] = ...) -> None: ...

class CXXNoexceptExpr(_message.Message):
    __slots__ = ("info", "operand", "value", "is_value_dependent")
    INFO_FIELD_NUMBER: _ClassVar[int]
    OPERAND_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    IS_VALUE_DEPENDENT_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    operand: ExpressionValue
    value: bool
    is_value_dependent: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., operand: _Optional[_Union[ExpressionValue, _Mapping]] = ..., value: _Optional[bool] = ..., is_value_dependent: _Optional[bool] = ...) -> None: ...

class CXXNewExpr(_message.Message):
    __slots__ = ("info", "operator_new", "operator_delete", "allocated_type", "array_size", "initializer", "is_array", "is_global_new", "is_nothrow", "is_placement", "placement_arguments")
    INFO_FIELD_NUMBER: _ClassVar[int]
    OPERATOR_NEW_FIELD_NUMBER: _ClassVar[int]
    OPERATOR_DELETE_FIELD_NUMBER: _ClassVar[int]
    ALLOCATED_TYPE_FIELD_NUMBER: _ClassVar[int]
    ARRAY_SIZE_FIELD_NUMBER: _ClassVar[int]
    INITIALIZER_FIELD_NUMBER: _ClassVar[int]
    IS_ARRAY_FIELD_NUMBER: _ClassVar[int]
    IS_GLOBAL_NEW_FIELD_NUMBER: _ClassVar[int]
    IS_NOTHROW_FIELD_NUMBER: _ClassVar[int]
    IS_PLACEMENT_FIELD_NUMBER: _ClassVar[int]
    PLACEMENT_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    operator_new: DeclarationSymbol
    operator_delete: DeclarationSymbol
    allocated_type: QualType
    array_size: ExpressionValue
    initializer: ExpressionValue
    is_array: bool
    is_global_new: bool
    is_nothrow: bool
    is_placement: bool
    placement_arguments: _containers.RepeatedCompositeFieldContainer[ExpressionValue]
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., operator_new: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., operator_delete: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., allocated_type: _Optional[_Union[QualType, _Mapping]] = ..., array_size: _Optional[_Union[ExpressionValue, _Mapping]] = ..., initializer: _Optional[_Union[ExpressionValue, _Mapping]] = ..., is_array: _Optional[bool] = ..., is_global_new: _Optional[bool] = ..., is_nothrow: _Optional[bool] = ..., is_placement: _Optional[bool] = ..., placement_arguments: _Optional[_Iterable[_Union[ExpressionValue, _Mapping]]] = ...) -> None: ...

class CXXInheritedCtorInitExpr(_message.Message):
    __slots__ = ("info", "constructor", "constructing_constructor", "is_constructed_in_class")
    INFO_FIELD_NUMBER: _ClassVar[int]
    CONSTRUCTOR_FIELD_NUMBER: _ClassVar[int]
    CONSTRUCTING_CONSTRUCTOR_FIELD_NUMBER: _ClassVar[int]
    IS_CONSTRUCTED_IN_CLASS_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    constructor: DeclarationSymbol
    constructing_constructor: DeclarationSymbol
    is_constructed_in_class: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., constructor: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., constructing_constructor: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., is_constructed_in_class: _Optional[bool] = ...) -> None: ...

class CXXFoldExpr(_message.Message):
    __slots__ = ("info", "pattern", "left_operand", "right_operand", "operator_kind", "is_left_fold")
    INFO_FIELD_NUMBER: _ClassVar[int]
    PATTERN_FIELD_NUMBER: _ClassVar[int]
    LEFT_OPERAND_FIELD_NUMBER: _ClassVar[int]
    RIGHT_OPERAND_FIELD_NUMBER: _ClassVar[int]
    OPERATOR_KIND_FIELD_NUMBER: _ClassVar[int]
    IS_LEFT_FOLD_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    pattern: ExpressionValue
    left_operand: ExpressionValue
    right_operand: ExpressionValue
    operator_kind: _operators_pb2.BinaryOpcode
    is_left_fold: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., pattern: _Optional[_Union[ExpressionValue, _Mapping]] = ..., left_operand: _Optional[_Union[ExpressionValue, _Mapping]] = ..., right_operand: _Optional[_Union[ExpressionValue, _Mapping]] = ..., operator_kind: _Optional[_Union[_operators_pb2.BinaryOpcode, str]] = ..., is_left_fold: _Optional[bool] = ...) -> None: ...

class CXXDependentScopeMemberExpr(_message.Message):
    __slots__ = ("info", "base", "qualifier", "member_name", "is_arrow", "is_explicit_template_arguments", "template_arguments")
    INFO_FIELD_NUMBER: _ClassVar[int]
    BASE_FIELD_NUMBER: _ClassVar[int]
    QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    MEMBER_NAME_FIELD_NUMBER: _ClassVar[int]
    IS_ARROW_FIELD_NUMBER: _ClassVar[int]
    IS_EXPLICIT_TEMPLATE_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    base: ExpressionValue
    qualifier: NestedNameSpecifier
    member_name: DeclarationName
    is_arrow: bool
    is_explicit_template_arguments: bool
    template_arguments: _containers.RepeatedCompositeFieldContainer[TemplateArgument]
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., base: _Optional[_Union[ExpressionValue, _Mapping]] = ..., qualifier: _Optional[_Union[NestedNameSpecifier, _Mapping]] = ..., member_name: _Optional[_Union[DeclarationName, _Mapping]] = ..., is_arrow: _Optional[bool] = ..., is_explicit_template_arguments: _Optional[bool] = ..., template_arguments: _Optional[_Iterable[_Union[TemplateArgument, _Mapping]]] = ...) -> None: ...

class CXXDeleteExpr(_message.Message):
    __slots__ = ("info", "argument", "is_array_form", "is_global_delete", "operator_delete")
    INFO_FIELD_NUMBER: _ClassVar[int]
    ARGUMENT_FIELD_NUMBER: _ClassVar[int]
    IS_ARRAY_FORM_FIELD_NUMBER: _ClassVar[int]
    IS_GLOBAL_DELETE_FIELD_NUMBER: _ClassVar[int]
    OPERATOR_DELETE_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    argument: ExpressionValue
    is_array_form: bool
    is_global_delete: bool
    operator_delete: DeclarationSymbol
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., argument: _Optional[_Union[ExpressionValue, _Mapping]] = ..., is_array_form: _Optional[bool] = ..., is_global_delete: _Optional[bool] = ..., operator_delete: _Optional[_Union[DeclarationSymbol, _Mapping]] = ...) -> None: ...

class CXXDefaultInitExpr(_message.Message):
    __slots__ = ("info", "field", "expression")
    INFO_FIELD_NUMBER: _ClassVar[int]
    FIELD_FIELD_NUMBER: _ClassVar[int]
    EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    field: DeclarationSymbol
    expression: ExpressionValue
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., field: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., expression: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class CXXDefaultArgExpr(_message.Message):
    __slots__ = ("info", "parameter", "expression")
    INFO_FIELD_NUMBER: _ClassVar[int]
    PARAMETER_FIELD_NUMBER: _ClassVar[int]
    EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    parameter: DeclarationSymbol
    expression: ExpressionValue
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., parameter: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., expression: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class CXXConstructExpr(_message.Message):
    __slots__ = ("construction",)
    CONSTRUCTION_FIELD_NUMBER: _ClassVar[int]
    construction: CXXConstructExprInfo
    def __init__(self, construction: _Optional[_Union[CXXConstructExprInfo, _Mapping]] = ...) -> None: ...

class CXXTemporaryObjectExpr(_message.Message):
    __slots__ = ("construction", "target_type")
    CONSTRUCTION_FIELD_NUMBER: _ClassVar[int]
    TARGET_TYPE_FIELD_NUMBER: _ClassVar[int]
    construction: CXXConstructExprInfo
    target_type: QualType
    def __init__(self, construction: _Optional[_Union[CXXConstructExprInfo, _Mapping]] = ..., target_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class CXXBoolLiteralExpr(_message.Message):
    __slots__ = ("info", "value")
    INFO_FIELD_NUMBER: _ClassVar[int]
    VALUE_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    value: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., value: _Optional[bool] = ...) -> None: ...

class CXXBindTemporaryExpr(_message.Message):
    __slots__ = ("info", "subexpression", "temporary")
    INFO_FIELD_NUMBER: _ClassVar[int]
    SUBEXPRESSION_FIELD_NUMBER: _ClassVar[int]
    TEMPORARY_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    subexpression: ExpressionValue
    temporary: CXXTemporary
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., subexpression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., temporary: _Optional[_Union[CXXTemporary, _Mapping]] = ...) -> None: ...

class BlockExpr(_message.Message):
    __slots__ = ("info", "block_declaration")
    INFO_FIELD_NUMBER: _ClassVar[int]
    BLOCK_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    block_declaration: DeclarationValue
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., block_declaration: _Optional[_Union[DeclarationValue, _Mapping]] = ...) -> None: ...

class BinaryOperator(_message.Message):
    __slots__ = ("info", "left", "right", "opcode", "is_compound_assignment")
    INFO_FIELD_NUMBER: _ClassVar[int]
    LEFT_FIELD_NUMBER: _ClassVar[int]
    RIGHT_FIELD_NUMBER: _ClassVar[int]
    OPCODE_FIELD_NUMBER: _ClassVar[int]
    IS_COMPOUND_ASSIGNMENT_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    left: ExpressionValue
    right: ExpressionValue
    opcode: _operators_pb2.BinaryOpcode
    is_compound_assignment: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., left: _Optional[_Union[ExpressionValue, _Mapping]] = ..., right: _Optional[_Union[ExpressionValue, _Mapping]] = ..., opcode: _Optional[_Union[_operators_pb2.BinaryOpcode, str]] = ..., is_compound_assignment: _Optional[bool] = ...) -> None: ...

class CompoundAssignOperator(_message.Message):
    __slots__ = ("info", "left", "right", "opcode", "computation_lhs_type", "computation_result_type")
    INFO_FIELD_NUMBER: _ClassVar[int]
    LEFT_FIELD_NUMBER: _ClassVar[int]
    RIGHT_FIELD_NUMBER: _ClassVar[int]
    OPCODE_FIELD_NUMBER: _ClassVar[int]
    COMPUTATION_LHS_TYPE_FIELD_NUMBER: _ClassVar[int]
    COMPUTATION_RESULT_TYPE_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    left: ExpressionValue
    right: ExpressionValue
    opcode: _operators_pb2.BinaryOpcode
    computation_lhs_type: QualType
    computation_result_type: QualType
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., left: _Optional[_Union[ExpressionValue, _Mapping]] = ..., right: _Optional[_Union[ExpressionValue, _Mapping]] = ..., opcode: _Optional[_Union[_operators_pb2.BinaryOpcode, str]] = ..., computation_lhs_type: _Optional[_Union[QualType, _Mapping]] = ..., computation_result_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class AtomicExpr(_message.Message):
    __slots__ = ("info", "opcode", "arguments", "opcode_name")
    INFO_FIELD_NUMBER: _ClassVar[int]
    OPCODE_FIELD_NUMBER: _ClassVar[int]
    ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    OPCODE_NAME_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    opcode: AtomicOpcode
    arguments: _containers.RepeatedCompositeFieldContainer[ExpressionValue]
    opcode_name: str
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., opcode: _Optional[_Union[AtomicOpcode, str]] = ..., arguments: _Optional[_Iterable[_Union[ExpressionValue, _Mapping]]] = ..., opcode_name: _Optional[str] = ...) -> None: ...

class ArrayTypeTraitExpr(_message.Message):
    __slots__ = ("info", "trait", "queried_type", "dimension")
    INFO_FIELD_NUMBER: _ClassVar[int]
    TRAIT_FIELD_NUMBER: _ClassVar[int]
    QUERIED_TYPE_FIELD_NUMBER: _ClassVar[int]
    DIMENSION_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    trait: ArrayTypeTrait
    queried_type: QualType
    dimension: int
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., trait: _Optional[_Union[ArrayTypeTrait, str]] = ..., queried_type: _Optional[_Union[QualType, _Mapping]] = ..., dimension: _Optional[int] = ...) -> None: ...

class ArraySubscriptExpr(_message.Message):
    __slots__ = ("info", "base", "index")
    INFO_FIELD_NUMBER: _ClassVar[int]
    BASE_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    base: ExpressionValue
    index: ExpressionValue
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., base: _Optional[_Union[ExpressionValue, _Mapping]] = ..., index: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class ArrayInitLoopExpr(_message.Message):
    __slots__ = ("info", "common_expression", "initializer_per_element", "array_size")
    INFO_FIELD_NUMBER: _ClassVar[int]
    COMMON_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    INITIALIZER_PER_ELEMENT_FIELD_NUMBER: _ClassVar[int]
    ARRAY_SIZE_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    common_expression: ExpressionValue
    initializer_per_element: ExpressionValue
    array_size: APIntBits
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., common_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., initializer_per_element: _Optional[_Union[ExpressionValue, _Mapping]] = ..., array_size: _Optional[_Union[APIntBits, _Mapping]] = ...) -> None: ...

class ArrayInitIndexExpr(_message.Message):
    __slots__ = ("info", "is_array_init_index")
    INFO_FIELD_NUMBER: _ClassVar[int]
    IS_ARRAY_INIT_INDEX_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    is_array_init_index: bool
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., is_array_init_index: _Optional[bool] = ...) -> None: ...

class AddrLabelExpr(_message.Message):
    __slots__ = ("info", "label")
    INFO_FIELD_NUMBER: _ClassVar[int]
    LABEL_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    label: DeclarationSymbol
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., label: _Optional[_Union[DeclarationSymbol, _Mapping]] = ...) -> None: ...

class ConditionalOperator(_message.Message):
    __slots__ = ("info", "condition", "true_expression", "false_expression")
    INFO_FIELD_NUMBER: _ClassVar[int]
    CONDITION_FIELD_NUMBER: _ClassVar[int]
    TRUE_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    FALSE_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    condition: ExpressionValue
    true_expression: ExpressionValue
    false_expression: ExpressionValue
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., condition: _Optional[_Union[ExpressionValue, _Mapping]] = ..., true_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., false_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class BinaryConditionalOperator(_message.Message):
    __slots__ = ("info", "common", "condition", "true_expression", "false_expression")
    INFO_FIELD_NUMBER: _ClassVar[int]
    COMMON_FIELD_NUMBER: _ClassVar[int]
    CONDITION_FIELD_NUMBER: _ClassVar[int]
    TRUE_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    FALSE_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    info: ExprInfo
    common: ExpressionValue
    condition: ExpressionValue
    true_expression: ExpressionValue
    false_expression: ExpressionValue
    def __init__(self, info: _Optional[_Union[ExprInfo, _Mapping]] = ..., common: _Optional[_Union[ExpressionValue, _Mapping]] = ..., condition: _Optional[_Union[ExpressionValue, _Mapping]] = ..., true_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., false_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class AttributedStmt(_message.Message):
    __slots__ = ("attributes", "substatement")
    ATTRIBUTES_FIELD_NUMBER: _ClassVar[int]
    SUBSTATEMENT_FIELD_NUMBER: _ClassVar[int]
    attributes: _containers.RepeatedCompositeFieldContainer[AttributeValue]
    substatement: StatementValue
    def __init__(self, attributes: _Optional[_Iterable[_Union[AttributeValue, _Mapping]]] = ..., substatement: _Optional[_Union[StatementValue, _Mapping]] = ...) -> None: ...

class SwitchStmt(_message.Message):
    __slots__ = ("condition_variable", "condition", "body", "default_case", "is_constexpr", "is_all_enum_cases_covered")
    CONDITION_VARIABLE_FIELD_NUMBER: _ClassVar[int]
    CONDITION_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    DEFAULT_CASE_FIELD_NUMBER: _ClassVar[int]
    IS_CONSTEXPR_FIELD_NUMBER: _ClassVar[int]
    IS_ALL_ENUM_CASES_COVERED_FIELD_NUMBER: _ClassVar[int]
    condition_variable: DeclarationValue
    condition: ExpressionValue
    body: StatementValue
    default_case: StatementValue
    is_constexpr: bool
    is_all_enum_cases_covered: bool
    def __init__(self, condition_variable: _Optional[_Union[DeclarationValue, _Mapping]] = ..., condition: _Optional[_Union[ExpressionValue, _Mapping]] = ..., body: _Optional[_Union[StatementValue, _Mapping]] = ..., default_case: _Optional[_Union[StatementValue, _Mapping]] = ..., is_constexpr: _Optional[bool] = ..., is_all_enum_cases_covered: _Optional[bool] = ...) -> None: ...

class DefaultStmt(_message.Message):
    __slots__ = ("substatement",)
    SUBSTATEMENT_FIELD_NUMBER: _ClassVar[int]
    substatement: StatementValue
    def __init__(self, substatement: _Optional[_Union[StatementValue, _Mapping]] = ...) -> None: ...

class CaseStmt(_message.Message):
    __slots__ = ("left_expression", "right_expression", "substatement", "is_case_range")
    LEFT_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    RIGHT_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    SUBSTATEMENT_FIELD_NUMBER: _ClassVar[int]
    IS_CASE_RANGE_FIELD_NUMBER: _ClassVar[int]
    left_expression: ExpressionValue
    right_expression: ExpressionValue
    substatement: StatementValue
    is_case_range: bool
    def __init__(self, left_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., right_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., substatement: _Optional[_Union[StatementValue, _Mapping]] = ..., is_case_range: _Optional[bool] = ...) -> None: ...

class SEHTryStmt(_message.Message):
    __slots__ = ("try_block", "handler", "is_cxx_try")
    TRY_BLOCK_FIELD_NUMBER: _ClassVar[int]
    HANDLER_FIELD_NUMBER: _ClassVar[int]
    IS_CXX_TRY_FIELD_NUMBER: _ClassVar[int]
    try_block: StatementValue
    handler: StatementValue
    is_cxx_try: bool
    def __init__(self, try_block: _Optional[_Union[StatementValue, _Mapping]] = ..., handler: _Optional[_Union[StatementValue, _Mapping]] = ..., is_cxx_try: _Optional[bool] = ...) -> None: ...

class SEHLeaveStmt(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class SEHFinallyStmt(_message.Message):
    __slots__ = ("block",)
    BLOCK_FIELD_NUMBER: _ClassVar[int]
    block: StatementValue
    def __init__(self, block: _Optional[_Union[StatementValue, _Mapping]] = ...) -> None: ...

class SEHExceptStmt(_message.Message):
    __slots__ = ("filter_expression", "block")
    FILTER_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    BLOCK_FIELD_NUMBER: _ClassVar[int]
    filter_expression: ExpressionValue
    block: StatementValue
    def __init__(self, filter_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., block: _Optional[_Union[StatementValue, _Mapping]] = ...) -> None: ...

class ReturnStmt(_message.Message):
    __slots__ = ("return_value", "return_value_init", "nrvo_candidate", "is_noreturn")
    RETURN_VALUE_FIELD_NUMBER: _ClassVar[int]
    RETURN_VALUE_INIT_FIELD_NUMBER: _ClassVar[int]
    NRVO_CANDIDATE_FIELD_NUMBER: _ClassVar[int]
    IS_NORETURN_FIELD_NUMBER: _ClassVar[int]
    return_value: ExpressionValue
    return_value_init: ExpressionValue
    nrvo_candidate: DeclarationSymbol
    is_noreturn: bool
    def __init__(self, return_value: _Optional[_Union[ExpressionValue, _Mapping]] = ..., return_value_init: _Optional[_Union[ExpressionValue, _Mapping]] = ..., nrvo_candidate: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., is_noreturn: _Optional[bool] = ...) -> None: ...

class NullStmt(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class MSDependentExistsStmt(_message.Message):
    __slots__ = ("substatement", "identifier", "is_if_exists")
    SUBSTATEMENT_FIELD_NUMBER: _ClassVar[int]
    IDENTIFIER_FIELD_NUMBER: _ClassVar[int]
    IS_IF_EXISTS_FIELD_NUMBER: _ClassVar[int]
    substatement: StatementValue
    identifier: str
    is_if_exists: bool
    def __init__(self, substatement: _Optional[_Union[StatementValue, _Mapping]] = ..., identifier: _Optional[str] = ..., is_if_exists: _Optional[bool] = ...) -> None: ...

class ContinueStmt(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class BreakStmt(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class IndirectGotoStmt(_message.Message):
    __slots__ = ("target_expression",)
    TARGET_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    target_expression: ExpressionValue
    def __init__(self, target_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class IfStmt(_message.Message):
    __slots__ = ("init_statement", "condition_variable", "condition", "then_statement", "else_statement", "is_constexpr", "is_negated_condition", "is_consteval")
    INIT_STATEMENT_FIELD_NUMBER: _ClassVar[int]
    CONDITION_VARIABLE_FIELD_NUMBER: _ClassVar[int]
    CONDITION_FIELD_NUMBER: _ClassVar[int]
    THEN_STATEMENT_FIELD_NUMBER: _ClassVar[int]
    ELSE_STATEMENT_FIELD_NUMBER: _ClassVar[int]
    IS_CONSTEXPR_FIELD_NUMBER: _ClassVar[int]
    IS_NEGATED_CONDITION_FIELD_NUMBER: _ClassVar[int]
    IS_CONSTEVAL_FIELD_NUMBER: _ClassVar[int]
    init_statement: StatementValue
    condition_variable: DeclarationValue
    condition: ExpressionValue
    then_statement: StatementValue
    else_statement: StatementValue
    is_constexpr: bool
    is_negated_condition: bool
    is_consteval: bool
    def __init__(self, init_statement: _Optional[_Union[StatementValue, _Mapping]] = ..., condition_variable: _Optional[_Union[DeclarationValue, _Mapping]] = ..., condition: _Optional[_Union[ExpressionValue, _Mapping]] = ..., then_statement: _Optional[_Union[StatementValue, _Mapping]] = ..., else_statement: _Optional[_Union[StatementValue, _Mapping]] = ..., is_constexpr: _Optional[bool] = ..., is_negated_condition: _Optional[bool] = ..., is_consteval: _Optional[bool] = ...) -> None: ...

class GotoStmt(_message.Message):
    __slots__ = ("target_label",)
    TARGET_LABEL_FIELD_NUMBER: _ClassVar[int]
    target_label: DeclarationSymbol
    def __init__(self, target_label: _Optional[_Union[DeclarationSymbol, _Mapping]] = ...) -> None: ...

class ForStmt(_message.Message):
    __slots__ = ("init_statement", "condition_variable", "condition", "increment", "body")
    INIT_STATEMENT_FIELD_NUMBER: _ClassVar[int]
    CONDITION_VARIABLE_FIELD_NUMBER: _ClassVar[int]
    CONDITION_FIELD_NUMBER: _ClassVar[int]
    INCREMENT_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    init_statement: StatementValue
    condition_variable: DeclarationValue
    condition: ExpressionValue
    increment: ExpressionValue
    body: StatementValue
    def __init__(self, init_statement: _Optional[_Union[StatementValue, _Mapping]] = ..., condition_variable: _Optional[_Union[DeclarationValue, _Mapping]] = ..., condition: _Optional[_Union[ExpressionValue, _Mapping]] = ..., increment: _Optional[_Union[ExpressionValue, _Mapping]] = ..., body: _Optional[_Union[StatementValue, _Mapping]] = ...) -> None: ...

class DoStmt(_message.Message):
    __slots__ = ("body", "condition")
    BODY_FIELD_NUMBER: _ClassVar[int]
    CONDITION_FIELD_NUMBER: _ClassVar[int]
    body: StatementValue
    condition: ExpressionValue
    def __init__(self, body: _Optional[_Union[StatementValue, _Mapping]] = ..., condition: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class DeclStmt(_message.Message):
    __slots__ = ("declarations",)
    DECLARATIONS_FIELD_NUMBER: _ClassVar[int]
    declarations: _containers.RepeatedCompositeFieldContainer[DeclarationValue]
    def __init__(self, declarations: _Optional[_Iterable[_Union[DeclarationValue, _Mapping]]] = ...) -> None: ...

class CoroutineBodyStmt(_message.Message):
    __slots__ = ("body", "promise_declaration", "return_value", "exception_handler", "fallthrough_handler", "parameter_moves", "allocation_expressions", "deallocation_expressions")
    BODY_FIELD_NUMBER: _ClassVar[int]
    PROMISE_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    RETURN_VALUE_FIELD_NUMBER: _ClassVar[int]
    EXCEPTION_HANDLER_FIELD_NUMBER: _ClassVar[int]
    FALLTHROUGH_HANDLER_FIELD_NUMBER: _ClassVar[int]
    PARAMETER_MOVES_FIELD_NUMBER: _ClassVar[int]
    ALLOCATION_EXPRESSIONS_FIELD_NUMBER: _ClassVar[int]
    DEALLOCATION_EXPRESSIONS_FIELD_NUMBER: _ClassVar[int]
    body: StatementValue
    promise_declaration: DeclarationValue
    return_value: ExpressionValue
    exception_handler: StatementValue
    fallthrough_handler: StatementValue
    parameter_moves: _containers.RepeatedCompositeFieldContainer[StatementValue]
    allocation_expressions: _containers.RepeatedCompositeFieldContainer[ExpressionValue]
    deallocation_expressions: _containers.RepeatedCompositeFieldContainer[ExpressionValue]
    def __init__(self, body: _Optional[_Union[StatementValue, _Mapping]] = ..., promise_declaration: _Optional[_Union[DeclarationValue, _Mapping]] = ..., return_value: _Optional[_Union[ExpressionValue, _Mapping]] = ..., exception_handler: _Optional[_Union[StatementValue, _Mapping]] = ..., fallthrough_handler: _Optional[_Union[StatementValue, _Mapping]] = ..., parameter_moves: _Optional[_Iterable[_Union[StatementValue, _Mapping]]] = ..., allocation_expressions: _Optional[_Iterable[_Union[ExpressionValue, _Mapping]]] = ..., deallocation_expressions: _Optional[_Iterable[_Union[ExpressionValue, _Mapping]]] = ...) -> None: ...

class CoreturnStmt(_message.Message):
    __slots__ = ("operand", "promise_call")
    OPERAND_FIELD_NUMBER: _ClassVar[int]
    PROMISE_CALL_FIELD_NUMBER: _ClassVar[int]
    operand: ExpressionValue
    promise_call: ExpressionValue
    def __init__(self, operand: _Optional[_Union[ExpressionValue, _Mapping]] = ..., promise_call: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class CompoundStmt(_message.Message):
    __slots__ = ("body", "is_statement_expression")
    BODY_FIELD_NUMBER: _ClassVar[int]
    IS_STATEMENT_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    body: _containers.RepeatedCompositeFieldContainer[StatementValue]
    is_statement_expression: bool
    def __init__(self, body: _Optional[_Iterable[_Union[StatementValue, _Mapping]]] = ..., is_statement_expression: _Optional[bool] = ...) -> None: ...

class CXXTryStmt(_message.Message):
    __slots__ = ("try_block", "handlers")
    TRY_BLOCK_FIELD_NUMBER: _ClassVar[int]
    HANDLERS_FIELD_NUMBER: _ClassVar[int]
    try_block: StatementValue
    handlers: _containers.RepeatedCompositeFieldContainer[StatementValue]
    def __init__(self, try_block: _Optional[_Union[StatementValue, _Mapping]] = ..., handlers: _Optional[_Iterable[_Union[StatementValue, _Mapping]]] = ...) -> None: ...

class CXXForRangeStmt(_message.Message):
    __slots__ = ("init_statement", "loop_variable", "range_statement", "begin_statement", "end_statement", "condition", "increment", "body", "is_for_range_loop")
    INIT_STATEMENT_FIELD_NUMBER: _ClassVar[int]
    LOOP_VARIABLE_FIELD_NUMBER: _ClassVar[int]
    RANGE_STATEMENT_FIELD_NUMBER: _ClassVar[int]
    BEGIN_STATEMENT_FIELD_NUMBER: _ClassVar[int]
    END_STATEMENT_FIELD_NUMBER: _ClassVar[int]
    CONDITION_FIELD_NUMBER: _ClassVar[int]
    INCREMENT_FIELD_NUMBER: _ClassVar[int]
    BODY_FIELD_NUMBER: _ClassVar[int]
    IS_FOR_RANGE_LOOP_FIELD_NUMBER: _ClassVar[int]
    init_statement: StatementValue
    loop_variable: DeclarationValue
    range_statement: StatementValue
    begin_statement: StatementValue
    end_statement: StatementValue
    condition: ExpressionValue
    increment: ExpressionValue
    body: StatementValue
    is_for_range_loop: bool
    def __init__(self, init_statement: _Optional[_Union[StatementValue, _Mapping]] = ..., loop_variable: _Optional[_Union[DeclarationValue, _Mapping]] = ..., range_statement: _Optional[_Union[StatementValue, _Mapping]] = ..., begin_statement: _Optional[_Union[StatementValue, _Mapping]] = ..., end_statement: _Optional[_Union[StatementValue, _Mapping]] = ..., condition: _Optional[_Union[ExpressionValue, _Mapping]] = ..., increment: _Optional[_Union[ExpressionValue, _Mapping]] = ..., body: _Optional[_Union[StatementValue, _Mapping]] = ..., is_for_range_loop: _Optional[bool] = ...) -> None: ...

class CXXCatchStmt(_message.Message):
    __slots__ = ("exception_declaration", "handler_block", "is_catch_all")
    EXCEPTION_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    HANDLER_BLOCK_FIELD_NUMBER: _ClassVar[int]
    IS_CATCH_ALL_FIELD_NUMBER: _ClassVar[int]
    exception_declaration: DeclarationValue
    handler_block: StatementValue
    is_catch_all: bool
    def __init__(self, exception_declaration: _Optional[_Union[DeclarationValue, _Mapping]] = ..., handler_block: _Optional[_Union[StatementValue, _Mapping]] = ..., is_catch_all: _Optional[bool] = ...) -> None: ...

class MSAsmStmt(_message.Message):
    __slots__ = ("asm_string", "outputs", "inputs", "clobbers", "is_simple", "is_volatile", "is_goto", "dialect")
    ASM_STRING_FIELD_NUMBER: _ClassVar[int]
    OUTPUTS_FIELD_NUMBER: _ClassVar[int]
    INPUTS_FIELD_NUMBER: _ClassVar[int]
    CLOBBERS_FIELD_NUMBER: _ClassVar[int]
    IS_SIMPLE_FIELD_NUMBER: _ClassVar[int]
    IS_VOLATILE_FIELD_NUMBER: _ClassVar[int]
    IS_GOTO_FIELD_NUMBER: _ClassVar[int]
    DIALECT_FIELD_NUMBER: _ClassVar[int]
    asm_string: str
    outputs: _containers.RepeatedCompositeFieldContainer[AsmOperand]
    inputs: _containers.RepeatedCompositeFieldContainer[AsmOperand]
    clobbers: _containers.RepeatedScalarFieldContainer[str]
    is_simple: bool
    is_volatile: bool
    is_goto: bool
    dialect: str
    def __init__(self, asm_string: _Optional[str] = ..., outputs: _Optional[_Iterable[_Union[AsmOperand, _Mapping]]] = ..., inputs: _Optional[_Iterable[_Union[AsmOperand, _Mapping]]] = ..., clobbers: _Optional[_Iterable[str]] = ..., is_simple: _Optional[bool] = ..., is_volatile: _Optional[bool] = ..., is_goto: _Optional[bool] = ..., dialect: _Optional[str] = ...) -> None: ...

class GCCAsmStmt(_message.Message):
    __slots__ = ("asm_string", "outputs", "inputs", "clobbers", "goto_labels", "is_simple", "is_volatile", "is_goto", "dialect")
    ASM_STRING_FIELD_NUMBER: _ClassVar[int]
    OUTPUTS_FIELD_NUMBER: _ClassVar[int]
    INPUTS_FIELD_NUMBER: _ClassVar[int]
    CLOBBERS_FIELD_NUMBER: _ClassVar[int]
    GOTO_LABELS_FIELD_NUMBER: _ClassVar[int]
    IS_SIMPLE_FIELD_NUMBER: _ClassVar[int]
    IS_VOLATILE_FIELD_NUMBER: _ClassVar[int]
    IS_GOTO_FIELD_NUMBER: _ClassVar[int]
    DIALECT_FIELD_NUMBER: _ClassVar[int]
    asm_string: str
    outputs: _containers.RepeatedCompositeFieldContainer[AsmOperand]
    inputs: _containers.RepeatedCompositeFieldContainer[AsmOperand]
    clobbers: _containers.RepeatedScalarFieldContainer[str]
    goto_labels: _containers.RepeatedCompositeFieldContainer[DeclarationSymbol]
    is_simple: bool
    is_volatile: bool
    is_goto: bool
    dialect: str
    def __init__(self, asm_string: _Optional[str] = ..., outputs: _Optional[_Iterable[_Union[AsmOperand, _Mapping]]] = ..., inputs: _Optional[_Iterable[_Union[AsmOperand, _Mapping]]] = ..., clobbers: _Optional[_Iterable[str]] = ..., goto_labels: _Optional[_Iterable[_Union[DeclarationSymbol, _Mapping]]] = ..., is_simple: _Optional[bool] = ..., is_volatile: _Optional[bool] = ..., is_goto: _Optional[bool] = ..., dialect: _Optional[str] = ...) -> None: ...

class AdjustedType(_message.Message):
    __slots__ = ("info", "original_type", "adjusted_type")
    INFO_FIELD_NUMBER: _ClassVar[int]
    ORIGINAL_TYPE_FIELD_NUMBER: _ClassVar[int]
    ADJUSTED_TYPE_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    original_type: QualType
    adjusted_type: QualType
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., original_type: _Optional[_Union[QualType, _Mapping]] = ..., adjusted_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class DecayedType(_message.Message):
    __slots__ = ("info", "original_type", "adjusted_type", "pointee_type")
    INFO_FIELD_NUMBER: _ClassVar[int]
    ORIGINAL_TYPE_FIELD_NUMBER: _ClassVar[int]
    ADJUSTED_TYPE_FIELD_NUMBER: _ClassVar[int]
    POINTEE_TYPE_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    original_type: QualType
    adjusted_type: QualType
    pointee_type: QualType
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., original_type: _Optional[_Union[QualType, _Mapping]] = ..., adjusted_type: _Optional[_Union[QualType, _Mapping]] = ..., pointee_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class ConstantArrayType(_message.Message):
    __slots__ = ("info", "element_type", "size", "size_expression", "size_modifier", "index_qualifiers")
    INFO_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    SIZE_FIELD_NUMBER: _ClassVar[int]
    SIZE_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    SIZE_MODIFIER_FIELD_NUMBER: _ClassVar[int]
    INDEX_QUALIFIERS_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    element_type: QualType
    size: APIntBits
    size_expression: ExpressionValue
    size_modifier: ArraySizeModifier
    index_qualifiers: _common_pb2.Qualifiers
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., element_type: _Optional[_Union[QualType, _Mapping]] = ..., size: _Optional[_Union[APIntBits, _Mapping]] = ..., size_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., size_modifier: _Optional[_Union[ArraySizeModifier, str]] = ..., index_qualifiers: _Optional[_Union[_common_pb2.Qualifiers, _Mapping]] = ...) -> None: ...

class DependentSizedArrayType(_message.Message):
    __slots__ = ("info", "element_type", "size_expression", "size_modifier", "index_qualifiers")
    INFO_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    SIZE_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    SIZE_MODIFIER_FIELD_NUMBER: _ClassVar[int]
    INDEX_QUALIFIERS_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    element_type: QualType
    size_expression: ExpressionValue
    size_modifier: ArraySizeModifier
    index_qualifiers: _common_pb2.Qualifiers
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., element_type: _Optional[_Union[QualType, _Mapping]] = ..., size_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., size_modifier: _Optional[_Union[ArraySizeModifier, str]] = ..., index_qualifiers: _Optional[_Union[_common_pb2.Qualifiers, _Mapping]] = ...) -> None: ...

class IncompleteArrayType(_message.Message):
    __slots__ = ("info", "element_type", "size_modifier", "index_qualifiers")
    INFO_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    SIZE_MODIFIER_FIELD_NUMBER: _ClassVar[int]
    INDEX_QUALIFIERS_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    element_type: QualType
    size_modifier: ArraySizeModifier
    index_qualifiers: _common_pb2.Qualifiers
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., element_type: _Optional[_Union[QualType, _Mapping]] = ..., size_modifier: _Optional[_Union[ArraySizeModifier, str]] = ..., index_qualifiers: _Optional[_Union[_common_pb2.Qualifiers, _Mapping]] = ...) -> None: ...

class VariableArrayType(_message.Message):
    __slots__ = ("info", "element_type", "size_expression", "size_modifier", "index_qualifiers")
    INFO_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    SIZE_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    SIZE_MODIFIER_FIELD_NUMBER: _ClassVar[int]
    INDEX_QUALIFIERS_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    element_type: QualType
    size_expression: ExpressionValue
    size_modifier: ArraySizeModifier
    index_qualifiers: _common_pb2.Qualifiers
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., element_type: _Optional[_Union[QualType, _Mapping]] = ..., size_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., size_modifier: _Optional[_Union[ArraySizeModifier, str]] = ..., index_qualifiers: _Optional[_Union[_common_pb2.Qualifiers, _Mapping]] = ...) -> None: ...

class AtomicType(_message.Message):
    __slots__ = ("info", "value_type")
    INFO_FIELD_NUMBER: _ClassVar[int]
    VALUE_TYPE_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    value_type: QualType
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., value_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class AttributedType(_message.Message):
    __slots__ = ("info", "modified_type", "equivalent_type", "attribute_kind", "attribute", "attribute_kind_name")
    INFO_FIELD_NUMBER: _ClassVar[int]
    MODIFIED_TYPE_FIELD_NUMBER: _ClassVar[int]
    EQUIVALENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_KIND_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_KIND_NAME_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    modified_type: QualType
    equivalent_type: QualType
    attribute_kind: AttributedTypeKind
    attribute: AttributeValue
    attribute_kind_name: str
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., modified_type: _Optional[_Union[QualType, _Mapping]] = ..., equivalent_type: _Optional[_Union[QualType, _Mapping]] = ..., attribute_kind: _Optional[_Union[AttributedTypeKind, str]] = ..., attribute: _Optional[_Union[AttributeValue, _Mapping]] = ..., attribute_kind_name: _Optional[str] = ...) -> None: ...

class BTFTagAttributedType(_message.Message):
    __slots__ = ("info", "wrapped_type", "attribute")
    INFO_FIELD_NUMBER: _ClassVar[int]
    WRAPPED_TYPE_FIELD_NUMBER: _ClassVar[int]
    ATTRIBUTE_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    wrapped_type: QualType
    attribute: AttributeValue
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., wrapped_type: _Optional[_Union[QualType, _Mapping]] = ..., attribute: _Optional[_Union[AttributeValue, _Mapping]] = ...) -> None: ...

class BitIntType(_message.Message):
    __slots__ = ("info", "bit_width", "is_unsigned")
    INFO_FIELD_NUMBER: _ClassVar[int]
    BIT_WIDTH_FIELD_NUMBER: _ClassVar[int]
    IS_UNSIGNED_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    bit_width: int
    is_unsigned: bool
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., bit_width: _Optional[int] = ..., is_unsigned: _Optional[bool] = ...) -> None: ...

class BlockPointerType(_message.Message):
    __slots__ = ("info", "pointee_type")
    INFO_FIELD_NUMBER: _ClassVar[int]
    POINTEE_TYPE_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    pointee_type: QualType
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., pointee_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class CountAttributedType(_message.Message):
    __slots__ = ("info", "wrapped_type", "count_expression", "count_kind", "coupled_declarations")
    INFO_FIELD_NUMBER: _ClassVar[int]
    WRAPPED_TYPE_FIELD_NUMBER: _ClassVar[int]
    COUNT_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    COUNT_KIND_FIELD_NUMBER: _ClassVar[int]
    COUPLED_DECLARATIONS_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    wrapped_type: QualType
    count_expression: ExpressionValue
    count_kind: DynamicCountKind
    coupled_declarations: _containers.RepeatedCompositeFieldContainer[DeclarationSymbol]
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., wrapped_type: _Optional[_Union[QualType, _Mapping]] = ..., count_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., count_kind: _Optional[_Union[DynamicCountKind, str]] = ..., coupled_declarations: _Optional[_Iterable[_Union[DeclarationSymbol, _Mapping]]] = ...) -> None: ...

class BuiltinType(_message.Message):
    __slots__ = ("info", "kind", "extended_kind_name")
    INFO_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    EXTENDED_KIND_NAME_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    kind: BuiltinKind
    extended_kind_name: str
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., kind: _Optional[_Union[BuiltinKind, str]] = ..., extended_kind_name: _Optional[str] = ...) -> None: ...

class ComplexType(_message.Message):
    __slots__ = ("info", "element_type")
    INFO_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    element_type: QualType
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., element_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class DecltypeType(_message.Message):
    __slots__ = ("info", "underlying_expression", "underlying_type")
    INFO_FIELD_NUMBER: _ClassVar[int]
    UNDERLYING_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    UNDERLYING_TYPE_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    underlying_expression: ExpressionValue
    underlying_type: QualType
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., underlying_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., underlying_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class AutoType(_message.Message):
    __slots__ = ("info", "deduced_type", "keyword", "is_constrained", "type_constraint_concept", "type_constraint_arguments")
    INFO_FIELD_NUMBER: _ClassVar[int]
    DEDUCED_TYPE_FIELD_NUMBER: _ClassVar[int]
    KEYWORD_FIELD_NUMBER: _ClassVar[int]
    IS_CONSTRAINED_FIELD_NUMBER: _ClassVar[int]
    TYPE_CONSTRAINT_CONCEPT_FIELD_NUMBER: _ClassVar[int]
    TYPE_CONSTRAINT_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    deduced_type: QualType
    keyword: AutoKeyword
    is_constrained: bool
    type_constraint_concept: DeclarationSymbol
    type_constraint_arguments: _containers.RepeatedCompositeFieldContainer[TemplateArgument]
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., deduced_type: _Optional[_Union[QualType, _Mapping]] = ..., keyword: _Optional[_Union[AutoKeyword, str]] = ..., is_constrained: _Optional[bool] = ..., type_constraint_concept: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., type_constraint_arguments: _Optional[_Iterable[_Union[TemplateArgument, _Mapping]]] = ...) -> None: ...

class DeducedTemplateSpecializationType(_message.Message):
    __slots__ = ("info", "template_name", "deduced_type")
    INFO_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_NAME_FIELD_NUMBER: _ClassVar[int]
    DEDUCED_TYPE_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    template_name: TemplateName
    deduced_type: QualType
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., template_name: _Optional[_Union[TemplateName, _Mapping]] = ..., deduced_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class DependentAddressSpaceType(_message.Message):
    __slots__ = ("info", "pointee_type", "address_space_expression")
    INFO_FIELD_NUMBER: _ClassVar[int]
    POINTEE_TYPE_FIELD_NUMBER: _ClassVar[int]
    ADDRESS_SPACE_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    pointee_type: QualType
    address_space_expression: ExpressionValue
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., pointee_type: _Optional[_Union[QualType, _Mapping]] = ..., address_space_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class DependentBitIntType(_message.Message):
    __slots__ = ("info", "bit_width_expression", "is_unsigned")
    INFO_FIELD_NUMBER: _ClassVar[int]
    BIT_WIDTH_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    IS_UNSIGNED_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    bit_width_expression: ExpressionValue
    is_unsigned: bool
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., bit_width_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., is_unsigned: _Optional[bool] = ...) -> None: ...

class DependentNameType(_message.Message):
    __slots__ = ("info", "qualifier", "identifier")
    INFO_FIELD_NUMBER: _ClassVar[int]
    QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    IDENTIFIER_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    qualifier: NestedNameSpecifier
    identifier: str
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., qualifier: _Optional[_Union[NestedNameSpecifier, _Mapping]] = ..., identifier: _Optional[str] = ...) -> None: ...

class DependentSizedExtVectorType(_message.Message):
    __slots__ = ("info", "element_type", "size_expression")
    INFO_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    SIZE_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    element_type: QualType
    size_expression: ExpressionValue
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., element_type: _Optional[_Union[QualType, _Mapping]] = ..., size_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class DependentVectorType(_message.Message):
    __slots__ = ("info", "element_type", "size_expression", "vector_kind")
    INFO_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    SIZE_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    VECTOR_KIND_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    element_type: QualType
    size_expression: ExpressionValue
    vector_kind: VectorKind
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., element_type: _Optional[_Union[QualType, _Mapping]] = ..., size_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., vector_kind: _Optional[_Union[VectorKind, str]] = ...) -> None: ...

class FunctionProtoType(_message.Message):
    __slots__ = ("info", "return_type", "parameter_types", "is_variadic", "ext_info", "prototype_info")
    INFO_FIELD_NUMBER: _ClassVar[int]
    RETURN_TYPE_FIELD_NUMBER: _ClassVar[int]
    PARAMETER_TYPES_FIELD_NUMBER: _ClassVar[int]
    IS_VARIADIC_FIELD_NUMBER: _ClassVar[int]
    EXT_INFO_FIELD_NUMBER: _ClassVar[int]
    PROTOTYPE_INFO_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    return_type: QualType
    parameter_types: _containers.RepeatedCompositeFieldContainer[QualType]
    is_variadic: bool
    ext_info: FunctionExtInfo
    prototype_info: FunctionProtoExtInfo
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., return_type: _Optional[_Union[QualType, _Mapping]] = ..., parameter_types: _Optional[_Iterable[_Union[QualType, _Mapping]]] = ..., is_variadic: _Optional[bool] = ..., ext_info: _Optional[_Union[FunctionExtInfo, _Mapping]] = ..., prototype_info: _Optional[_Union[FunctionProtoExtInfo, _Mapping]] = ...) -> None: ...

class MacroQualifiedType(_message.Message):
    __slots__ = ("info", "underlying_type")
    INFO_FIELD_NUMBER: _ClassVar[int]
    UNDERLYING_TYPE_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    underlying_type: QualType
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., underlying_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class ConstantMatrixType(_message.Message):
    __slots__ = ("info", "element_type", "row_count", "column_count")
    INFO_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    ROW_COUNT_FIELD_NUMBER: _ClassVar[int]
    COLUMN_COUNT_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    element_type: QualType
    row_count: int
    column_count: int
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., element_type: _Optional[_Union[QualType, _Mapping]] = ..., row_count: _Optional[int] = ..., column_count: _Optional[int] = ...) -> None: ...

class DependentSizedMatrixType(_message.Message):
    __slots__ = ("info", "element_type", "row_count_expression", "column_count_expression")
    INFO_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    ROW_COUNT_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    COLUMN_COUNT_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    element_type: QualType
    row_count_expression: ExpressionValue
    column_count_expression: ExpressionValue
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., element_type: _Optional[_Union[QualType, _Mapping]] = ..., row_count_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., column_count_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ...) -> None: ...

class MemberPointerType(_message.Message):
    __slots__ = ("info", "pointee_type", "class_qualifier", "is_member_function_pointer")
    INFO_FIELD_NUMBER: _ClassVar[int]
    POINTEE_TYPE_FIELD_NUMBER: _ClassVar[int]
    CLASS_QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    IS_MEMBER_FUNCTION_POINTER_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    pointee_type: QualType
    class_qualifier: NestedNameSpecifier
    is_member_function_pointer: bool
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., pointee_type: _Optional[_Union[QualType, _Mapping]] = ..., class_qualifier: _Optional[_Union[NestedNameSpecifier, _Mapping]] = ..., is_member_function_pointer: _Optional[bool] = ...) -> None: ...

class PackExpansionType(_message.Message):
    __slots__ = ("info", "pattern_type", "expansion_count")
    INFO_FIELD_NUMBER: _ClassVar[int]
    PATTERN_TYPE_FIELD_NUMBER: _ClassVar[int]
    EXPANSION_COUNT_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    pattern_type: QualType
    expansion_count: int
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., pattern_type: _Optional[_Union[QualType, _Mapping]] = ..., expansion_count: _Optional[int] = ...) -> None: ...

class PackIndexingType(_message.Message):
    __slots__ = ("info", "pattern_type", "index_expression", "selected_index", "selected_type")
    INFO_FIELD_NUMBER: _ClassVar[int]
    PATTERN_TYPE_FIELD_NUMBER: _ClassVar[int]
    INDEX_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    SELECTED_INDEX_FIELD_NUMBER: _ClassVar[int]
    SELECTED_TYPE_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    pattern_type: QualType
    index_expression: ExpressionValue
    selected_index: int
    selected_type: QualType
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., pattern_type: _Optional[_Union[QualType, _Mapping]] = ..., index_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., selected_index: _Optional[int] = ..., selected_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class ParenType(_message.Message):
    __slots__ = ("info", "inner_type")
    INFO_FIELD_NUMBER: _ClassVar[int]
    INNER_TYPE_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    inner_type: QualType
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., inner_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class PointerType(_message.Message):
    __slots__ = ("info", "pointee_type")
    INFO_FIELD_NUMBER: _ClassVar[int]
    POINTEE_TYPE_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    pointee_type: QualType
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., pointee_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class PredefinedSugarType(_message.Message):
    __slots__ = ("info", "predefined_kind", "identifier")
    INFO_FIELD_NUMBER: _ClassVar[int]
    PREDEFINED_KIND_FIELD_NUMBER: _ClassVar[int]
    IDENTIFIER_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    predefined_kind: PredefinedTypeKind
    identifier: str
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., predefined_kind: _Optional[_Union[PredefinedTypeKind, str]] = ..., identifier: _Optional[str] = ...) -> None: ...

class LValueReferenceType(_message.Message):
    __slots__ = ("info", "referred_type")
    INFO_FIELD_NUMBER: _ClassVar[int]
    REFERRED_TYPE_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    referred_type: QualType
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., referred_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class RValueReferenceType(_message.Message):
    __slots__ = ("info", "referred_type")
    INFO_FIELD_NUMBER: _ClassVar[int]
    REFERRED_TYPE_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    referred_type: QualType
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., referred_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...

class SubstBuiltinTemplatePackType(_message.Message):
    __slots__ = ("info", "argument_pack")
    INFO_FIELD_NUMBER: _ClassVar[int]
    ARGUMENT_PACK_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    argument_pack: TemplateArgument
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., argument_pack: _Optional[_Union[TemplateArgument, _Mapping]] = ...) -> None: ...

class SubstTemplateTypeParmPackType(_message.Message):
    __slots__ = ("info", "associated_declaration", "replaced_parameter", "parameter_index", "is_final", "argument_pack")
    INFO_FIELD_NUMBER: _ClassVar[int]
    ASSOCIATED_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    REPLACED_PARAMETER_FIELD_NUMBER: _ClassVar[int]
    PARAMETER_INDEX_FIELD_NUMBER: _ClassVar[int]
    IS_FINAL_FIELD_NUMBER: _ClassVar[int]
    ARGUMENT_PACK_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    associated_declaration: DeclarationSymbol
    replaced_parameter: DeclarationSymbol
    parameter_index: int
    is_final: bool
    argument_pack: TemplateArgument
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., associated_declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., replaced_parameter: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., parameter_index: _Optional[int] = ..., is_final: _Optional[bool] = ..., argument_pack: _Optional[_Union[TemplateArgument, _Mapping]] = ...) -> None: ...

class SubstTemplateTypeParmType(_message.Message):
    __slots__ = ("info", "replacement_type", "associated_declaration", "replaced_parameter", "parameter_index", "pack_index", "is_final")
    INFO_FIELD_NUMBER: _ClassVar[int]
    REPLACEMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    ASSOCIATED_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    REPLACED_PARAMETER_FIELD_NUMBER: _ClassVar[int]
    PARAMETER_INDEX_FIELD_NUMBER: _ClassVar[int]
    PACK_INDEX_FIELD_NUMBER: _ClassVar[int]
    IS_FINAL_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    replacement_type: QualType
    associated_declaration: DeclarationSymbol
    replaced_parameter: DeclarationSymbol
    parameter_index: int
    pack_index: int
    is_final: bool
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., replacement_type: _Optional[_Union[QualType, _Mapping]] = ..., associated_declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., replaced_parameter: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., parameter_index: _Optional[int] = ..., pack_index: _Optional[int] = ..., is_final: _Optional[bool] = ...) -> None: ...

class EnumType(_message.Message):
    __slots__ = ("info", "declaration", "qualifier")
    INFO_FIELD_NUMBER: _ClassVar[int]
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    declaration: DeclarationSymbol
    qualifier: NestedNameSpecifier
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., qualifier: _Optional[_Union[NestedNameSpecifier, _Mapping]] = ...) -> None: ...

class InjectedClassNameType(_message.Message):
    __slots__ = ("info", "declaration", "qualifier", "template_declaration", "template_name", "specialization_arguments")
    INFO_FIELD_NUMBER: _ClassVar[int]
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_NAME_FIELD_NUMBER: _ClassVar[int]
    SPECIALIZATION_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    declaration: DeclarationSymbol
    qualifier: NestedNameSpecifier
    template_declaration: DeclarationSymbol
    template_name: TemplateName
    specialization_arguments: _containers.RepeatedCompositeFieldContainer[TemplateArgument]
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., qualifier: _Optional[_Union[NestedNameSpecifier, _Mapping]] = ..., template_declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., template_name: _Optional[_Union[TemplateName, _Mapping]] = ..., specialization_arguments: _Optional[_Iterable[_Union[TemplateArgument, _Mapping]]] = ...) -> None: ...

class RecordType(_message.Message):
    __slots__ = ("info", "declaration", "qualifier", "template_declaration", "template_name", "specialization_arguments")
    INFO_FIELD_NUMBER: _ClassVar[int]
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_NAME_FIELD_NUMBER: _ClassVar[int]
    SPECIALIZATION_ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    declaration: DeclarationSymbol
    qualifier: NestedNameSpecifier
    template_declaration: DeclarationSymbol
    template_name: TemplateName
    specialization_arguments: _containers.RepeatedCompositeFieldContainer[TemplateArgument]
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., qualifier: _Optional[_Union[NestedNameSpecifier, _Mapping]] = ..., template_declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., template_name: _Optional[_Union[TemplateName, _Mapping]] = ..., specialization_arguments: _Optional[_Iterable[_Union[TemplateArgument, _Mapping]]] = ...) -> None: ...

class TemplateSpecializationType(_message.Message):
    __slots__ = ("info", "template_name", "arguments", "aliased_type", "has_alias")
    INFO_FIELD_NUMBER: _ClassVar[int]
    TEMPLATE_NAME_FIELD_NUMBER: _ClassVar[int]
    ARGUMENTS_FIELD_NUMBER: _ClassVar[int]
    ALIASED_TYPE_FIELD_NUMBER: _ClassVar[int]
    HAS_ALIAS_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    template_name: TemplateName
    arguments: _containers.RepeatedCompositeFieldContainer[TemplateArgument]
    aliased_type: QualType
    has_alias: bool
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., template_name: _Optional[_Union[TemplateName, _Mapping]] = ..., arguments: _Optional[_Iterable[_Union[TemplateArgument, _Mapping]]] = ..., aliased_type: _Optional[_Union[QualType, _Mapping]] = ..., has_alias: _Optional[bool] = ...) -> None: ...

class TemplateTypeParmType(_message.Message):
    __slots__ = ("info", "depth", "index", "is_pack", "declaration", "identifier")
    INFO_FIELD_NUMBER: _ClassVar[int]
    DEPTH_FIELD_NUMBER: _ClassVar[int]
    INDEX_FIELD_NUMBER: _ClassVar[int]
    IS_PACK_FIELD_NUMBER: _ClassVar[int]
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    IDENTIFIER_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    depth: int
    index: int
    is_pack: bool
    declaration: DeclarationSymbol
    identifier: str
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., depth: _Optional[int] = ..., index: _Optional[int] = ..., is_pack: _Optional[bool] = ..., declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., identifier: _Optional[str] = ...) -> None: ...

class TypeOfExprType(_message.Message):
    __slots__ = ("info", "underlying_expression", "kind")
    INFO_FIELD_NUMBER: _ClassVar[int]
    UNDERLYING_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    underlying_expression: ExpressionValue
    kind: TypeOfKind
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., underlying_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., kind: _Optional[_Union[TypeOfKind, str]] = ...) -> None: ...

class TypeOfType(_message.Message):
    __slots__ = ("info", "underlying_type", "kind")
    INFO_FIELD_NUMBER: _ClassVar[int]
    UNDERLYING_TYPE_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    underlying_type: QualType
    kind: TypeOfKind
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., underlying_type: _Optional[_Union[QualType, _Mapping]] = ..., kind: _Optional[_Union[TypeOfKind, str]] = ...) -> None: ...

class TypedefType(_message.Message):
    __slots__ = ("info", "declaration", "desugared_type", "qualifier")
    INFO_FIELD_NUMBER: _ClassVar[int]
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    DESUGARED_TYPE_FIELD_NUMBER: _ClassVar[int]
    QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    declaration: DeclarationSymbol
    desugared_type: QualType
    qualifier: NestedNameSpecifier
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., desugared_type: _Optional[_Union[QualType, _Mapping]] = ..., qualifier: _Optional[_Union[NestedNameSpecifier, _Mapping]] = ...) -> None: ...

class UnaryTransformType(_message.Message):
    __slots__ = ("info", "base_type", "transformed_type", "transform_kind")
    INFO_FIELD_NUMBER: _ClassVar[int]
    BASE_TYPE_FIELD_NUMBER: _ClassVar[int]
    TRANSFORMED_TYPE_FIELD_NUMBER: _ClassVar[int]
    TRANSFORM_KIND_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    base_type: QualType
    transformed_type: QualType
    transform_kind: UnaryTransformKind
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., base_type: _Optional[_Union[QualType, _Mapping]] = ..., transformed_type: _Optional[_Union[QualType, _Mapping]] = ..., transform_kind: _Optional[_Union[UnaryTransformKind, str]] = ...) -> None: ...

class UnresolvedUsingType(_message.Message):
    __slots__ = ("info", "declaration", "qualifier")
    INFO_FIELD_NUMBER: _ClassVar[int]
    DECLARATION_FIELD_NUMBER: _ClassVar[int]
    QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    declaration: DeclarationSymbol
    qualifier: NestedNameSpecifier
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., qualifier: _Optional[_Union[NestedNameSpecifier, _Mapping]] = ...) -> None: ...

class UsingType(_message.Message):
    __slots__ = ("info", "shadow_declaration", "desugared_type", "qualifier")
    INFO_FIELD_NUMBER: _ClassVar[int]
    SHADOW_DECLARATION_FIELD_NUMBER: _ClassVar[int]
    DESUGARED_TYPE_FIELD_NUMBER: _ClassVar[int]
    QUALIFIER_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    shadow_declaration: DeclarationSymbol
    desugared_type: QualType
    qualifier: NestedNameSpecifier
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., shadow_declaration: _Optional[_Union[DeclarationSymbol, _Mapping]] = ..., desugared_type: _Optional[_Union[QualType, _Mapping]] = ..., qualifier: _Optional[_Union[NestedNameSpecifier, _Mapping]] = ...) -> None: ...

class VectorType(_message.Message):
    __slots__ = ("info", "element_type", "element_count", "vector_kind")
    INFO_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_COUNT_FIELD_NUMBER: _ClassVar[int]
    VECTOR_KIND_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    element_type: QualType
    element_count: int
    vector_kind: VectorKind
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., element_type: _Optional[_Union[QualType, _Mapping]] = ..., element_count: _Optional[int] = ..., vector_kind: _Optional[_Union[VectorKind, str]] = ...) -> None: ...

class ExtVectorType(_message.Message):
    __slots__ = ("info", "element_type", "element_count")
    INFO_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_TYPE_FIELD_NUMBER: _ClassVar[int]
    ELEMENT_COUNT_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    element_type: QualType
    element_count: int
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., element_type: _Optional[_Union[QualType, _Mapping]] = ..., element_count: _Optional[int] = ...) -> None: ...

class DependentTypeOfExprType(_message.Message):
    __slots__ = ("info", "underlying_expression", "kind")
    INFO_FIELD_NUMBER: _ClassVar[int]
    UNDERLYING_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    KIND_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    underlying_expression: ExpressionValue
    kind: TypeOfKind
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., underlying_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., kind: _Optional[_Union[TypeOfKind, str]] = ...) -> None: ...

class DependentDecltypeType(_message.Message):
    __slots__ = ("info", "underlying_expression", "underlying_type")
    INFO_FIELD_NUMBER: _ClassVar[int]
    UNDERLYING_EXPRESSION_FIELD_NUMBER: _ClassVar[int]
    UNDERLYING_TYPE_FIELD_NUMBER: _ClassVar[int]
    info: TypeInfo
    underlying_expression: ExpressionValue
    underlying_type: QualType
    def __init__(self, info: _Optional[_Union[TypeInfo, _Mapping]] = ..., underlying_expression: _Optional[_Union[ExpressionValue, _Mapping]] = ..., underlying_type: _Optional[_Union[QualType, _Mapping]] = ...) -> None: ...
