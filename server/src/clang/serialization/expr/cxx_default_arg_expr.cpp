#include "cxx_default_arg_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool CXXDefaultArgExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::CXXDefaultArgExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_cxx_default_arg_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getParam())
    helpers::write_symbol(*value, *payload->mutable_parameter(), context);
  if (auto *value = native->getExpr())
    helpers::write_expr(value, *payload->mutable_expression(), context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
