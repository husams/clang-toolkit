#include "array_init_loop_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool ArrayInitLoopExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::ArrayInitLoopExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_array_init_loop_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getCommonExpr())
    helpers::write_expr(value, *payload->mutable_common_expression(), context);
  if (auto *value = native->getSubExpr())
    helpers::write_expr(value, *payload->mutable_initializer_per_element(),
                        context);
  helpers::write_apint(native->getArraySize(), *payload->mutable_array_size());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
