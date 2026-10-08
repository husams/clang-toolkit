#include "decl_stmt.hpp"
#include "../semantic_helpers.hpp"
#include <clang/AST/Attr.h>
#include <clang/AST/ParentMapContext.h>
namespace ctk::clang_layer::serialization {
bool DeclStmtSerializer::serialize(const clang::DynTypedNode &node,
                                   ctk::match::v1::MatchBinding &binding,
                                   SerializationContext &context) const {
  const auto *native = node.get<clang::DeclStmt>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_decl_stmt();
  for (const auto *decl : native->decls()) {
    if (!helpers::can_expand(*payload, "declarations", context))
      break;
    helpers::write_decl(decl, *payload->add_declarations(), context);
  }
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
