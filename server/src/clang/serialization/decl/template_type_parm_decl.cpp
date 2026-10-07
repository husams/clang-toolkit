#include "template_type_parm_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool TemplateTypeParmDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::TemplateTypeParmDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_template_type_parm_decl();
  helpers::write_common(*native, *payload, context);
  payload->set_depth(native->getDepth());
  payload->set_position(native->getIndex());
  payload->set_is_parameter_pack(native->isParameterPack());
  payload->set_default_argument_was_inherited(
      native->defaultArgumentWasInherited());
  if (native->hasDefaultArgument())
    helpers::write_default_argument(
        *native, *payload->mutable_default_argument(), context);
  if (native->getTypeConstraint())
    helpers::write_type_constraint(*native->getTypeConstraint(),
                                   *payload->mutable_type_constraint(),
                                   context);
  payload->set_is_pack_expansion(native->isPackExpansion());
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
