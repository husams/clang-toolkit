#include "matrix_single_subscript_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {
#if CLANG_VERSION_MAJOR >= 22

bool MatrixSingleSubscriptExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::MatrixSingleSubscriptExpr>();
  if (!native)
    return false;
  auto *payload =
      binding.mutable_node()->mutable_matrix_single_subscript_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getBase())
    helpers::write_expr(value, *payload->mutable_base(), context);
  if (auto *value = native->getRowIdx())
    helpers::write_expr(value, *payload->mutable_row_index(), context);
  helpers::finish_binding(binding, context);
  return true;
}
#endif
} // namespace ctk::clang_layer::serialization
