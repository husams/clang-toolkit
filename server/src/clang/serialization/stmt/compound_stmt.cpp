#include "compound_stmt.hpp"
#include "../semantic_helpers.hpp"
#include <clang/AST/Attr.h>
#include <clang/AST/ParentMapContext.h>
namespace ctk::clang_layer::serialization {
bool CompoundStmtSerializer::serialize(const clang::DynTypedNode &node,
                                       ctk::match::v1::MatchBinding &binding,
                                       SerializationContext &context) const {
  const auto *native = node.get<clang::CompoundStmt>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_compound_stmt();
  for (const auto *stmt : native->body()) {
    if (!helpers::can_expand("CompoundStmt.body", context))
      break;
    if (stmt)
      helpers::write_stmt(stmt, *payload->add_body(), context);
  }
  bool statement_expression = false;
  for (const auto &parent : context.ast_context.getParents(*native))
    if (parent.get<clang::StmtExpr>()) {
      statement_expression = true;
      break;
    }
  payload->set_is_statement_expression(statement_expression);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
