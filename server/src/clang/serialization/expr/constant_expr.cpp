#include "constant_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool ConstantExprSerializer::serialize(const clang::DynTypedNode &node,
                                       ctk::match::v1::MatchBinding &binding,
                                       SerializationContext &context) const {
  const auto *native = node.get<clang::ConstantExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_constant_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getSubExpr())
    helpers::write_expr(value, *payload->mutable_subexpression(), context);
  if (native->hasAPValueResult()) {
    helpers::write_apvalue(native->getAPValueResult(),
                           *payload->mutable_value(), native->getType(),
                           context);
    payload->set_result_kind(ctk::ast::v1::CONSTANT_EXPR_RESULT_SUCCEEDED);
  } else
    payload->set_result_kind(ctk::ast::v1::CONSTANT_EXPR_RESULT_NOT_EVALUATED);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
