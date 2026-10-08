#include "subst_non_type_template_parm_pack_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool SubstNonTypeTemplateParmPackExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::SubstNonTypeTemplateParmPackExpr>();
  if (!native)
    return false;
  auto *payload =
      binding.mutable_node()->mutable_subst_non_type_template_parm_pack_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getParameterPack())
    helpers::write_symbol(*value, *payload->mutable_parameter_pack(), context);
  for (const auto &argument : native->getArgumentPack().pack_elements()) {
    if (!helpers::can_expand(*payload, "template_arguments", context))
      break;

    helpers::write_template_argument(
        argument, *payload->add_template_arguments(), context);
    if (argument.getKind() == clang::TemplateArgument::Expression)
      helpers::write_expr(argument.getAsExpr(), *payload->add_arguments(),
                          context);
  }
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
