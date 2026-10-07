#include "ms_property_ref_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool MSPropertyRefExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::MSPropertyRefExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_ms_property_ref_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getBaseExpr())
    helpers::write_expr(value, *payload->mutable_base(), context);
  if (auto *value = native->getPropertyDecl())
    helpers::write_symbol(*value, *payload->mutable_property(), context);
  payload->set_is_arrow(native->isArrow());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
