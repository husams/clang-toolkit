#include "binding_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool BindingDeclSerializer::serialize(const clang::DynTypedNode &node,
                                      ctk::match::v1::MatchBinding &binding,
                                      SerializationContext &context) const {
  const auto *native = node.get<clang::BindingDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_binding_decl();
  helpers::write_common(*native, *payload, context);
  if (native->getHoldingVar())
    helpers::write_symbol(*native->getHoldingVar(),
                          *payload->mutable_holding_variable(), context);
  if (native->getBinding())
    helpers::write_expr(native->getBinding(), *payload->mutable_binding(),
                        context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
