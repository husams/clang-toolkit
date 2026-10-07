#include "attributed_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool AttributedTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
  const auto *native = node.get<clang::AttributedType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_attributed_type();
  helpers::write_common(*native, *payload, context);
  helpers::write_type(native->getModifiedType(), *payload->mutable_modified_type(), context);
  helpers::write_type(native->getEquivalentType(), *payload->mutable_equivalent_type(), context);
  payload->set_attribute_kind(type_helpers::attribute_kind(*native));
  payload->set_attribute_kind_name(type_helpers::attribute_name(native->getAttrKind()));
#if CLANG_VERSION_MAJOR >= 22
  if (native->getAttr()) type_helpers::write_attribute(*native->getAttr(), *payload->mutable_attribute(), context);
  else {
    payload->mutable_attribute()->set_clang_class(type_helpers::attribute_name(native->getAttrKind()));
    payload->mutable_attribute()->set_state(ctk::ast::v1::FIELD_STATE_UNAVAILABLE);
    payload->mutable_attribute()->set_reason("native attributed type has no attribute object");
    helpers::unavailable(*payload, "attribute", "native attributed type has no attribute object", context);
  }
#else
  payload->mutable_attribute()->set_clang_class(type_helpers::attribute_name(native->getAttrKind()));
  payload->mutable_attribute()->set_state(ctk::ast::v1::FIELD_STATE_UNAVAILABLE);
  payload->mutable_attribute()->set_reason("this Clang version does not retain a type attribute object");
  helpers::unavailable(*payload, "attribute", "this Clang version does not retain a type attribute object", context);
#endif
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
