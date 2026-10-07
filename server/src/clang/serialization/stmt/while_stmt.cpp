#include "while_stmt.hpp"
#include "../semantic_helpers.hpp"
#include <clang/AST/Attr.h>
#include <clang/AST/ParentMapContext.h>
namespace ctk::clang_layer::serialization {
bool WhileStmtSerializer::serialize(const clang::DynTypedNode &node,
                                    ctk::match::v1::MatchBinding &binding,
                                    SerializationContext &context) const {
  const auto *native = node.get<clang::WhileStmt>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_while_stmt();
  if (auto *child = native->getConditionVariable())
    helpers::write_decl(child, *payload->mutable_condition_variable(), context);
  if (auto *child = native->getCond())
    helpers::write_expr(child, *payload->mutable_condition(), context);
  if (auto *child = native->getBody())
    helpers::write_stmt(child, *payload->mutable_body(), context);
  payload->set_is_constexpr(false);
  bool constant_condition;
  if (native->getCond() && !native->getCond()->isValueDependent() &&
      native->getCond()->EvaluateAsBooleanCondition(constant_condition,
                                                    context.ast_context))
    payload->set_is_condition_false(!constant_condition);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
