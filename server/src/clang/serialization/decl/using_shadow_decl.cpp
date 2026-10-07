#include "using_shadow_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool UsingShadowDeclSerializer::serialize(const clang::DynTypedNode &node,
                                          ctk::match::v1::MatchBinding &binding,
                                          SerializationContext &context) const {
  const auto *native = node.get<clang::UsingShadowDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_using_shadow_decl();
  helpers::write_common(*native, *payload, context);
  helpers::write_symbol(*native->getTargetDecl(),
                        *payload->mutable_target_declaration(), context);
  helpers::write_symbol(*native->getIntroducer(),
                        *payload->mutable_introducer(), context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
