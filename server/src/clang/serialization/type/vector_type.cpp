#include "vector_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool VectorTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
  const auto *native = node.get<clang::VectorType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_vector_type();
  helpers::write_common(*native, *payload, context);
  helpers::write_type(native->getElementType(), *payload->mutable_element_type(), context);
  payload->set_element_count(native->getNumElements());
  payload->set_vector_kind(type_helpers::vector_kind(native->getVectorKind()));
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
