#include "coawait_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool CoawaitExprSerializer::serialize(const clang::DynTypedNode &node,
                                      ctk::match::v1::MatchBinding &binding,
                                      SerializationContext &context) const {
  const auto *native = node.get<clang::CoawaitExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_coawait_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getOperand())
    helpers::write_expr(value, *payload->mutable_operand(), context);
  if (auto *value = native->getReadyExpr())
    helpers::write_expr(value, *payload->mutable_ready_call(), context);
  if (auto *value = native->getSuspendExpr())
    helpers::write_expr(value, *payload->mutable_suspend_call(), context);
  if (auto *value = native->getResumeExpr())
    helpers::write_expr(value, *payload->mutable_resume_call(), context);
  helpers::unavailable(
      "is_ready",
      "Await readiness is a runtime result, not a stored Clang AST fact",
      context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
