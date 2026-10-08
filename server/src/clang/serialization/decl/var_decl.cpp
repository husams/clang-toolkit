#include "var_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool VarDeclSerializer::serialize(const clang::DynTypedNode &node,
                                  ctk::match::v1::MatchBinding &binding,
                                  SerializationContext &context) const {
  const auto *native = node.get<clang::VarDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_var_decl();
  helpers::write_common(*native, *payload, context);
  switch (native->getTLSKind()) {
  case clang::VarDecl::TLS_None:
    payload->set_tls_kind(ctk::ast::v1::DECL_VARIABLE_TLS_KIND_NONE);
    break;
  case clang::VarDecl::TLS_Static:
    payload->set_tls_kind(ctk::ast::v1::DECL_VARIABLE_TLS_KIND_STATIC);
    break;
  case clang::VarDecl::TLS_Dynamic:
    payload->set_tls_kind(ctk::ast::v1::DECL_VARIABLE_TLS_KIND_DYNAMIC);
    break;
  }
  switch (native->getInitStyle()) {
  case clang::VarDecl::CInit:
    payload->set_initialization_style(
        ctk::ast::v1::DECL_VARIABLE_INITIALIZATION_STYLE_C);
    break;
  case clang::VarDecl::CallInit:
    payload->set_initialization_style(
        ctk::ast::v1::DECL_VARIABLE_INITIALIZATION_STYLE_CALL);
    break;
  case clang::VarDecl::ListInit:
    payload->set_initialization_style(
        ctk::ast::v1::DECL_VARIABLE_INITIALIZATION_STYLE_LIST);
    break;
#if CLANG_VERSION_MAJOR >= 19
  case clang::VarDecl::ParenListInit:
    payload->set_initialization_style(
        ctk::ast::v1::DECL_VARIABLE_INITIALIZATION_STYLE_PAREN_LIST);
    break;
#endif
  }
  payload->set_is_static_data_member(native->isStaticDataMember());
  if (helpers::can_expand(*payload, "initializer_from_any_declaration", context))
    if (const auto *initializer = native->getAnyInitializer())
      helpers::write_expr(initializer,
                          *payload->mutable_initializer_from_any_declaration(),
                          context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
