#include "implicit_concept_specialization_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool ImplicitConceptSpecializationDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::ImplicitConceptSpecializationDecl>();
  if (!native)
    return false;
  auto *payload =
      binding.mutable_node()->mutable_implicit_concept_specialization_decl();
  helpers::write_common(*native, *payload, context);
  for (const auto &argument : native->getTemplateArguments()) {
    if (!helpers::can_expand(
            "implicit_concept_specialization_decl.template_arguments", context))
      break;
    helpers::write_template_argument(
        argument, *payload->add_template_arguments(), context);
  }
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
