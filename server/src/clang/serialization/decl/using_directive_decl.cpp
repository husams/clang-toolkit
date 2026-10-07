#include "using_directive_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool UsingDirectiveDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::UsingDirectiveDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_using_directive_decl();
  helpers::write_common(*native, *payload, context);
  helpers::write_symbol(*native->getNominatedNamespace(),
                        *payload->mutable_nominated_namespace(), context);
  if (const auto *alias = llvm::dyn_cast<clang::NamespaceAliasDecl>(
          native->getNominatedNamespaceAsWritten()))
    helpers::write_symbol(*alias, *payload->mutable_nominated_namespace_alias(),
                          context);
  if (const auto *scope = llvm::dyn_cast<clang::NamedDecl>(
          clang::Decl::castFromDeclContext(native->getCommonAncestor())))
    helpers::write_symbol(*scope, *payload->mutable_common_ancestor(), context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
