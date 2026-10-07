#include "ext_vector_element_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool ExtVectorElementExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::ExtVectorElementExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_ext_vector_element_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getBase())
    helpers::write_expr(value, *payload->mutable_base(), context);
  payload->set_accessor(native->getAccessor().getName().str());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
