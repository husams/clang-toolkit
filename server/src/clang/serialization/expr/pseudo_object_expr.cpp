#include "pseudo_object_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool PseudoObjectExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::PseudoObjectExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_pseudo_object_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getSyntacticForm())
    helpers::write_expr(value, *payload->mutable_syntax_expression(), context);
  for (const auto *value : native->semantics()) {
    if (!helpers::can_expand(*payload, "semantic_expressions", context))
      break;
    helpers::write_expr(value, *payload->add_semantic_expressions(), context);
  }
  if (auto *value = native->getResultExpr())
    helpers::write_expr(value, *payload->mutable_result_expression(), context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
