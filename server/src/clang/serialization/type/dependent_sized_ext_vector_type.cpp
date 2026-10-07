#include "dependent_sized_ext_vector_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool DependentSizedExtVectorTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
  const auto *native = node.get<clang::DependentSizedExtVectorType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_dependent_sized_ext_vector_type();
  helpers::write_common(*native, *payload, context);
  helpers::write_type(native->getElementType(), *payload->mutable_element_type(), context);
  helpers::write_expr(native->getSizeExpr(), *payload->mutable_size_expression(), context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
