#include "unresolved_lookup_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool UnresolvedLookupExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::UnresolvedLookupExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_unresolved_lookup_expr();
  helpers::write_common(*native, *payload, context);
  helpers::write_name(native->getName(), *payload->mutable_name(), context);
  helpers::write_nested_name(native->getQualifier(),
                             *payload->mutable_qualifier(), context);
  for (const auto &argument : native->template_arguments()) {
    if (!helpers::can_expand("template_arguments", context))
      break;
    helpers::write_template_argument(
        argument.getArgument(), *payload->add_template_arguments(), context);
  }
  for (const auto *declaration : native->decls()) {
    if (!helpers::can_expand("candidate_declarations", context))
      break;
    helpers::write_symbol(*declaration, *payload->add_candidate_declarations(),
                          context);
  }
  payload->set_requires_adl(native->requiresADL());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
