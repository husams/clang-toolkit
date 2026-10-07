#include "choose_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool ChooseExprSerializer::serialize(const clang::DynTypedNode &node,
                                     ctk::match::v1::MatchBinding &binding,
                                     SerializationContext &context) const {
  const auto *native = node.get<clang::ChooseExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_choose_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getCond())
    helpers::write_expr(value, *payload->mutable_condition(), context);
  if (auto *value = native->getLHS())
    helpers::write_expr(value, *payload->mutable_left_expression(), context);
  if (auto *value = native->getRHS())
    helpers::write_expr(value, *payload->mutable_right_expression(), context);
  if (!native->isConditionDependent())
    payload->set_is_condition_true(native->isConditionTrue());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
