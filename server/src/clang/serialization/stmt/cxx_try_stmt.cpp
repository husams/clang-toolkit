#include "cxx_try_stmt.hpp"
#include "../semantic_helpers.hpp"
#include <clang/AST/Attr.h>
#include <clang/AST/ParentMapContext.h>
namespace ctk::clang_layer::serialization {
bool CXXTryStmtSerializer::serialize(const clang::DynTypedNode &node,
                                     ctk::match::v1::MatchBinding &binding,
                                     SerializationContext &context) const {
  const auto *native = node.get<clang::CXXTryStmt>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_cxx_try_stmt();
  if (auto *child = native->getTryBlock())
    helpers::write_stmt(child, *payload->mutable_try_block(), context);
  for (unsigned i = 0; i < native->getNumHandlers(); ++i) {
    if (!helpers::can_expand("CXXTryStmt.handlers", context))
      break;
    helpers::write_stmt(native->getHandler(i), *payload->add_handlers(),
                        context);
  }
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
