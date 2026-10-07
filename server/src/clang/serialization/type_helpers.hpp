#pragma once
#include "semantic_helpers.hpp"
#include <clang/AST/Attr.h>

namespace ctk::clang_layer::serialization::type_helpers {
ctk::ast::v1::BuiltinKind builtin_kind(clang::BuiltinType::Kind);
#if CLANG_VERSION_MAJOR >= 21
ctk::ast::v1::ArraySizeModifier array_modifier(clang::ArraySizeModifier);
ctk::ast::v1::VectorKind vector_kind(clang::VectorKind);
#else
ctk::ast::v1::ArraySizeModifier array_modifier(clang::ArrayType::ArraySizeModifier);
ctk::ast::v1::VectorKind vector_kind(clang::VectorType::VectorKind);
#endif
ctk::ast::v1::UnaryTransformKind transform_kind(clang::UnaryTransformType::UTTKind);
ctk::ast::v1::FunctionCallingConvention calling_convention(clang::CallingConv);
ctk::ast::v1::ExceptionSpecification exception_specification(clang::ExceptionSpecificationType);
std::string attribute_name(clang::attr::Kind);
ctk::ast::v1::AttributedTypeKind attribute_kind(const clang::AttributedType &);
void write_attribute(const clang::Attr &, ctk::ast::v1::AttributeValue &, SerializationContext &);
void write_function_ext(const clang::FunctionType &, ctk::ast::v1::FunctionExtInfo &, SerializationContext &);
void write_function_proto_ext(const clang::FunctionProtoType &, ctk::ast::v1::FunctionProtoExtInfo &, SerializationContext &);

} // namespace ctk::clang_layer::serialization::type_helpers
