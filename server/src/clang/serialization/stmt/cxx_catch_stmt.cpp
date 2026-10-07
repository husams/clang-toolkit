#include "cxx_catch_stmt.hpp"
#include "../semantic_helpers.hpp"
#include <clang/AST/Attr.h>
#include <clang/AST/ParentMapContext.h>
namespace ctk::clang_layer::serialization {
bool CXXCatchStmtSerializer::serialize(const clang::DynTypedNode &node,
                                       ctk::match::v1::MatchBinding &binding,
                                       SerializationContext &context) const {
  const auto *native = node.get<clang::CXXCatchStmt>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_cxx_catch_stmt();
  if (auto *child = native->getExceptionDecl())
    helpers::write_decl(child, *payload->mutable_exception_declaration(),
                        context);
  if (auto *child = native->getHandlerBlock())
    helpers::write_stmt(child, *payload->mutable_handler_block(), context);
  payload->set_is_catch_all(native->getExceptionDecl() == nullptr);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
