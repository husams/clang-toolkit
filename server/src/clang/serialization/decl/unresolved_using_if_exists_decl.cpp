#include "unresolved_using_if_exists_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool UnresolvedUsingIfExistsDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::UnresolvedUsingIfExistsDecl>();
  if (!native)
    return false;
  auto *payload =
      binding.mutable_node()->mutable_unresolved_using_if_exists_decl();
  helpers::write_common(*native, *payload, context);
  helpers::write_name(native->getDeclName(), *payload->mutable_target_name(),
                      context);
  helpers::unavailable(*payload, "qualifier",
                       "UnresolvedUsingIfExistsDecl stores the declaration "
                       "name but not its qualifier",
                       context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
