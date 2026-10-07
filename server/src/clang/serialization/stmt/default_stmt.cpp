#include "default_stmt.hpp"
#include "../semantic_helpers.hpp"
#include <clang/AST/Attr.h>
#include <clang/AST/ParentMapContext.h>
namespace ctk::clang_layer::serialization {
bool DefaultStmtSerializer::serialize(const clang::DynTypedNode &node,
                                      ctk::match::v1::MatchBinding &binding,
                                      SerializationContext &context) const {
  const auto *native = node.get<clang::DefaultStmt>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_default_stmt();
  if (auto *child = native->getSubStmt())
    helpers::write_stmt(child, *payload->mutable_substatement(), context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
