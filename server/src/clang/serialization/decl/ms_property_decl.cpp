#include "ms_property_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool MSPropertyDeclSerializer::serialize(const clang::DynTypedNode &node,
                                         ctk::match::v1::MatchBinding &binding,
                                         SerializationContext &context) const {
  const auto *native = node.get<clang::MSPropertyDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_ms_property_decl();
  helpers::write_common(*native, *payload, context);
  if (native->getGetterId())
    payload->set_getter_identifier(native->getGetterId()->getName().str());
  if (native->getSetterId())
    payload->set_setter_identifier(native->getSetterId()->getName().str());
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
