#include "constant_array_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool ConstantArrayTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
  const auto *native = node.get<clang::ConstantArrayType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_constant_array_type();
  helpers::write_common(*native, *payload, context);
  helpers::write_type(native->getElementType(), *payload->mutable_element_type(), context);
  payload->set_size_modifier(type_helpers::array_modifier(native->getSizeModifier()));
  helpers::write_qualifiers(native->getIndexTypeQualifiers(), *payload->mutable_index_qualifiers());
  if (native->getSizeExpr()) helpers::write_expr(native->getSizeExpr(), *payload->mutable_size_expression(), context);
  helpers::write_apint(native->getSize(), *payload->mutable_size());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
