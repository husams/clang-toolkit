#include "shuffle_vector_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool ShuffleVectorExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::ShuffleVectorExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_shuffle_vector_expr();
  helpers::write_common(*native, *payload, context);
  if (context.projection == ProjectionPolicy::Shallow) {
    for (const char *field : {"arguments", "shuffle_mask", "signed_shuffle_mask"})
      helpers::can_expand(*payload, field, context);
    helpers::finish_binding(binding, context);
    return true;
  }
  for (unsigned i = 0; i < native->getNumSubExprs(); ++i) {
    if (!helpers::can_expand(*payload, "arguments", context))
      break;

    helpers::write_expr(native->getExpr(i), *payload->add_arguments(), context);
    if (i < 2 || native->getExpr(i)->isValueDependent())
      continue;
    clang::Expr::EvalResult evaluated;
    if (!helpers::can_expand(*payload, "signed_shuffle_mask", context))
      break;
    if (!native->getExpr(i)->EvaluateAsInt(evaluated, context.ast_context)) {
      helpers::unavailable("signed_shuffle_mask",
                           "Mask expression cannot be evaluated as an integer",
                           context);
      continue;
    }
    const auto &index = evaluated.Val.getInt();
    payload->add_signed_shuffle_mask(index.getSExtValue());
    if (index.isNonNegative())
      payload->add_shuffle_mask(index.getZExtValue());
  }
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
