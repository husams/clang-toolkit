#include "block_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool BlockDeclSerializer::serialize(const clang::DynTypedNode &node,
                                    ctk::match::v1::MatchBinding &binding,
                                    SerializationContext &context) const {
  const auto *native = node.get<clang::BlockDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_block_decl();
  helpers::write_common(*native, *payload, context);
  for (const auto *parameter : native->parameters()) {
    if (!helpers::can_expand("block_decl.parameters", context))
      break;
    helpers::write_decl(parameter, *payload->add_parameters(), context);
  }
  if (native->getBody())
    helpers::write_stmt(native->getBody(), *payload->mutable_body(), context);
  for (const auto &capture : native->captures()) {
    if (!helpers::can_expand("block_decl.captures", context))
      break;

    auto *value = payload->add_captures();
    helpers::write_symbol(*capture.getVariable(), *value->mutable_variable(),
                          context);
    value->set_is_by_ref(capture.isByRef());
    value->set_is_nested(capture.isNested());
    if (capture.getCopyExpr())
      helpers::write_expr(capture.getCopyExpr(),
                          *value->mutable_copy_expression(), context);
  }
  payload->set_is_variadic(native->isVariadic());
  if (native->getSignatureAsWritten())
    helpers::write_type(native->getSignatureAsWritten()->getType(),
                        *payload->mutable_signature(), context);
  else
    helpers::unavailable(
        *payload, "signature",
        "Clang does not retain a signature TypeSourceInfo for this block",
        context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
