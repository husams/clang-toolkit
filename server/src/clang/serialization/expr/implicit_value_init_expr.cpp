#include "implicit_value_init_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool ImplicitValueInitExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::ImplicitValueInitExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_implicit_value_init_expr();
  helpers::write_common(*native, *payload, context);
  helpers::write_type(native->getType(), *payload->mutable_initialized_type(),
                      context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
