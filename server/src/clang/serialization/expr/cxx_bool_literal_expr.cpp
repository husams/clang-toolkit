#include "cxx_bool_literal_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool CXXBoolLiteralExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::CXXBoolLiteralExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_cxx_bool_literal_expr();
  helpers::write_common(*native, *payload, context);
  payload->set_value(native->getValue());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
