#include "template_specialization_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool TemplateSpecializationTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
  const auto *native = node.get<clang::TemplateSpecializationType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_template_specialization_type();
  helpers::write_common(*native, *payload, context);
  helpers::write_template_name(native->getTemplateName(), *payload->mutable_template_name(), context);
  for (const auto &argument : native->template_arguments()) {
    if (!helpers::can_expand(*payload, "arguments", context)) break;
    helpers::write_template_argument(argument, *payload->add_arguments(), context);
  }
  payload->set_has_alias(native->isTypeAlias());
  if (native->isTypeAlias()) helpers::write_type(native->getAliasedType(), *payload->mutable_aliased_type(), context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
