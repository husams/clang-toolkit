#include "cxx_dynamic_cast_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool CXXDynamicCastExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::CXXDynamicCastExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_cxx_dynamic_cast_expr();
  helpers::write_cast(*native, *payload->mutable_cast(), context);
  helpers::write_type(native->getTypeAsWritten(),
                      *payload->mutable_target_type(), context);
  payload->set_is_always_null(native->isAlwaysNull());
  helpers::unavailable(
      "is_always_success",
      "Clang exposes an always-null test but no always-success semantic fact",
      context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
