#include "namespace_alias_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool NamespaceAliasDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::NamespaceAliasDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_namespace_alias_decl();
  helpers::write_common(*native, *payload, context);
  helpers::write_symbol(*native->getNamespace(),
                        *payload->mutable_namespace_declaration(), context);
  helpers::write_symbol(*native->getAliasedNamespace(),
                        *payload->mutable_aliased_namespace(), context);
  helpers::write_nested_name(native->getQualifier(),
                             *payload->mutable_qualifier(), context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
