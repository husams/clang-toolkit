#include "array_init_index_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool ArrayInitIndexExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::ArrayInitIndexExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_array_init_index_expr();
  helpers::write_common(*native, *payload, context);
  payload->set_is_array_init_index(true);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
