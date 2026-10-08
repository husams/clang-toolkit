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
  const auto destination_type = native->getType();
  if (const auto *destination = destination_type->getAs<clang::VectorType>()) {
    helpers::write_type(destination->getElementType(),
                        *payload->mutable_destination_element_type(), context);
  } else if (const auto *destination =
                 destination_type->getAs<clang::DependentVectorType>()) {
    helpers::write_type(destination->getElementType(),
                        *payload->mutable_destination_element_type(), context);
  } else if (const auto *destination =
                 destination_type
                     ->getAs<clang::DependentSizedExtVectorType>()) {
    helpers::write_type(destination->getElementType(),
                        *payload->mutable_destination_element_type(), context);
  } else {
    // ExprInfo carries the full result type, including dependent template
    // types. Some dependent vector forms still expose their element type above.
    helpers::unavailable(*payload, "destination_element_type",
                         "destination type has no concrete vector element type",
                         context);
  }
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
