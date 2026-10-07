#include "label_stmt.hpp"
#include "../semantic_helpers.hpp"
#include <clang/AST/Attr.h>
#include <clang/AST/ParentMapContext.h>
namespace ctk::clang_layer::serialization {
bool LabelStmtSerializer::serialize(const clang::DynTypedNode &node,
                                    ctk::match::v1::MatchBinding &binding,
                                    SerializationContext &context) const {
  const auto *native = node.get<clang::LabelStmt>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_label_stmt();
  helpers::write_symbol(*native->getDecl(), *payload->mutable_declaration(),
                        context);
  if (auto *child = native->getSubStmt())
    helpers::write_stmt(child, *payload->mutable_substatement(), context);
  helpers::unavailable(*payload, "is_gnu_asm_label",
                       "Clang retains GNU local-label and MS asm-label flags, "
                       "but no GNU asm-label flag on LabelStmt",
                       context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
