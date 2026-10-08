#include "indirect_field_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool IndirectFieldDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::IndirectFieldDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_indirect_field_decl();
  helpers::write_common(*native, *payload, context);
  for (const auto *declaration : native->chain()) {
    if (!helpers::can_expand(*payload, "chain", context))
      break;
    helpers::write_symbol(*declaration, *payload->add_chain(), context);
  }
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
