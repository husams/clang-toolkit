#include "namespace_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool NamespaceDeclSerializer::serialize(const clang::DynTypedNode &node,
                                        ctk::match::v1::MatchBinding &binding,
                                        SerializationContext &context) const {
  const auto *native = node.get<clang::NamespaceDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_namespace_decl();
  helpers::write_common(*native, *payload, context);
  helpers::write_symbol(*native->getCanonicalDecl(),
                        *payload->mutable_original_namespace(), context);
  if (native->getAnonymousNamespace())
    helpers::write_symbol(*native->getAnonymousNamespace(),
                          *payload->mutable_anonymous_namespace(), context);
  payload->set_is_inline(native->isInline());
  payload->set_is_anonymous(native->isAnonymousNamespace());
  for (const auto *declaration : native->decls()) {
    if (!helpers::can_expand("namespace_decl.declarations", context))
      break;
    helpers::write_decl(declaration, *payload->add_declarations(), context);
  }
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
