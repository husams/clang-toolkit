#include "cxx_noexcept_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool CXXNoexceptExprSerializer::serialize(const clang::DynTypedNode &node,
                                          ctk::match::v1::MatchBinding &binding,
                                          SerializationContext &context) const {
  const auto *native = node.get<clang::CXXNoexceptExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_cxx_noexcept_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getOperand())
    helpers::write_expr(value, *payload->mutable_operand(), context);
  payload->set_is_value_dependent(native->isValueDependent());
  if (!native->isValueDependent())
    payload->set_value(native->getValue());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
