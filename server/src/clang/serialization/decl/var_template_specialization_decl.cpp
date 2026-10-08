#include "var_template_specialization_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool VarTemplateSpecializationDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::VarTemplateSpecializationDecl>();
  if (!native)
    return false;
  auto *payload =
      binding.mutable_node()->mutable_var_template_specialization_decl();
  helpers::write_common(*native, *payload, context);
  for (const auto &argument : native->getTemplateArgs().asArray()) {
    if (!helpers::can_expand(
            *payload, "template_arguments", context))
      break;
    helpers::write_template_argument(
        argument, *payload->add_template_arguments(), context);
  }
  helpers::write_symbol(*native->getSpecializedTemplate(),
                        *payload->mutable_specialized_template(), context);
  switch (native->getSpecializationKind()) {
  case clang::TSK_Undeclared:
    payload->set_specialization_kind(
        ctk::ast::v1::DECL_TEMPLATE_SPECIALIZATION_KIND_UNDECLARED);
    break;
  case clang::TSK_ImplicitInstantiation:
    payload->set_specialization_kind(
        ctk::ast::v1::DECL_TEMPLATE_SPECIALIZATION_KIND_IMPLICIT_INSTANTIATION);
    break;
  case clang::TSK_ExplicitSpecialization:
    payload->set_specialization_kind(
        ctk::ast::v1::
            DECL_TEMPLATE_SPECIALIZATION_KIND_EXPLICIT_SPECIALIZATION);
    break;
  case clang::TSK_ExplicitInstantiationDeclaration:
    payload->set_specialization_kind(
        ctk::ast::v1::
            DECL_TEMPLATE_SPECIALIZATION_KIND_EXPLICIT_INSTANTIATION_DECLARATION);
    break;
  case clang::TSK_ExplicitInstantiationDefinition:
    payload->set_specialization_kind(
        ctk::ast::v1::
            DECL_TEMPLATE_SPECIALIZATION_KIND_EXPLICIT_INSTANTIATION_DEFINITION);
    break;
  }
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
