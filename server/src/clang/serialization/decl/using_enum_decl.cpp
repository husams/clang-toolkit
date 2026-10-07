#include "using_enum_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool UsingEnumDeclSerializer::serialize(const clang::DynTypedNode &node,
                                        ctk::match::v1::MatchBinding &binding,
                                        SerializationContext &context) const {
  const auto *native = node.get<clang::UsingEnumDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_using_enum_decl();
  helpers::write_common(*native, *payload, context);
  helpers::write_symbol(*native->getEnumDecl(),
                        *payload->mutable_enum_declaration(), context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
