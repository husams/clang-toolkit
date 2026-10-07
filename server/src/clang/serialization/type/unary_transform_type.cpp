#include "unary_transform_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool UnaryTransformTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
  const auto *native = node.get<clang::UnaryTransformType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_unary_transform_type();
  helpers::write_common(*native, *payload, context);
  helpers::write_type(native->getBaseType(), *payload->mutable_base_type(), context);
  helpers::write_type(native->getUnderlyingType(), *payload->mutable_transformed_type(), context);
  payload->set_transform_kind(type_helpers::transform_kind(native->getUTTKind()));
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
