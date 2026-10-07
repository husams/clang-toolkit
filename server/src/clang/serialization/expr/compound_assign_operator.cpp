#include "compound_assign_operator.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool CompoundAssignOperatorSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::CompoundAssignOperator>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_compound_assign_operator();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getLHS())
    helpers::write_expr(value, *payload->mutable_left(), context);
  if (auto *value = native->getRHS())
    helpers::write_expr(value, *payload->mutable_right(), context);
  payload->set_opcode(helpers::binary_opcode(native->getOpcode()));
  helpers::write_type(native->getComputationLHSType(),
                      *payload->mutable_computation_lhs_type(), context);
  helpers::write_type(native->getComputationResultType(),
                      *payload->mutable_computation_result_type(), context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
