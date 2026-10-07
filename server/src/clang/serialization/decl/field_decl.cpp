#include "field_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool FieldDeclSerializer::serialize(const clang::DynTypedNode &node,
                                    ctk::match::v1::MatchBinding &binding,
                                    SerializationContext &context) const {
  const auto *native = node.get<clang::FieldDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_field_decl();
  helpers::write_common(*native, *payload, context);
  if (native->getBitWidth())
    helpers::write_expr(native->getBitWidth(), *payload->mutable_bit_width(),
                        context);
  if (native->hasInClassInitializer())
    helpers::write_expr(native->getInClassInitializer(),
                        *payload->mutable_in_class_initializer(), context);
  payload->set_is_mutable(native->isMutable());
  payload->set_is_bit_field(native->isBitField());
  payload->set_is_anonymous_struct_or_union(native->isAnonymousStructOrUnion());
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
