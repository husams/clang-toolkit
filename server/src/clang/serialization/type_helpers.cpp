#include "type_helpers.hpp"
#include <stdexcept>

namespace ctk::clang_layer::serialization::helpers {
void write_common(const clang::Type &native, google::protobuf::Message &payload,
                  SerializationContext &context) {
  const auto *field = payload.GetDescriptor()->FindFieldByName("info");
  if (!field || !field->message_type() ||
      field->message_type()->full_name() != "ctk.ast.v1.TypeInfo")
    throw std::logic_error("concrete type payload lacks its typed TypeInfo field");
  const auto &policy = context.ast_context.getPrintingPolicy();
  ctk::ast::v1::TypeInfo info;
  info.set_spelling(clang::QualType(&native, 0).getAsString(policy));
  info.set_canonical_spelling(native.getCanonicalTypeInternal().getAsString(policy));
  info.set_is_dependent(native.isDependentType());
  info.set_is_instantiation_dependent(native.isInstantiationDependentType());
  info.set_contains_unexpanded_parameter_pack(native.containsUnexpandedParameterPack());
  payload.GetReflection()->MutableMessage(&payload, field)->CopyFrom(info);
}
} // namespace ctk::clang_layer::serialization::helpers

// Enum names map deliberately; protobuf numbers are independent of Clang ordinals.
namespace ctk::clang_layer::serialization::type_helpers {
ctk::ast::v1::BuiltinKind builtin_kind(clang::BuiltinType::Kind value) {
  switch (value) {
  case clang::BuiltinType::Void: return ctk::ast::v1::BUILTIN_KIND_VOID;
  case clang::BuiltinType::Bool: return ctk::ast::v1::BUILTIN_KIND_BOOL;
  case clang::BuiltinType::Char_U: return ctk::ast::v1::BUILTIN_KIND_CHAR_U;
  case clang::BuiltinType::UChar: return ctk::ast::v1::BUILTIN_KIND_UCHAR;
  case clang::BuiltinType::Char16: return ctk::ast::v1::BUILTIN_KIND_CHAR16;
  case clang::BuiltinType::Char32: return ctk::ast::v1::BUILTIN_KIND_CHAR32;
  case clang::BuiltinType::UShort: return ctk::ast::v1::BUILTIN_KIND_USHORT;
  case clang::BuiltinType::UInt: return ctk::ast::v1::BUILTIN_KIND_UINT;
  case clang::BuiltinType::ULong: return ctk::ast::v1::BUILTIN_KIND_ULONG;
  case clang::BuiltinType::ULongLong: return ctk::ast::v1::BUILTIN_KIND_ULONGLONG;
  case clang::BuiltinType::UInt128: return ctk::ast::v1::BUILTIN_KIND_UINT128;
  case clang::BuiltinType::Char_S: return ctk::ast::v1::BUILTIN_KIND_CHAR_S;
  case clang::BuiltinType::SChar: return ctk::ast::v1::BUILTIN_KIND_SCHAR;
  case clang::BuiltinType::Short: return ctk::ast::v1::BUILTIN_KIND_SHORT;
  case clang::BuiltinType::Int: return ctk::ast::v1::BUILTIN_KIND_INT;
  case clang::BuiltinType::Long: return ctk::ast::v1::BUILTIN_KIND_LONG;
  case clang::BuiltinType::LongLong: return ctk::ast::v1::BUILTIN_KIND_LONGLONG;
  case clang::BuiltinType::Int128: return ctk::ast::v1::BUILTIN_KIND_INT128;
  case clang::BuiltinType::Half: return ctk::ast::v1::BUILTIN_KIND_HALF;
  case clang::BuiltinType::Float: return ctk::ast::v1::BUILTIN_KIND_FLOAT;
  case clang::BuiltinType::Double: return ctk::ast::v1::BUILTIN_KIND_DOUBLE;
  case clang::BuiltinType::LongDouble: return ctk::ast::v1::BUILTIN_KIND_LONGDOUBLE;
  case clang::BuiltinType::Float128: return ctk::ast::v1::BUILTIN_KIND_FLOAT128;
  case clang::BuiltinType::NullPtr: return ctk::ast::v1::BUILTIN_KIND_NULLPTR;
  case clang::BuiltinType::Overload: return ctk::ast::v1::BUILTIN_KIND_OVERLOAD;
  case clang::BuiltinType::Dependent: return ctk::ast::v1::BUILTIN_KIND_DEPENDENT;
  case clang::BuiltinType::Float16: return ctk::ast::v1::BUILTIN_KIND_FLOAT16;
  case clang::BuiltinType::BFloat16: return ctk::ast::v1::BUILTIN_KIND_BFLOAT16;
  case clang::BuiltinType::Char8: return ctk::ast::v1::BUILTIN_KIND_CHAR8;
  case clang::BuiltinType::WChar_U: return ctk::ast::v1::BUILTIN_KIND_WCHAR_U;
  case clang::BuiltinType::WChar_S: return ctk::ast::v1::BUILTIN_KIND_WCHAR_S;
  default: return ctk::ast::v1::BUILTIN_KIND_EXTENDED;
  }
}

#if CLANG_VERSION_MAJOR >= 21
using NativeArrayModifier = clang::ArraySizeModifier;
using NativeVectorKind = clang::VectorKind;
#else
using NativeArrayModifier = clang::ArrayType::ArraySizeModifier;
using NativeVectorKind = clang::VectorType::VectorKind;
#endif
ctk::ast::v1::ArraySizeModifier array_modifier(NativeArrayModifier value) {
  switch (value) {
  case NativeArrayModifier::Normal: return ctk::ast::v1::ARRAY_SIZE_MODIFIER_NORMAL;
  case NativeArrayModifier::Static: return ctk::ast::v1::ARRAY_SIZE_MODIFIER_STATIC;
  case NativeArrayModifier::Star: return ctk::ast::v1::ARRAY_SIZE_MODIFIER_STAR;
  default: return ctk::ast::v1::ARRAY_SIZE_MODIFIER_UNSPECIFIED;
  }
}

ctk::ast::v1::VectorKind vector_kind(NativeVectorKind value) {
  switch (value) {
  case NativeVectorKind::Generic: return ctk::ast::v1::VECTOR_KIND_GENERIC;
  case NativeVectorKind::AltiVecVector: return ctk::ast::v1::VECTOR_KIND_ALTIVEC_VECTOR;
  case NativeVectorKind::AltiVecPixel: return ctk::ast::v1::VECTOR_KIND_ALTIVEC_PIXEL;
  case NativeVectorKind::AltiVecBool: return ctk::ast::v1::VECTOR_KIND_ALTIVEC_BOOL;
  case NativeVectorKind::Neon: return ctk::ast::v1::VECTOR_KIND_NEON;
  case NativeVectorKind::NeonPoly: return ctk::ast::v1::VECTOR_KIND_NEON_POLY;
  case NativeVectorKind::SveFixedLengthData: return ctk::ast::v1::VECTOR_KIND_SVE_FIXED_DATA;
  case NativeVectorKind::SveFixedLengthPredicate: return ctk::ast::v1::VECTOR_KIND_SVE_FIXED_PREDICATE;
  case NativeVectorKind::RVVFixedLengthData: return ctk::ast::v1::VECTOR_KIND_RVV_FIXED_DATA;
  case NativeVectorKind::RVVFixedLengthMask: return ctk::ast::v1::VECTOR_KIND_RVV_FIXED_MASK;
#if CLANG_VERSION_MAJOR >= 21
  case NativeVectorKind::RVVFixedLengthMask_1: return ctk::ast::v1::VECTOR_KIND_RVV_FIXED_MASK_1;
#endif
#if CLANG_VERSION_MAJOR >= 21
  case NativeVectorKind::RVVFixedLengthMask_2: return ctk::ast::v1::VECTOR_KIND_RVV_FIXED_MASK_2;
#endif
#if CLANG_VERSION_MAJOR >= 21
  case NativeVectorKind::RVVFixedLengthMask_4: return ctk::ast::v1::VECTOR_KIND_RVV_FIXED_MASK_4;
#endif
  default: return ctk::ast::v1::VECTOR_KIND_UNSPECIFIED;
  }
}

ctk::ast::v1::UnaryTransformKind transform_kind(clang::UnaryTransformType::UTTKind value) {
  switch (value) {
  case clang::UnaryTransformType::AddLvalueReference: return ctk::ast::v1::UNARY_TRANSFORM_KIND_ADD_LVALUE_REFERENCE;
  case clang::UnaryTransformType::AddPointer: return ctk::ast::v1::UNARY_TRANSFORM_KIND_ADD_POINTER;
  case clang::UnaryTransformType::AddRvalueReference: return ctk::ast::v1::UNARY_TRANSFORM_KIND_ADD_RVALUE_REFERENCE;
  case clang::UnaryTransformType::Decay: return ctk::ast::v1::UNARY_TRANSFORM_KIND_DECAY;
  case clang::UnaryTransformType::MakeSigned: return ctk::ast::v1::UNARY_TRANSFORM_KIND_MAKE_SIGNED;
  case clang::UnaryTransformType::MakeUnsigned: return ctk::ast::v1::UNARY_TRANSFORM_KIND_MAKE_UNSIGNED;
  case clang::UnaryTransformType::RemoveAllExtents: return ctk::ast::v1::UNARY_TRANSFORM_KIND_REMOVE_ALL_EXTENTS;
  case clang::UnaryTransformType::RemoveConst: return ctk::ast::v1::UNARY_TRANSFORM_KIND_REMOVE_CONST;
  case clang::UnaryTransformType::RemoveCV: return ctk::ast::v1::UNARY_TRANSFORM_KIND_REMOVE_CV;
  case clang::UnaryTransformType::RemoveCVRef: return ctk::ast::v1::UNARY_TRANSFORM_KIND_REMOVE_CV_REF;
  case clang::UnaryTransformType::RemoveExtent: return ctk::ast::v1::UNARY_TRANSFORM_KIND_REMOVE_EXTENT;
  case clang::UnaryTransformType::RemovePointer: return ctk::ast::v1::UNARY_TRANSFORM_KIND_REMOVE_POINTER;
  case clang::UnaryTransformType::RemoveReference: return ctk::ast::v1::UNARY_TRANSFORM_KIND_REMOVE_REFERENCE;
  case clang::UnaryTransformType::RemoveRestrict: return ctk::ast::v1::UNARY_TRANSFORM_KIND_REMOVE_RESTRICT;
  case clang::UnaryTransformType::RemoveVolatile: return ctk::ast::v1::UNARY_TRANSFORM_KIND_REMOVE_VOLATILE;
  case clang::UnaryTransformType::EnumUnderlyingType: return ctk::ast::v1::UNARY_TRANSFORM_KIND_ENUM_UNDERLYING_TYPE;
  default: return ctk::ast::v1::UNARY_TRANSFORM_KIND_UNSPECIFIED;
  }
}

ctk::ast::v1::FunctionCallingConvention calling_convention(clang::CallingConv value) {
  switch (value) {
  case clang::CC_C: return ctk::ast::v1::FUNCTION_CALLING_CONVENTION_C;
  case clang::CC_X86StdCall: return ctk::ast::v1::FUNCTION_CALLING_CONVENTION_X86_STDCALL;
  case clang::CC_X86FastCall: return ctk::ast::v1::FUNCTION_CALLING_CONVENTION_X86_FASTCALL;
  case clang::CC_X86ThisCall: return ctk::ast::v1::FUNCTION_CALLING_CONVENTION_X86_THISCALL;
  case clang::CC_X86VectorCall: return ctk::ast::v1::FUNCTION_CALLING_CONVENTION_X86_VECTORCALL;
  case clang::CC_Win64: return ctk::ast::v1::FUNCTION_CALLING_CONVENTION_WIN64;
  case clang::CC_X86_64SysV: return ctk::ast::v1::FUNCTION_CALLING_CONVENTION_X86_64_SYSV;
  case clang::CC_X86RegCall: return ctk::ast::v1::FUNCTION_CALLING_CONVENTION_X86_REGCALL;
  case clang::CC_AAPCS: return ctk::ast::v1::FUNCTION_CALLING_CONVENTION_AAPCS;
  case clang::CC_AAPCS_VFP: return ctk::ast::v1::FUNCTION_CALLING_CONVENTION_AAPCS_VFP;
  case clang::CC_Swift: return ctk::ast::v1::FUNCTION_CALLING_CONVENTION_SWIFT;
  case clang::CC_SwiftAsync: return ctk::ast::v1::FUNCTION_CALLING_CONVENTION_SWIFT_ASYNC;
  case clang::CC_PreserveMost: return ctk::ast::v1::FUNCTION_CALLING_CONVENTION_PRESERVE_MOST;
  case clang::CC_PreserveAll: return ctk::ast::v1::FUNCTION_CALLING_CONVENTION_PRESERVE_ALL;
  case clang::CC_AArch64VectorCall: return ctk::ast::v1::FUNCTION_CALLING_CONVENTION_AARCH64_VECTOR;
  case clang::CC_AArch64SVEPCS: return ctk::ast::v1::FUNCTION_CALLING_CONVENTION_AARCH64_SVE;
  case clang::CC_PreserveNone: return ctk::ast::v1::FUNCTION_CALLING_CONVENTION_PRESERVE_NONE;
  case clang::CC_RISCVVectorCall: return ctk::ast::v1::FUNCTION_CALLING_CONVENTION_RISCV_VECTOR;
  default: return ctk::ast::v1::FUNCTION_CALLING_CONVENTION_TARGET_EXTENSION;
  }
}

ctk::ast::v1::ExceptionSpecification exception_specification(clang::ExceptionSpecificationType value) {
  switch (value) {
  case clang::EST_None: return ctk::ast::v1::EXCEPTION_SPECIFICATION_NONE;
  case clang::EST_DynamicNone: return ctk::ast::v1::EXCEPTION_SPECIFICATION_DYNAMIC_NONE;
  case clang::EST_Dynamic: return ctk::ast::v1::EXCEPTION_SPECIFICATION_DYNAMIC;
  case clang::EST_MSAny: return ctk::ast::v1::EXCEPTION_SPECIFICATION_MS_ANY;
  case clang::EST_NoThrow: return ctk::ast::v1::EXCEPTION_SPECIFICATION_NO_THROW;
  case clang::EST_BasicNoexcept: return ctk::ast::v1::EXCEPTION_SPECIFICATION_MS_BASIC_NOEXCEPT;
  case clang::EST_DependentNoexcept: return ctk::ast::v1::EXCEPTION_SPECIFICATION_DEPENDENT_NOEXCEPT;
  case clang::EST_NoexceptFalse: return ctk::ast::v1::EXCEPTION_SPECIFICATION_NOEXCEPT_FALSE;
  case clang::EST_NoexceptTrue: return ctk::ast::v1::EXCEPTION_SPECIFICATION_NOEXCEPT_TRUE;
  case clang::EST_Unevaluated: return ctk::ast::v1::EXCEPTION_SPECIFICATION_UNEVALUATED;
  case clang::EST_Uninstantiated: return ctk::ast::v1::EXCEPTION_SPECIFICATION_UNINSTANTIATED;
  case clang::EST_Unparsed: return ctk::ast::v1::EXCEPTION_SPECIFICATION_UNPARSED;
  default: return ctk::ast::v1::EXCEPTION_SPECIFICATION_OTHER;
  }
}

std::string attribute_name(clang::attr::Kind kind) {
  // Metadata naming only; no node serializer implementation is macro generated.
  switch (kind) {
#define ATTR(Name) case clang::attr::Name: return #Name;
#include <clang/Basic/AttrList.inc>
#undef ATTR
  default: return "unknown_attribute";
  }
}

ctk::ast::v1::AttributedTypeKind attribute_kind(const clang::AttributedType &native) {
  auto name = attribute_name(native.getAttrKind());
  if (name.find("AddressSpace") != std::string::npos) return ctk::ast::v1::ATTRIBUTED_TYPE_KIND_ADDRESS_SPACE;
  if (native.getImmediateNullability()) return ctk::ast::v1::ATTRIBUTED_TYPE_KIND_NULLABILITY;
  if (native.isCallingConv()) return ctk::ast::v1::ATTRIBUTED_TYPE_KIND_CALLING_CONVENTION;
  if (name.find("Vector") != std::string::npos) return ctk::ast::v1::ATTRIBUTED_TYPE_KIND_VECTOR;
  if (name.find("FixedPoint") != std::string::npos) return ctk::ast::v1::ATTRIBUTED_TYPE_KIND_FIXED_POINT;
  return ctk::ast::v1::ATTRIBUTED_TYPE_KIND_CPP_EXTENSION;
}

void write_attribute(const clang::Attr &native, ctk::ast::v1::AttributeValue &payload,
                     SerializationContext &context) {
  payload.set_clang_class(attribute_name(native.getKind()) + "Attr");
  payload.set_state(ctk::ast::v1::FIELD_STATE_UNAVAILABLE);
  payload.set_reason("attribute arguments have no typed contract in the supported AST catalog");
  helpers::unavailable(payload, "arguments", payload.reason(), context);
}

void write_function_ext(const clang::FunctionType &native, ctk::ast::v1::FunctionExtInfo &payload,
                        SerializationContext &) {
  auto info = native.getExtInfo();
  payload.set_calling_convention(calling_convention(info.getCC()));
  if (payload.calling_convention() == ctk::ast::v1::FUNCTION_CALLING_CONVENTION_TARGET_EXTENSION)
    payload.set_target_convention_name(clang::FunctionType::getNameForCallConv(info.getCC()).str());
  payload.set_no_return(info.getNoReturn());
  payload.set_produces_result(info.getProducesResult());
  if (info.getHasRegParm()) payload.set_regparm(info.getRegParm());
  payload.set_no_caller_saved_registers(info.getNoCallerSavedRegs());
  payload.set_no_cf_check(info.getNoCfCheck());
  payload.set_cmse_nonsecure_call(info.getCmseNSCall());
}

void write_function_proto_ext(const clang::FunctionProtoType &native,
                              ctk::ast::v1::FunctionProtoExtInfo &payload,
                              SerializationContext &context) {
  payload.set_exception_specification(exception_specification(native.getExceptionSpecType()));
  for (auto exception : native.exceptions()) {
    if (!helpers::can_expand(payload, "exception_types", context)) break;
    helpers::write_type(exception, *payload.add_exception_types(), context);
  }
  switch (native.getRefQualifier()) {
  case clang::RQ_None: payload.set_ref_qualifier(ctk::ast::v1::REF_QUALIFIER_NONE); break;
  case clang::RQ_LValue: payload.set_ref_qualifier(ctk::ast::v1::REF_QUALIFIER_LVALUE); break;
  case clang::RQ_RValue: payload.set_ref_qualifier(ctk::ast::v1::REF_QUALIFIER_RVALUE); break;
  }
  if (auto *expr = native.getNoexceptExpr())
    helpers::write_expr(expr, *payload.mutable_noexcept_expression(), context);
  if (auto *declaration = native.getExceptionSpecDecl())
    helpers::write_symbol(*declaration, *payload.mutable_exception_specification_declaration(), context);
  if (auto *declaration = native.getExceptionSpecTemplate())
    helpers::write_symbol(*declaration, *payload.mutable_exception_specification_template(), context);
  helpers::write_qualifiers(native.getMethodQuals(), *payload.mutable_type_qualifiers());
  payload.set_is_cfi_unchecked_callee(native.hasCFIUncheckedCallee());
}
} // namespace ctk::clang_layer::serialization::type_helpers
