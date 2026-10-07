#include "if_stmt.hpp"
#include "../semantic_helpers.hpp"
#include <clang/AST/Attr.h>
#include <clang/AST/ParentMapContext.h>
namespace ctk::clang_layer::serialization {
bool IfStmtSerializer::serialize(const clang::DynTypedNode &node,
                                 ctk::match::v1::MatchBinding &binding,
                                 SerializationContext &context) const {
  const auto *native = node.get<clang::IfStmt>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_if_stmt();
  if (auto *child = native->getInit())
    helpers::write_stmt(child, *payload->mutable_init_statement(), context);
  if (auto *child = native->getConditionVariable())
    helpers::write_decl(child, *payload->mutable_condition_variable(), context);
  if (auto *child = native->getCond())
    helpers::write_expr(child, *payload->mutable_condition(), context);
  if (auto *child = native->getThen())
    helpers::write_stmt(child, *payload->mutable_then_statement(), context);
  if (auto *child = native->getElse())
    helpers::write_stmt(child, *payload->mutable_else_statement(), context);
  payload->set_is_constexpr(native->isConstexpr());
  payload->set_is_consteval(native->isConsteval());
  payload->set_is_negated_condition(native->isNegatedConsteval());
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
