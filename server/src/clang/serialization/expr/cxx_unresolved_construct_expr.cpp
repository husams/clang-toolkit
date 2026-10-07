#include "cxx_unresolved_construct_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool CXXUnresolvedConstructExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::CXXUnresolvedConstructExpr>();
  if (!native)
    return false;
  auto *payload =
      binding.mutable_node()->mutable_cxx_unresolved_construct_expr();
  helpers::write_common(*native, *payload, context);
  helpers::write_type(native->getTypeAsWritten(),
                      *payload->mutable_constructed_type(), context);
  for (unsigned i = 0; i < native->getNumArgs(); ++i) {
    if (!helpers::can_expand("arguments", context))
      break;
    helpers::write_expr(native->getArg(i), *payload->add_arguments(), context);
  }
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
