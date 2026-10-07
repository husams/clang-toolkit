#include "cxx_fold_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool CXXFoldExprSerializer::serialize(const clang::DynTypedNode &node,
                                      ctk::match::v1::MatchBinding &binding,
                                      SerializationContext &context) const {
  const auto *native = node.get<clang::CXXFoldExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_cxx_fold_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getPattern())
    helpers::write_expr(value, *payload->mutable_pattern(), context);
  if (auto *value = native->getLHS())
    helpers::write_expr(value, *payload->mutable_left_operand(), context);
  if (auto *value = native->getRHS())
    helpers::write_expr(value, *payload->mutable_right_operand(), context);
  payload->set_operator_kind(helpers::binary_opcode(native->getOperator()));
  payload->set_is_left_fold(native->isLeftFold());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
