#include "seh_finally_stmt.hpp"
#include "../semantic_helpers.hpp"
#include <clang/AST/Attr.h>
#include <clang/AST/ParentMapContext.h>
namespace ctk::clang_layer::serialization {
bool SEHFinallyStmtSerializer::serialize(const clang::DynTypedNode &node,
                                         ctk::match::v1::MatchBinding &binding,
                                         SerializationContext &context) const {
  const auto *native = node.get<clang::SEHFinallyStmt>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_seh_finally_stmt();
  if (auto *child = native->getBlock())
    helpers::write_stmt(child, *payload->mutable_block(), context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
