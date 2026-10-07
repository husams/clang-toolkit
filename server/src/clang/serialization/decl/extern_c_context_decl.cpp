#include "extern_c_context_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool ExternCContextDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::ExternCContextDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_extern_c_context_decl();
  helpers::write_common(*native, *payload, context);
  for (const auto *declaration : native->decls()) {
    if (!helpers::can_expand("extern_c_context_decl.declarations", context))
      break;
    helpers::write_decl(declaration, *payload->add_declarations(), context);
  }
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
