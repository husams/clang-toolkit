#include "top_level_stmt_decl.hpp"
#include "../declaration_helpers.hpp"

namespace ctk::clang_layer::serialization {
bool TopLevelStmtDeclSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::TopLevelStmtDecl>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_top_level_stmt_decl();
  helpers::write_common(*native, *payload, context);
  if (native->getStmt())
    helpers::write_stmt(native->getStmt(), *payload->mutable_statement(),
                        context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
