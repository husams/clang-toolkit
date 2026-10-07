#include "cxx_method_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool CXXMethodDeclSerializer::serialize(const clang::DynTypedNode &node,
                                        ctk::match::v1::MatchBinding &binding,
                                        SerializationContext &context) const {
  const auto *native = node.get<clang::CXXMethodDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_cxx_method_decl();
  helpers::write_common(*native, *payload, context);

  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
