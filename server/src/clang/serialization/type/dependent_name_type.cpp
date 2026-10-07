#include "dependent_name_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool DependentNameTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
  const auto *native = node.get<clang::DependentNameType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_dependent_name_type();
  helpers::write_common(*native, *payload, context);
  helpers::write_nested_name(native->getQualifier(), *payload->mutable_qualifier(), context);
  if (native->getIdentifier()) payload->set_identifier(native->getIdentifier()->getName().str());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
