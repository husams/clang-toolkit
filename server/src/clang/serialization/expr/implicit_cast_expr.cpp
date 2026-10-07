#include "implicit_cast_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool ImplicitCastExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::ImplicitCastExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_implicit_cast_expr();
  helpers::write_cast(*native, *payload->mutable_cast(), context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
