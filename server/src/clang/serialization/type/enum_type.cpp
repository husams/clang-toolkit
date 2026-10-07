#include "enum_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool EnumTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
  const auto *native = node.get<clang::EnumType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_enum_type();
  helpers::write_common(*native, *payload, context);
  helpers::write_symbol(*native->getDecl(), *payload->mutable_declaration(), context);
#if CLANG_VERSION_MAJOR >= 22
  helpers::write_nested_name(native->getQualifier(), *payload->mutable_qualifier(), context);
#else
  helpers::unavailable(*payload, "qualifier", "this Clang version does not retain a qualifier on this type node", context);
#endif
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
