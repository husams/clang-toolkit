#include "coreturn_stmt.hpp"
#include "../semantic_helpers.hpp"
#include <clang/AST/Attr.h>
#include <clang/AST/ParentMapContext.h>
namespace ctk::clang_layer::serialization {
bool CoreturnStmtSerializer::serialize(const clang::DynTypedNode &node,
                                       ctk::match::v1::MatchBinding &binding,
                                       SerializationContext &context) const {
  const auto *native = node.get<clang::CoreturnStmt>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_coreturn_stmt();
  if (auto *child = native->getOperand())
    helpers::write_expr(child, *payload->mutable_operand(), context);
  if (auto *child = native->getPromiseCall())
    helpers::write_expr(child, *payload->mutable_promise_call(), context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
