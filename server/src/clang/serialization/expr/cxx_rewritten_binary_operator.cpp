#include "cxx_rewritten_binary_operator.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool CXXRewrittenBinaryOperatorSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::CXXRewrittenBinaryOperator>();
  if (!native)
    return false;
  auto *payload =
      binding.mutable_node()->mutable_cxx_rewritten_binary_operator();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getSemanticForm())
    helpers::write_expr(value, *payload->mutable_semantic_form(), context);
  payload->set_is_reversed(native->isReversed());
  auto *syntactic =
      payload->mutable_syntactic_form()->mutable_binary_operator();
  helpers::write_expr_info(*native, *syntactic->mutable_info(), context);
  helpers::write_expr(native->getLHS(), *syntactic->mutable_left(), context);
  helpers::write_expr(native->getRHS(), *syntactic->mutable_right(), context);
  syntactic->set_opcode(helpers::binary_opcode(native->getOpcode()));
  syntactic->set_is_compound_assignment(false);
  payload->mutable_syntactic_form()->set_is_complete(context.complete);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
