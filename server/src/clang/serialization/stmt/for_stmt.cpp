#include "for_stmt.hpp"
#include "../semantic_helpers.hpp"
#include <clang/AST/Attr.h>
#include <clang/AST/ParentMapContext.h>
namespace ctk::clang_layer::serialization {
bool ForStmtSerializer::serialize(const clang::DynTypedNode &node,
                                  ctk::match::v1::MatchBinding &binding,
                                  SerializationContext &context) const {
  const auto *native = node.get<clang::ForStmt>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_for_stmt();
  if (auto *child = native->getInit())
    helpers::write_stmt(child, *payload->mutable_init_statement(), context);
  if (auto *child = native->getConditionVariable())
    helpers::write_decl(child, *payload->mutable_condition_variable(), context);
  if (auto *child = native->getCond())
    helpers::write_expr(child, *payload->mutable_condition(), context);
  if (auto *child = native->getInc())
    helpers::write_expr(child, *payload->mutable_increment(), context);
  if (auto *child = native->getBody())
    helpers::write_stmt(child, *payload->mutable_body(), context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
