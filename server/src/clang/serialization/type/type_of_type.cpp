#include "type_of_type.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
// Source: installed Clang AST/Type.h (Clang 22 delegates to AST/TypeBase.h).
namespace ctk::clang_layer::serialization {

bool TypeOfTypeSerializer::serialize(const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding, SerializationContext &context) const {
  const auto *native = node.get<clang::TypeOfType>();
  if (!native) return false;
  auto *payload = binding.mutable_node()->mutable_type_of_type();
  helpers::write_common(*native, *payload, context);
  helpers::write_type(native->getUnmodifiedType(), *payload->mutable_underlying_type(), context);
  payload->set_kind(native->getKind() == clang::TypeOfKind::Unqualified ? ctk::ast::v1::TYPE_OF_KIND_UNQUALIFIED : ctk::ast::v1::TYPE_OF_KIND_QUALIFIED);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
