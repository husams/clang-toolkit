#include "coyield_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool CoyieldExprSerializer::serialize(const clang::DynTypedNode &node,
                                      ctk::match::v1::MatchBinding &binding,
                                      SerializationContext &context) const {
  const auto *native = node.get<clang::CoyieldExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_coyield_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getOperand())
    helpers::write_expr(value, *payload->mutable_operand(), context);
  if (auto *value = native->getCommonExpr())
    helpers::write_expr(value, *payload->mutable_promise_call(), context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
