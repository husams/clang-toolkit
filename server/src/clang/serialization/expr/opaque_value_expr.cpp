#include "opaque_value_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool OpaqueValueExprSerializer::serialize(const clang::DynTypedNode &node,
                                          ctk::match::v1::MatchBinding &binding,
                                          SerializationContext &context) const {
  const auto *native = node.get<clang::OpaqueValueExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_opaque_value_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getSourceExpr())
    helpers::write_expr(value, *payload->mutable_source_expression(), context);
  helpers::write_type(native->getType(), *payload->mutable_opaque_type(),
                      context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
