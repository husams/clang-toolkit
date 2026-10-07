#include "subst_non_type_template_parm_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool SubstNonTypeTemplateParmExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::SubstNonTypeTemplateParmExpr>();
  if (!native)
    return false;
  auto *payload =
      binding.mutable_node()->mutable_subst_non_type_template_parm_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getParameter())
    helpers::write_symbol(*value, *payload->mutable_parameter(), context);
  if (auto *value = native->getReplacement())
    helpers::write_expr(value, *payload->mutable_replacement(), context);
  payload->set_parameter_index(native->getIndex());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
