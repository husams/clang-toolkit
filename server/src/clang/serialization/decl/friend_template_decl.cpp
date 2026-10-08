#include "friend_template_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool FriendTemplateDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::FriendTemplateDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_friend_template_decl();
  helpers::write_common(*native, *payload, context);
  for (unsigned index = 0; index < native->getNumTemplateParameters();
       ++index) {
    if (!helpers::can_expand(*payload, "template_parameters", context))
      break;
    helpers::write_template_parameters(*native->getTemplateParameterList(index),
                                       *payload->add_template_parameters(),
                                       context);
  }
  if (native->getFriendDecl())
    helpers::write_symbol(*native->getFriendDecl(),
                          *payload->mutable_friend_declaration(), context);
  if (native->getFriendType())
    helpers::write_type(native->getFriendType()->getType(),
                        *payload->mutable_friend_type(), context);
  payload->set_is_described_template(
      native->getFriendDecl() &&
      llvm::isa<clang::TemplateDecl>(native->getFriendDecl()));
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
