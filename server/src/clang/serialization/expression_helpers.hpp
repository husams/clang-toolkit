#pragma once
#include "node_serializers.hpp"
namespace ctk::clang_layer::serialization::helpers {
void write_expr_info(const clang::Expr &, ctk::ast::v1::ExprInfo &,
                     SerializationContext &);
void write_call(const clang::CallExpr &, ctk::ast::v1::CallExprInfo &,
                SerializationContext &);
void write_cast(const clang::CastExpr &, ctk::ast::v1::CastExprInfo &,
                SerializationContext &);
void write_construction(const clang::CXXConstructExpr &,
                        ctk::ast::v1::CXXConstructExprInfo &,
                        SerializationContext &);
ctk::ast::v1::UnaryOpcode unary_opcode(clang::UnaryOperatorKind);
ctk::ast::v1::BinaryOpcode binary_opcode(clang::BinaryOperatorKind);
ctk::ast::v1::OverloadedOperatorKind
    overloaded_operator(clang::OverloadedOperatorKind);
ctk::ast::v1::AtomicOpcode atomic_opcode(clang::AtomicExpr::AtomicOp);
const char *atomic_name(clang::AtomicExpr::AtomicOp);
} // namespace ctk::clang_layer::serialization::helpers
