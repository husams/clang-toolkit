#include "label_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool LabelDeclSerializer::serialize(const clang::DynTypedNode &node,
                                    ctk::match::v1::MatchBinding &binding,
                                    SerializationContext &context) const {
  const auto *native = node.get<clang::LabelDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_label_decl();
  helpers::write_common(*native, *payload, context);
  if (native->getStmt())
    helpers::write_stmt(native->getStmt(), *payload->mutable_statement(),
                        context);
  payload->set_is_gnu_local(native->isGnuLocal());
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
