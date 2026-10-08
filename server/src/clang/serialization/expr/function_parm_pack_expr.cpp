#include "function_parm_pack_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool FunctionParmPackExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::FunctionParmPackExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_function_parm_pack_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getParameterPack())
    helpers::write_symbol(*value, *payload->mutable_parameter_pack(), context);
  for (const auto *value : *native) {
    if (!helpers::can_expand(*payload, "expansions", context))
      break;
    helpers::write_symbol(*value, *payload->add_expansions(), context);
  }
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
