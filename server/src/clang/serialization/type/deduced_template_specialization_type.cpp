#include "deduced_template_specialization_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool DeducedTemplateSpecializationTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
  const auto *native = node.get<clang::DeducedTemplateSpecializationType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_deduced_template_specialization_type();
  helpers::write_common(*native, *payload, context);
  helpers::write_template_name(native->getTemplateName(), *payload->mutable_template_name(), context);
  if (!native->getDeducedType().isNull())
    helpers::write_type(native->getDeducedType(), *payload->mutable_deduced_type(), context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
