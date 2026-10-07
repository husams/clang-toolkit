#include "constructor_using_shadow_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool ConstructorUsingShadowDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::ConstructorUsingShadowDecl>();
  if (!native)
    return false;
  auto *payload =
      binding.mutable_node()->mutable_constructor_using_shadow_decl();
  auto *shadow = payload->mutable_using_shadow();
  helpers::write_named_info(*native, *shadow->mutable_named(), context);
  helpers::write_symbol(*native->getTargetDecl(),
                        *shadow->mutable_target_declaration(), context);
  helpers::write_symbol(*native->getIntroducer(), *shadow->mutable_introducer(),
                        context);
  helpers::write_symbol(*native->getNominatedBaseClass(),
                        *payload->mutable_nominated_base_class(), context);
  helpers::write_symbol(*native->getConstructedBaseClass(),
                        *payload->mutable_constructed_base_class(), context);
  payload->set_constructs_virtual_base(native->constructsVirtualBase());
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
