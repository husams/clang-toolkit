#include "using_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool UsingDeclSerializer::serialize(const clang::DynTypedNode &node,
                                    ctk::match::v1::MatchBinding &binding,
                                    SerializationContext &context) const {
  const auto *native = node.get<clang::UsingDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_using_decl();
  helpers::write_common(*native, *payload, context);
  helpers::write_nested_name(native->getQualifier(),
                             *payload->mutable_qualifier(), context);
  helpers::write_name(native->getDeclName(), *payload->mutable_name(), context);
  for (const auto *shadow : native->shadows()) {
    if (!helpers::can_expand("using_decl.shadows", context))
      break;
    helpers::write_symbol(*shadow, *payload->add_shadows(), context);
  }
  payload->set_is_access_declaration(native->isAccessDeclaration());
  payload->set_has_typename(native->hasTypename());
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
