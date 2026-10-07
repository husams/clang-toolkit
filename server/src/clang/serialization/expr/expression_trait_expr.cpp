#include "expression_trait_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool ExpressionTraitExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::ExpressionTraitExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_expression_trait_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getQueriedExpression())
    helpers::write_expr(value, *payload->mutable_queried_expression(), context);
  switch (native->getTrait()) {
  case clang::ET_IsLValueExpr:
    payload->set_trait(ctk::ast::v1::EXPRESSION_TRAIT_IS_LVALUE);
    break;
  case clang::ET_IsRValueExpr:
    payload->set_trait(ctk::ast::v1::EXPRESSION_TRAIT_IS_PRVALUE);
    break;
  default:
    payload->set_trait(ctk::ast::v1::EXPRESSION_TRAIT_OTHER);
    break;
  }
  if (!native->isValueDependent())
    payload->set_trait_value(native->getValue());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
