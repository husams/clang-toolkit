#include "pointer_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool PointerTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
  const auto *native = node.get<clang::PointerType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_pointer_type();
  helpers::write_common(*native, *payload, context);
  helpers::write_type(native->getPointeeType(), *payload->mutable_pointee_type(), context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
