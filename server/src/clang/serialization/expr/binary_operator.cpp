#include "binary_operator.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool BinaryOperatorSerializer::serialize(const clang::DynTypedNode &node,
                                         ctk::match::v1::MatchBinding &binding,
                                         SerializationContext &context) const {
  const auto *native = node.get<clang::BinaryOperator>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_binary_operator();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getLHS())
    helpers::write_expr(value, *payload->mutable_left(), context);
  if (auto *value = native->getRHS())
    helpers::write_expr(value, *payload->mutable_right(), context);
  payload->set_opcode(helpers::binary_opcode(native->getOpcode()));
  payload->set_is_compound_assignment(native->isCompoundAssignmentOp());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
