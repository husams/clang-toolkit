#include "recovery_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool RecoveryExprSerializer::serialize(const clang::DynTypedNode &node,
                                       ctk::match::v1::MatchBinding &binding,
                                       SerializationContext &context) const {
  const auto *native = node.get<clang::RecoveryExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_recovery_expr();
  helpers::write_common(*native, *payload, context);
  for (const auto *value : native->subExpressions()) {
    if (!helpers::can_expand(*payload, "subexpressions", context))
      break;
    helpers::write_expr(value, *payload->add_subexpressions(), context);
  }
  helpers::unavailable("candidate_declarations",
                       "Clang RecoveryExpr retains only child expressions, not "
                       "candidate declarations",
                       context);
  helpers::unavailable("is_overloaded",
                       "Clang RecoveryExpr does not retain an overload flag",
                       context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
