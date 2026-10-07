#pragma once

#include "semantic_helpers.hpp"

namespace ctk::clang_layer::serialization::helpers {
void write_decl_info(const clang::Decl &, ctk::ast::v1::DeclInfo &,
                     SerializationContext &);
void write_named_info(const clang::NamedDecl &, ctk::ast::v1::NamedDeclInfo &,
                      SerializationContext &);
void write_value_info(const clang::ValueDecl &, ctk::ast::v1::ValueDeclInfo &,
                      SerializationContext &);
void write_declarator_info(const clang::DeclaratorDecl &,
                           ctk::ast::v1::DeclaratorDeclInfo &,
                           SerializationContext &);
void write_function_info(const clang::FunctionDecl &,
                         ctk::ast::v1::FunctionDeclInfo &,
                         SerializationContext &);
void write_method_info(const clang::CXXMethodDecl &,
                       ctk::ast::v1::CXXMethodDeclInfo &,
                       SerializationContext &);
void write_var_info(const clang::VarDecl &, ctk::ast::v1::VarDeclInfo &,
                    SerializationContext &);
void write_type_decl_info(const clang::TypeDecl &, ctk::ast::v1::TypeDeclInfo &,
                          SerializationContext &);
void write_tag_info(const clang::TagDecl &, ctk::ast::v1::TagDeclInfo &,
                    SerializationContext &);
void write_record_info(const clang::RecordDecl &,
                       ctk::ast::v1::RecordDeclInfo &, SerializationContext &);
void write_template_parameters(const clang::TemplateParameterList &,
                               ctk::ast::v1::TemplateParameterList &,
                               SerializationContext &);
void write_type_constraint(const clang::TypeConstraint &,
                           ctk::ast::v1::TypeConstraint &,
                           SerializationContext &);
void write_signature(const clang::FunctionDecl &,
                     ctk::ast::v1::FunctionSignature &, SerializationContext &);

// Template defaults changed representation in Clang 22. Both branches read the
// semantic argument, while discarding its TypeLoc/source-location wrapper.
template <class Parameter>
void write_default_argument(const Parameter &native,
                            ctk::ast::v1::TemplateArgument &payload,
                            SerializationContext &context) {
  if constexpr (requires { native.getDefaultArgument().getArgument(); })
    write_template_argument(native.getDefaultArgument().getArgument(), payload,
                            context);
  else if constexpr (requires {
                       clang::TemplateArgument(native.getDefaultArgument());
                     })
    write_template_argument(
        clang::TemplateArgument(native.getDefaultArgument()), payload, context);
  else
    write_template_argument(
        clang::TemplateArgument(native.getDefaultArgument()->getType()),
        payload, context);
}
} // namespace ctk::clang_layer::serialization::helpers
