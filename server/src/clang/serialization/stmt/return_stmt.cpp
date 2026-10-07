#include "return_stmt.hpp"
#include "../semantic_helpers.hpp"
#include <clang/AST/Attr.h>
#include <clang/AST/ParentMapContext.h>
namespace ctk::clang_layer::serialization {
bool ReturnStmtSerializer::serialize(const clang::DynTypedNode &node,
                                     ctk::match::v1::MatchBinding &binding,
                                     SerializationContext &context) const {
  const auto *native = node.get<clang::ReturnStmt>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_return_stmt();
  if (auto *child = native->getRetValue())
    helpers::write_expr(child, *payload->mutable_return_value(), context);
  if (const auto *candidate = native->getNRVOCandidate())
    helpers::write_symbol(*candidate, *payload->mutable_nrvo_candidate(),
                          context);
  helpers::unavailable(
      *payload, "return_value_init",
      "Clang ReturnStmt stores one return expression; a separate coroutine "
      "return-object initializer belongs to CoroutineBodyStmt",
      context);
  helpers::unavailable(*payload, "is_noreturn",
                       "Clang ReturnStmt has no noreturn property", context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
