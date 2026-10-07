#include "seh_try_stmt.hpp"
#include "../semantic_helpers.hpp"
#include <clang/AST/Attr.h>
#include <clang/AST/ParentMapContext.h>
namespace ctk::clang_layer::serialization {
bool SEHTryStmtSerializer::serialize(const clang::DynTypedNode &node,
                                     ctk::match::v1::MatchBinding &binding,
                                     SerializationContext &context) const {
  const auto *native = node.get<clang::SEHTryStmt>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_seh_try_stmt();
  if (auto *child = native->getTryBlock())
    helpers::write_stmt(child, *payload->mutable_try_block(), context);
  if (auto *child = native->getHandler())
    helpers::write_stmt(child, *payload->mutable_handler(), context);
  payload->set_is_cxx_try(native->getIsCXXTry());
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
