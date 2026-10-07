#include "function_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool FunctionDeclSerializer::serialize(const clang::DynTypedNode &node,
                                       ctk::match::v1::MatchBinding &binding,
                                       SerializationContext &context) const {
  const auto *native = node.get<clang::FunctionDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_function_decl();
  helpers::write_common(*native, *payload, context);
  payload->set_is_deleted(native->isDeleted());
  payload->set_is_defaulted(native->isDefaulted());
  payload->set_is_explicitly_defaulted(native->isExplicitlyDefaulted());
  payload->set_is_pure_virtual(native->isPureVirtual());
  payload->set_is_trivial(native->isTrivial());
  payload->set_is_trivial_for_call(native->isTrivialForCall());
  payload->set_is_inline_specified(native->isInlineSpecified());
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
