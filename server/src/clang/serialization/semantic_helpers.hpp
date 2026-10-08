#pragma once
#include "node_serializers.hpp"
#include <clang/AST/APValue.h>
#include <llvm/ADT/APFixedPoint.h>
#include <llvm/ADT/APFloat.h>

namespace ctk::clang_layer::serialization::helpers {
void write_common(const clang::Decl &, google::protobuf::Message &,
                  SerializationContext &);
void write_common(const clang::Stmt &, google::protobuf::Message &,
                  SerializationContext &);
void write_common(const clang::Type &, google::protobuf::Message &,
                  SerializationContext &);
bool can_expand(const std::string &field_path, SerializationContext &);
bool can_expand(const google::protobuf::Message &owner,
                const std::string &field,
                SerializationContext &);
class ExpansionFrame {
public:
  SerializationContext &context;
  bool allowed;
  ExpansionFrame(const std::string &field_path, SerializationContext &);
  ~ExpansionFrame();
  ExpansionFrame(const ExpansionFrame &) = delete;
  ExpansionFrame &operator=(const ExpansionFrame &) = delete;
};
void finish_binding(ctk::match::v1::MatchBinding &, SerializationContext &);
void unavailable(const std::string &field, const std::string &reason,
                 SerializationContext &);
void unavailable(google::protobuf::Message &, const std::string &field,
                 const std::string &reason, SerializationContext &);
void write_decl(const clang::Decl *, ctk::ast::v1::DeclarationValue &,
                SerializationContext &);
void write_stmt(const clang::Stmt *, ctk::ast::v1::StatementValue &,
                SerializationContext &);
void write_expr(const clang::Expr *, ctk::ast::v1::ExpressionValue &,
                SerializationContext &);
void write_type(clang::QualType, ctk::ast::v1::QualType &,
                SerializationContext &);
void write_type_value(clang::QualType, ctk::ast::v1::TypeValue &,
                      SerializationContext &);
void write_type_description(clang::QualType, ctk::ast::v1::TypeDescription &,
                            SerializationContext &);
void write_qualifiers(clang::Qualifiers, ctk::ast::v1::Qualifiers &);
void write_apint(const llvm::APInt &, ctk::ast::v1::APIntBits &);
void write_apsint(const llvm::APSInt &, ctk::ast::v1::APSIntBits &);
void write_apfloat(const llvm::APFloat &, ctk::ast::v1::APFloatBits &);
void write_apfixed(const llvm::APFixedPoint &,
                   ctk::ast::v1::APFixedPointBits &);
void write_apvalue(const clang::APValue &, ctk::ast::v1::APValue &,
                   clang::QualType, SerializationContext &);
inline void write_apvalue(const clang::APValue &n, ctk::ast::v1::APValue &p,
                          SerializationContext &c) {
  write_apvalue(n, p, {}, c);
}
void write_symbol(const clang::NamedDecl &, ctk::ast::v1::DeclarationSymbol &,
                  SerializationContext &);
void write_template_argument(const clang::TemplateArgument &,
                             ctk::ast::v1::TemplateArgument &,
                             SerializationContext &);
void write_template_name(clang::TemplateName, ctk::ast::v1::TemplateName &,
                         SerializationContext &);
void write_declaration_name(clang::DeclarationName,
                            ctk::ast::v1::DeclarationName &,
                            SerializationContext &);
inline void write_name(clang::DeclarationName n,
                       ctk::ast::v1::DeclarationName &p,
                       SerializationContext &c) {
  write_declaration_name(n, p, c);
}
#if CLANG_VERSION_MAJOR >= 22
void write_nested_name(clang::NestedNameSpecifier,
                       ctk::ast::v1::NestedNameSpecifier &,
                       SerializationContext &);
#else
void write_nested_name(const clang::NestedNameSpecifier *,
                       ctk::ast::v1::NestedNameSpecifier &,
                       SerializationContext &);
#endif
void write_base(const clang::CXXBaseSpecifier &,
                ctk::ast::v1::CXXBaseSpecifier &, SerializationContext &);
void write_concept_reference(const clang::ConceptReference &,
                             ctk::ast::v1::ConceptReference &,
                             SerializationContext &);
} // namespace ctk::clang_layer::serialization::helpers
