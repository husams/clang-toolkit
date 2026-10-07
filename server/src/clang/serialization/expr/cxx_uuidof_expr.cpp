#include "cxx_uuidof_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool CXXUuidofExprSerializer::serialize(const clang::DynTypedNode &node,
                                        ctk::match::v1::MatchBinding &binding,
                                        SerializationContext &context) const {
  const auto *native = node.get<clang::CXXUuidofExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_cxx_uuidof_expr();
  helpers::write_common(*native, *payload, context);
  payload->set_is_type_operand(native->isTypeOperand());
  if (native->isTypeOperand()) {
    helpers::write_type(native->getTypeOperand(context.ast_context),
                        *payload->mutable_queried_type(), context);
  } else {
    if (auto *value = native->getExprOperand())
      helpers::write_expr(value, *payload->mutable_operand(), context);
  }
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
