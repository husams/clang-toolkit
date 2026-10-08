#include "var_template_partial_specialization_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool VarTemplatePartialSpecializationDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::VarTemplatePartialSpecializationDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()
                      ->mutable_var_template_partial_specialization_decl();
  helpers::write_common(*native, *payload, context);
  for (const auto &argument : native->getTemplateArgs().asArray()) {
    if (!helpers::can_expand(
            *payload, "template_arguments",
            context))
      break;
    helpers::write_template_argument(
        argument, *payload->add_template_arguments(), context);
  }
  helpers::write_symbol(*native->getSpecializedTemplate(),
                        *payload->mutable_specialized_template(), context);
  helpers::write_template_parameters(*native->getTemplateParameters(),
                                     *payload->mutable_template_parameters(),
                                     context);
  auto specialized = native->getSpecializedTemplateOrPartial();
  if (const auto *primary = specialized.dyn_cast<clang::VarTemplateDecl *>())
    helpers::write_symbol(
        *primary, *payload->mutable_specialized_template_or_partial(), context);
  else
    helpers::write_symbol(
        *specialized.get<clang::VarTemplatePartialSpecializationDecl *>(),
        *payload->mutable_specialized_template_or_partial(), context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
