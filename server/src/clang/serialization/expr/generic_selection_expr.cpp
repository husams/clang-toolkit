#include "generic_selection_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool GenericSelectionExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::GenericSelectionExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_generic_selection_expr();
  helpers::write_common(*native, *payload, context);
#if CLANG_VERSION_MAJOR >= 21
  if (native->isExprPredicate()) {
    helpers::write_expr(native->getControllingExpr(),
                        *payload->mutable_controlling_expression(), context);
  } else {
    helpers::write_type(native->getControllingType()->getType(),
                        *payload->mutable_controlling_type(), context);
  }
#else
  helpers::write_expr(native->getControllingExpr(),
                      *payload->mutable_controlling_expression(), context);
#endif
  if (!native->isResultDependent()) {
    helpers::write_expr(native->getResultExpr(),
                        *payload->mutable_result_expression(), context);
    payload->set_selected_index(native->getResultIndex());
  }
  for (unsigned i = 0; i < native->getNumAssocs(); ++i) {
    if (!helpers::can_expand("associations", context))
      break;

    const auto association = native->getAssociation(i);
    auto *target = payload->add_associations();
    if (!association.getType().isNull())
      helpers::write_type(association.getType(), *target->mutable_type(),
                          context);
    helpers::write_expr(association.getAssociationExpr(),
                        *target->mutable_expression(), context);
    target->set_is_default(association.getType().isNull());
    if (!native->isResultDependent())
      target->set_is_selected(association.isSelected());
  }
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
