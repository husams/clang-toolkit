#include "builtin_template_decl.hpp"
#include "../declaration_helpers.hpp"
#include <clang/Basic/Builtins.h>

namespace ctk::clang_layer::serialization {
bool BuiltinTemplateDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::BuiltinTemplateDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_builtin_template_decl();
  helpers::write_common(*native, *payload, context);
  switch (native->getBuiltinTemplateKind()) {
#if CLANG_VERSION_MAJOR >= 19
  case clang::BTK__builtin_common_type:
    payload->set_builtin_kind(
        ctk::ast::v1::DECL_BUILTIN_TEMPLATE_KIND_COMMON_TYPE);
    break;
#endif
#if CLANG_VERSION_MAJOR >= 22
  case clang::BTK__builtin_dedup_pack:
    payload->set_builtin_kind(
        ctk::ast::v1::DECL_BUILTIN_TEMPLATE_KIND_DEDUP_PACK);
    break;
#endif
  case clang::BTK__make_integer_seq:
    payload->set_builtin_kind(
        ctk::ast::v1::DECL_BUILTIN_TEMPLATE_KIND_MAKE_INTEGER_SEQ);
    break;
  case clang::BTK__type_pack_element:
    payload->set_builtin_kind(
        ctk::ast::v1::DECL_BUILTIN_TEMPLATE_KIND_TYPE_PACK_ELEMENT);
    break;
  default:
    helpers::unavailable(*payload, "builtin_kind",
                         "builtin template kind is outside the C++ contract",
                         context);
    break;
  }
  helpers::write_template_parameters(*native->getTemplateParameters(),
                                     *payload->mutable_template_parameters(),
                                     context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
