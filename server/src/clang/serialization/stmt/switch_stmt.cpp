#include "switch_stmt.hpp"
#include "../semantic_helpers.hpp"
#include <clang/AST/Attr.h>
#include <clang/AST/ParentMapContext.h>
namespace ctk::clang_layer::serialization {
bool SwitchStmtSerializer::serialize(const clang::DynTypedNode &node,
                                     ctk::match::v1::MatchBinding &binding,
                                     SerializationContext &context) const {
  const auto *native = node.get<clang::SwitchStmt>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_switch_stmt();
  if (auto *child = native->getConditionVariable())
    helpers::write_decl(child, *payload->mutable_condition_variable(), context);
  if (auto *child = native->getCond())
    helpers::write_expr(child, *payload->mutable_condition(), context);
  if (auto *child = native->getBody())
    helpers::write_stmt(child, *payload->mutable_body(), context);
  for (const auto *item = native->getSwitchCaseList(); item;
       item = item->getNextSwitchCase())
    if (auto *d = llvm::dyn_cast<clang::DefaultStmt>(item)) {
      helpers::write_stmt(d, *payload->mutable_default_case(), context);
      break;
    }
  payload->set_is_constexpr(false);
  payload->set_is_all_enum_cases_covered(native->isAllEnumCasesCovered());
  helpers::finish_binding(binding, context);
  return true;
}
} // namespace ctk::clang_layer::serialization
