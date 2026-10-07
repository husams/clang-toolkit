#include "case_stmt.hpp"
#include "../semantic_helpers.hpp"
#include <clang/AST/Attr.h>
#include <clang/AST/ParentMapContext.h>
namespace ctk::clang_layer::serialization {
bool CaseStmtSerializer::serialize(const clang::DynTypedNode &node,
                                   ctk::match::v1::MatchBinding &binding,
                                   SerializationContext &context) const {
  const auto *native = node.get<clang::CaseStmt>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_case_stmt();
  if (auto *child = native->getLHS())
    helpers::write_expr(child, *payload->mutable_left_expression(), context);
  if (auto *child = native->getRHS())
    helpers::write_expr(child, *payload->mutable_right_expression(), context);
  if (auto *child = native->getSubStmt())
    helpers::write_stmt(child, *payload->mutable_substatement(), context);
  payload->set_is_case_range(native->getRHS() != nullptr);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
