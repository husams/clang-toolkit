#include "friend_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool FriendDeclSerializer::serialize(const clang::DynTypedNode &node,
                                     ctk::match::v1::MatchBinding &binding,
                                     SerializationContext &context) const {
  const auto *native = node.get<clang::FriendDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_friend_decl();
  helpers::write_common(*native, *payload, context);
  if (native->getFriendDecl())
    helpers::write_symbol(*native->getFriendDecl(),
                          *payload->mutable_friend_declaration(), context);
  if (native->getFriendType())
    helpers::write_type(native->getFriendType()->getType(),
                        *payload->mutable_friend_type(), context);
  payload->set_is_pack_expansion(native->isPackExpansion());
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
