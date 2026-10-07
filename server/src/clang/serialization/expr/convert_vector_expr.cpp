#include "convert_vector_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool ConvertVectorExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::ConvertVectorExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_convert_vector_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getSrcExpr())
    helpers::write_expr(value, *payload->mutable_operand(), context);
  helpers::write_type(
      native->getType()->castAs<clang::VectorType>()->getElementType(),
      *payload->mutable_destination_element_type(), context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
