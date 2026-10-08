#include "linkage_spec_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool LinkageSpecDeclSerializer::serialize(const clang::DynTypedNode &node,
                                          ctk::match::v1::MatchBinding &binding,
                                          SerializationContext &context) const {
  const auto *native = node.get<clang::LinkageSpecDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_linkage_spec_decl();
  helpers::write_common(*native, *payload, context);
  payload->set_language(static_cast<int>(native->getLanguage()) == 1
                            ? ctk::ast::v1::DECL_LINKAGE_LANGUAGE_C
                            : ctk::ast::v1::DECL_LINKAGE_LANGUAGE_CXX);
  for (const auto *declaration : native->decls()) {
    if (!helpers::can_expand(*payload, "declarations", context))
      break;
    helpers::write_decl(declaration, *payload->add_declarations(), context);
  }
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
