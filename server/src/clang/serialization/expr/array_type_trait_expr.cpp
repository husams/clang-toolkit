#include "array_type_trait_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool ArrayTypeTraitExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::ArrayTypeTraitExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_array_type_trait_expr();
  helpers::write_common(*native, *payload, context);
  payload->set_trait(ctk::ast::v1::ARRAY_TYPE_TRAIT_COUNT);
  helpers::write_type(native->getQueriedType(),
                      *payload->mutable_queried_type(), context);
  if (auto *dimension = native->getDimensionExpression();
      dimension && !dimension->isValueDependent()) {
    clang::Expr::EvalResult evaluated;
    if (dimension->EvaluateAsInt(evaluated, context.ast_context))
      payload->set_dimension(evaluated.Val.getInt().getLimitedValue());
    else
      helpers::unavailable(
          "dimension", "Dimension expression cannot be evaluated as an integer",
          context);
  }
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
