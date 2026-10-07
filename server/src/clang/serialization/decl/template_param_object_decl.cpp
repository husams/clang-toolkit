#include "template_param_object_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool TemplateParamObjectDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::TemplateParamObjectDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_template_param_object_decl();
  helpers::write_common(*native, *payload, context);
  helpers::write_apvalue(native->getValue(),
                         *payload->mutable_value_as_constant(),
                         native->getType(), context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
