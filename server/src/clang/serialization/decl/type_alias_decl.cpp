#include "type_alias_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool TypeAliasDeclSerializer::serialize(const clang::DynTypedNode &node,
                                        ctk::match::v1::MatchBinding &binding,
                                        SerializationContext &context) const {
  const auto *native = node.get<clang::TypeAliasDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_type_alias_decl();
  helpers::write_common(*native, *payload, context);
  helpers::write_type(native->getUnderlyingType(),
                      *payload->mutable_underlying_type(), context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
