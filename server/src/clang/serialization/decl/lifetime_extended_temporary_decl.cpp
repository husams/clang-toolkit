#include "lifetime_extended_temporary_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool LifetimeExtendedTemporaryDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::LifetimeExtendedTemporaryDecl>();
  if (!native)
    return false;
  auto *payload =
      binding.mutable_node()->mutable_lifetime_extended_temporary_decl();
  helpers::write_common(*native, *payload, context);
  helpers::write_symbol(*native->getExtendingDecl(),
                        *payload->mutable_extending_declaration(), context);
  helpers::write_expr(native->getTemporaryExpr(),
                      *payload->mutable_temporary_expression(), context);
  payload->set_mangling_number(native->getManglingNumber());
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
