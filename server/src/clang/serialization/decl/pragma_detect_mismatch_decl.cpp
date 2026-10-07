#include "pragma_detect_mismatch_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool PragmaDetectMismatchDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::PragmaDetectMismatchDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_pragma_detect_mismatch_decl();
  helpers::write_common(*native, *payload, context);
  payload->set_name(native->getName().str());
  payload->set_value(native->getValue().str());
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
