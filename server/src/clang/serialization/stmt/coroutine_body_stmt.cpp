#include "coroutine_body_stmt.hpp"
#include "../semantic_helpers.hpp"
#include <clang/AST/Attr.h>
#include <clang/AST/ParentMapContext.h>
namespace ctk::clang_layer::serialization {
bool CoroutineBodyStmtSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::CoroutineBodyStmt>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_coroutine_body_stmt();
  if (auto *child = native->getBody())
    helpers::write_stmt(child, *payload->mutable_body(), context);
  if (auto *child = native->getPromiseDecl())
    helpers::write_decl(child, *payload->mutable_promise_declaration(),
                        context);
  if (auto *child = native->getReturnValue())
    helpers::write_expr(child, *payload->mutable_return_value(), context);
  if (auto *child = native->getExceptionHandler())
    helpers::write_stmt(child, *payload->mutable_exception_handler(), context);
  if (auto *child = native->getFallthroughHandler())
    helpers::write_stmt(child, *payload->mutable_fallthrough_handler(),
                        context);
  for (const auto *stmt : native->getParamMoves()) {
    if (!helpers::can_expand(*payload, "parameter_moves", context))
      break;
    if (stmt)
      helpers::write_stmt(stmt, *payload->add_parameter_moves(), context);
  }
  if (auto *expr = native->getAllocate())
    helpers::write_expr(expr, *payload->add_allocation_expressions(), context);
  if (auto *expr = native->getDeallocate())
    helpers::write_expr(expr, *payload->add_deallocation_expressions(),
                        context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
