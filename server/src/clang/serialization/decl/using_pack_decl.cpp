#include "using_pack_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool UsingPackDeclSerializer::serialize(const clang::DynTypedNode &node,
                                        ctk::match::v1::MatchBinding &binding,
                                        SerializationContext &context) const {
  const auto *native = node.get<clang::UsingPackDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_using_pack_decl();
  helpers::write_common(*native, *payload, context);
  helpers::write_symbol(*native->getInstantiatedFromUsingDecl(),
                        *payload->mutable_using_declaration(), context);
  for (const auto *expansion : native->expansions()) {
    if (!helpers::can_expand(*payload, "expansions", context))
      break;
    helpers::write_symbol(*expansion, *payload->add_expansions(), context);
  }
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
