#include "indirect_goto_stmt.hpp"
#include "../semantic_helpers.hpp"
#include <clang/AST/Attr.h>
#include <clang/AST/ParentMapContext.h>
namespace ctk::clang_layer::serialization {
bool IndirectGotoStmtSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::IndirectGotoStmt>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_indirect_goto_stmt();
  if (auto *child = native->getTarget())
    helpers::write_expr(child, *payload->mutable_target_expression(), context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
