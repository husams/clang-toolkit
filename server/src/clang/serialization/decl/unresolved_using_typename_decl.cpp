#include "unresolved_using_typename_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool UnresolvedUsingTypenameDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::UnresolvedUsingTypenameDecl>();
  if (!native)
    return false;
  auto *payload =
      binding.mutable_node()->mutable_unresolved_using_typename_decl();
  helpers::write_common(*native, *payload, context);
  helpers::write_nested_name(native->getQualifier(),
                             *payload->mutable_qualifier(), context);
  helpers::write_name(native->getDeclName(), *payload->mutable_target_name(),
                      context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
