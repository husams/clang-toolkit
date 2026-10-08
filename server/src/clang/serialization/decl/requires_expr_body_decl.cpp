#include "requires_expr_body_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool RequiresExprBodyDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::RequiresExprBodyDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_requires_expr_body_decl();
  helpers::write_common(*native, *payload, context);
  for (const auto *declaration : native->decls()) {
    if (!helpers::can_expand(*payload, "local_parameters", context))
      break;
    if (llvm::isa<clang::ParmVarDecl>(declaration))
      helpers::write_decl(declaration, *payload->add_local_parameters(),
                          context);
  }
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
