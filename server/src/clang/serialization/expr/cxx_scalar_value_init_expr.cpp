#include "cxx_scalar_value_init_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool CXXScalarValueInitExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::CXXScalarValueInitExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_cxx_scalar_value_init_expr();
  helpers::write_common(*native, *payload, context);
  helpers::write_type(native->getType(), *payload->mutable_target_type(),
                      context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
