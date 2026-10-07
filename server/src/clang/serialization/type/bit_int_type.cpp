#include "bit_int_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool BitIntTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
  const auto *native = node.get<clang::BitIntType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_bit_int_type();
  helpers::write_common(*native, *payload, context);
  payload->set_bit_width(native->getNumBits());
  payload->set_is_unsigned(native->isUnsigned());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
