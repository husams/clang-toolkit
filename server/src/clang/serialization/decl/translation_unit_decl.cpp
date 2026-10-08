#include "translation_unit_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool TranslationUnitDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::TranslationUnitDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_translation_unit_decl();
  helpers::write_common(*native, *payload, context);
  for (const auto *declaration : native->decls()) {
    if (!helpers::can_expand(*payload, "declarations", context))
      break;
    helpers::write_decl(declaration, *payload->add_declarations(), context);
  }
  if (native->getAnonymousNamespace())
    helpers::write_symbol(*native->getAnonymousNamespace(),
                          *payload->mutable_anonymous_namespace(), context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
