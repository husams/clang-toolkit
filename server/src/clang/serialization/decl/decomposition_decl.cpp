#include "decomposition_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool DecompositionDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::DecompositionDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_decomposition_decl();
  helpers::write_common(*native, *payload, context);
  for (const auto *binding : native->bindings()) {
    if (!helpers::can_expand("decomposition_decl.bindings", context))
      break;
    helpers::write_decl(binding, *payload->add_bindings(), context);
  }
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
