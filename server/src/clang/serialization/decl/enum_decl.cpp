#include "enum_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool EnumDeclSerializer::serialize(const clang::DynTypedNode &node,
                                   ctk::match::v1::MatchBinding &binding,
                                   SerializationContext &context) const {
  const auto *native = node.get<clang::EnumDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_enum_decl();
  helpers::write_common(*native, *payload, context);
  if (!native->getIntegerType().isNull())
    helpers::write_type(native->getIntegerType(),
                        *payload->mutable_integer_type(), context);
  if (!native->getPromotionType().isNull())
    helpers::write_type(native->getPromotionType(),
                        *payload->mutable_promotion_type(), context);
  payload->set_is_scoped(native->isScoped());
  payload->set_is_fixed(native->isFixed());
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
