#include "materialize_temporary_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool MaterializeTemporaryExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::MaterializeTemporaryExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_materialize_temporary_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getSubExpr())
    helpers::write_expr(value, *payload->mutable_subexpression(), context);
  if (auto *value = native->getExtendingDecl())
    helpers::write_symbol(*value, *payload->mutable_extending_declaration(),
                          context);
  helpers::unavailable("bound_to_lvalue_rank",
                       "Clang exposes lvalue binding as a boolean, not a rank",
                       context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
