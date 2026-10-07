#include "predefined_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool PredefinedExprSerializer::serialize(const clang::DynTypedNode &node,
                                         ctk::match::v1::MatchBinding &binding,
                                         SerializationContext &context) const {
  const auto *native = node.get<clang::PredefinedExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_predefined_expr();
  helpers::write_common(*native, *payload, context);
  switch (native->getIdentKind()) {
  case clang::PredefinedIdentKind::Func:
    payload->set_identifier_kind(ctk::ast::v1::PREDEFINED_IDENT_KIND_FUNC);
    break;
  case clang::PredefinedIdentKind::Function:
    payload->set_identifier_kind(ctk::ast::v1::PREDEFINED_IDENT_KIND_FUNCTION);
    break;
  case clang::PredefinedIdentKind::PrettyFunction:
    payload->set_identifier_kind(
        ctk::ast::v1::PREDEFINED_IDENT_KIND_PRETTY_FUNCTION);
    break;
  default:
    payload->set_identifier_kind(ctk::ast::v1::PREDEFINED_IDENT_KIND_OTHER);
    break;
  }
  if (auto *literal = native->getFunctionName())
    payload->set_literal_bytes(literal->getBytes().str());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
