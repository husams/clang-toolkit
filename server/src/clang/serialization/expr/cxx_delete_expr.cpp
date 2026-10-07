#include "cxx_delete_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool CXXDeleteExprSerializer::serialize(const clang::DynTypedNode &node,
                                        ctk::match::v1::MatchBinding &binding,
                                        SerializationContext &context) const {
  const auto *native = node.get<clang::CXXDeleteExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_cxx_delete_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getArgument())
    helpers::write_expr(value, *payload->mutable_argument(), context);
  payload->set_is_array_form(native->isArrayForm());
  payload->set_is_global_delete(native->isGlobalDelete());
  if (auto *value = native->getOperatorDelete())
    helpers::write_symbol(*value, *payload->mutable_operator_delete(), context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
