#include "unary_operator.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool UnaryOperatorSerializer::serialize(const clang::DynTypedNode &node,
                                        ctk::match::v1::MatchBinding &binding,
                                        SerializationContext &context) const {
  const auto *native = node.get<clang::UnaryOperator>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_unary_operator();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getSubExpr())
    helpers::write_expr(value, *payload->mutable_operand(), context);
  payload->set_opcode(helpers::unary_opcode(native->getOpcode()));
  payload->set_is_postfix(native->isPostfix());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
