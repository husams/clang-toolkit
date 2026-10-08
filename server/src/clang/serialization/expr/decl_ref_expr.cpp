#include "decl_ref_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool DeclRefExprSerializer::serialize(const clang::DynTypedNode &node,
                                      ctk::match::v1::MatchBinding &binding,
                                      SerializationContext &context) const {
  const auto *native = node.get<clang::DeclRefExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_decl_ref_expr();
  helpers::write_common(*native, *payload, context);
  helpers::write_name(native->getNameInfo().getName(), *payload->mutable_name(),
                      context);
  helpers::write_nested_name(native->getQualifier(),
                             *payload->mutable_qualifier(), context);
  for (const auto &argument : native->template_arguments()) {
    if (!helpers::can_expand(*payload, "template_arguments", context))
      break;
    helpers::write_template_argument(
        argument.getArgument(), *payload->add_template_arguments(), context);
  }
  if (auto *value = native->getDecl())
    helpers::write_symbol(*value, *payload->mutable_declaration(), context);
  payload->set_is_non_odr_use(native->isNonOdrUse() != clang::NOUR_None);
  payload->set_has_explicit_template_arguments(
      native->hasExplicitTemplateArgs());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
