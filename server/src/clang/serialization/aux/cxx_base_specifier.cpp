#include "cxx_base_specifier.hpp"

#include "../semantic_helpers.hpp"

namespace ctk::clang_layer::serialization {

bool CXXBaseSpecifierSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::CXXBaseSpecifier>();
  if (!native)
    return false;

  helpers::write_base(*native, *binding.mutable_base_specifier(), context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
