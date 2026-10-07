#include "seh_leave_stmt.hpp"
#include "../semantic_helpers.hpp"
#include <clang/AST/Attr.h>
#include <clang/AST/ParentMapContext.h>
namespace ctk::clang_layer::serialization {
bool SEHLeaveStmtSerializer::serialize(const clang::DynTypedNode &node,
                                       ctk::match::v1::MatchBinding &binding,
                                       SerializationContext &context) const {
  const auto *native = node.get<clang::SEHLeaveStmt>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_seh_leave_stmt();
  (void)payload;
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
