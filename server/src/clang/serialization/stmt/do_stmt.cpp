#include "do_stmt.hpp"
#include "../semantic_helpers.hpp"
#include <clang/AST/Attr.h>
#include <clang/AST/ParentMapContext.h>
namespace ctk::clang_layer::serialization {
bool DoStmtSerializer::serialize(const clang::DynTypedNode &node,
                                 ctk::match::v1::MatchBinding &binding,
                                 SerializationContext &context) const {
  const auto *native = node.get<clang::DoStmt>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_do_stmt();
  if (auto *child = native->getBody())
    helpers::write_stmt(child, *payload->mutable_body(), context);
  if (auto *child = native->getCond())
    helpers::write_expr(child, *payload->mutable_condition(), context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
