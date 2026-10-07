#include "implicit_param_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool ImplicitParamDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::ImplicitParamDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_implicit_param_decl();
  helpers::write_common(*native, *payload, context);
  helpers::unavailable(
      *payload, "parameter_index",
      "ImplicitParamDecl stores parameter kind, not a function parameter index",
      context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
