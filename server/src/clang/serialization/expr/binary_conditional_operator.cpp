#include "binary_conditional_operator.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool BinaryConditionalOperatorSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::BinaryConditionalOperator>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_binary_conditional_operator();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getCommon())
    helpers::write_expr(value, *payload->mutable_common(), context);
  if (auto *value = native->getCond())
    helpers::write_expr(value, *payload->mutable_condition(), context);
  if (auto *value = native->getTrueExpr())
    helpers::write_expr(value, *payload->mutable_true_expression(), context);
  if (auto *value = native->getFalseExpr())
    helpers::write_expr(value, *payload->mutable_false_expression(), context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
