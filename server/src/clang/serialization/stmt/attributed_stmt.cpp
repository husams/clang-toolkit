#include "attributed_stmt.hpp"
#include "../semantic_helpers.hpp"
#include "../type_helpers.hpp"
#include <clang/AST/Attr.h>
#include <clang/AST/ParentMapContext.h>
namespace ctk::clang_layer::serialization {
bool AttributedStmtSerializer::serialize(const clang::DynTypedNode &node,
                                         ctk::match::v1::MatchBinding &binding,
                                         SerializationContext &context) const {
  const auto *native = node.get<clang::AttributedStmt>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_attributed_stmt();
  for (const auto *attr : native->getAttrs()) {
    if (!helpers::can_expand(*payload, "attributes", context))
      break;
    type_helpers::write_attribute(*attr, *payload->add_attributes(), context);
  }
  if (auto *child = native->getSubStmt())
    helpers::write_stmt(child, *payload->mutable_substatement(), context);
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
