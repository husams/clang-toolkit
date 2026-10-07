#include "static_assert_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool StaticAssertDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::StaticAssertDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_static_assert_decl();
  helpers::write_common(*native, *payload, context);
  helpers::write_expr(native->getAssertExpr(),
                      *payload->mutable_assertion_expression(), context);
  if (native->getMessage())
    helpers::write_expr(native->getMessage(),
                        *payload->mutable_message_expression(), context);
  payload->set_is_failed(native->isFailed());
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
