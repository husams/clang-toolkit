#include "cxx_destructor_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool CXXDestructorDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::CXXDestructorDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_cxx_destructor_decl();
  helpers::write_common(*native, *payload, context);
  payload->set_is_trivial(native->isTrivial());
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
