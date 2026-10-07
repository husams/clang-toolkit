#include "dependent_scope_decl_ref_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool DependentScopeDeclRefExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::DependentScopeDeclRefExpr>();
  if (!native)
    return false;
  auto *payload =
      binding.mutable_node()->mutable_dependent_scope_decl_ref_expr();
  helpers::write_common(*native, *payload, context);
  helpers::write_name(native->getDeclName(), *payload->mutable_name(), context);
  helpers::write_nested_name(native->getQualifier(),
                             *payload->mutable_qualifier(), context);
  for (const auto &argument : native->template_arguments()) {
    if (!helpers::can_expand("template_arguments", context))
      break;
    helpers::write_template_argument(
        argument.getArgument(), *payload->add_template_arguments(), context);
  }
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
