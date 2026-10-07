#include "enum_constant_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool EnumConstantDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::EnumConstantDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_enum_constant_decl();
  helpers::write_common(*native, *payload, context);
  if (native->getInitExpr())
    helpers::write_expr(native->getInitExpr(), *payload->mutable_initializer(),
                        context);
  helpers::write_apsint(native->getInitVal(),
                        *payload->mutable_evaluated_value());
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
