#include "template_template_parm_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool TemplateTemplateParmDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::TemplateTemplateParmDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_template_template_parm_decl();
  helpers::write_common(*native, *payload, context);
  helpers::write_template_parameters(*native->getTemplateParameters(),
                                     *payload->mutable_template_parameters(),
                                     context);
  payload->set_depth(native->getDepth());
  payload->set_position(native->getPosition());
  payload->set_is_parameter_pack(native->isParameterPack());
  payload->set_default_argument_was_inherited(
      native->defaultArgumentWasInherited());
  if (native->hasDefaultArgument())
    helpers::write_default_argument(
        *native, *payload->mutable_default_argument(), context);
  payload->set_is_expanded_parameter_pack(native->isExpandedParameterPack());
  if (native->isExpandedParameterPack())
    for (unsigned index = 0;
         index < native->getNumExpansionTemplateParameters(); ++index) {
      if (!helpers::can_expand(
              *payload, "expanded_template_parameters",
              context))
        break;
      helpers::write_template_parameters(
          *native->getExpansionTemplateParameters(index),
          *payload->add_expanded_template_parameters(), context);
    }
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
