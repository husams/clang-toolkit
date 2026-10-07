#include "va_arg_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool VAArgExprSerializer::serialize(const clang::DynTypedNode &node,
                                    ctk::match::v1::MatchBinding &binding,
                                    SerializationContext &context) const {
  const auto *native = node.get<clang::VAArgExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_va_arg_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getSubExpr())
    helpers::write_expr(value, *payload->mutable_subexpression(), context);
  helpers::write_type(native->getType(), *payload->mutable_result_type(),
                      context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
