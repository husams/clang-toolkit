#include "type_alias_template_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool TypeAliasTemplateDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::TypeAliasTemplateDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_type_alias_template_decl();
  helpers::write_common(*native, *payload, context);
  helpers::write_decl(native->getTemplatedDecl(),
                      *payload->mutable_templated_declaration(), context);
  helpers::write_template_parameters(*native->getTemplateParameters(),
                                     *payload->mutable_template_parameters(),
                                     context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
