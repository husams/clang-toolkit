#include "cxx_record_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool CXXRecordDeclSerializer::serialize(const clang::DynTypedNode &node,
                                        ctk::match::v1::MatchBinding &binding,
                                        SerializationContext &context) const {
  const auto *native = node.get<clang::CXXRecordDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_cxx_record_decl();
  helpers::write_common(*native, *payload, context);
  if (const auto *definition = native->getDefinition()) {
    for (const auto &base : definition->bases()) {
      if (!helpers::can_expand("cxx_record_decl.definition_bases", context))
        break;
      helpers::write_base(base, *payload->add_definition_bases(), context);
    }
    for (const auto *friend_decl : definition->friends()) {
      if (!helpers::can_expand("cxx_record_decl.friends", context))
        break;
      helpers::write_decl(friend_decl, *payload->add_friends(), context);
    }
    payload->set_is_structural(definition->isStructural());
  }
  payload->set_is_lambda(native->isLambda());
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
