#include "pack_indexing_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool PackIndexingExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::PackIndexingExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_pack_indexing_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getPackIdExpression())
    helpers::write_expr(value, *payload->mutable_pack_expression(), context);
  if (auto *value = native->getPackDecl())
    helpers::write_symbol(*value, *payload->mutable_pack_declaration(),
                          context);
  if (auto *value = native->getIndexExpr())
    helpers::write_expr(value, *payload->mutable_index_expression(), context);
  if (auto index = native->getSelectedIndex()) {
    payload->set_selected_index(*index);
    helpers::write_expr(native->getSelectedExpr(),
                        *payload->mutable_selected_expression(), context);
  }
  for (const auto *value : native->getExpressions()) {
    if (!helpers::can_expand(*payload, "substituted_expressions", context))
      break;
    helpers::write_expr(value, *payload->add_substituted_expressions(),
                        context);
  }
  payload->set_is_fully_substituted(native->isFullySubstituted());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
