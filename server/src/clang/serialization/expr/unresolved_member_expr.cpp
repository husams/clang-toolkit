#include "unresolved_member_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool UnresolvedMemberExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::UnresolvedMemberExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_unresolved_member_expr();
  helpers::write_common(*native, *payload, context);
  helpers::write_name(native->getName(), *payload->mutable_name(), context);
  helpers::write_nested_name(native->getQualifier(),
                             *payload->mutable_qualifier(), context);
  for (const auto &argument : native->template_arguments()) {
    if (!helpers::can_expand(*payload, "template_arguments", context))
      break;
    helpers::write_template_argument(
        argument.getArgument(), *payload->add_template_arguments(), context);
  }
  for (const auto *declaration : native->decls()) {
    if (!helpers::can_expand(*payload, "candidate_declarations", context))
      break;
    helpers::write_symbol(*declaration, *payload->add_candidate_declarations(),
                          context);
  }
  if (!native->isImplicitAccess()) {
    if (auto *value = native->getBase())
      helpers::write_expr(value, *payload->mutable_base(), context);
  }
  payload->set_is_arrow(native->isArrow());
  payload->set_is_unqualified(!native->getQualifier());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
