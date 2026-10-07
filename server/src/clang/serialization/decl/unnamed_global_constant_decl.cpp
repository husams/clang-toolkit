#include "unnamed_global_constant_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool UnnamedGlobalConstantDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::UnnamedGlobalConstantDecl>();
  if (!native)
    return false;
  auto *payload =
      binding.mutable_node()->mutable_unnamed_global_constant_decl();
  helpers::write_common(*native, *payload, context);
  helpers::write_apvalue(native->getValue(),
                         *payload->mutable_value_as_constant(),
                         native->getType(), context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
