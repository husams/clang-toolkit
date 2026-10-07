#include "access_spec_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool AccessSpecDeclSerializer::serialize(const clang::DynTypedNode &node,
                                         ctk::match::v1::MatchBinding &binding,
                                         SerializationContext &context) const {
  const auto *native = node.get<clang::AccessSpecDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_access_spec_decl();
  helpers::write_common(*native, *payload, context);
  switch (native->getAccess()) {
  case clang::AS_public:
    payload->set_access(ctk::ast::v1::ACCESS_SPECIFIER_PUBLIC);
    break;
  case clang::AS_protected:
    payload->set_access(ctk::ast::v1::ACCESS_SPECIFIER_PROTECTED);
    break;
  case clang::AS_private:
    payload->set_access(ctk::ast::v1::ACCESS_SPECIFIER_PRIVATE);
    break;
  case clang::AS_none:
    payload->set_access(ctk::ast::v1::ACCESS_SPECIFIER_NONE);
    break;
  }
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
