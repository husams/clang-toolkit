#include "btf_tag_attributed_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool BTFTagAttributedTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
  const auto *native = node.get<clang::BTFTagAttributedType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_btf_tag_attributed_type();
  helpers::write_common(*native, *payload, context);
  helpers::write_type(native->getWrappedType(), *payload->mutable_wrapped_type(), context);
  if (native->getAttr()) type_helpers::write_attribute(*native->getAttr(), *payload->mutable_attribute(), context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
