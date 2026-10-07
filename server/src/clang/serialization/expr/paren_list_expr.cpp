#include "paren_list_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool ParenListExprSerializer::serialize(const clang::DynTypedNode &node,
                                        ctk::match::v1::MatchBinding &binding,
                                        SerializationContext &context) const {
  const auto *native = node.get<clang::ParenListExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_paren_list_expr();
  helpers::write_common(*native, *payload, context);
  for (unsigned i = 0; i < native->getNumExprs(); ++i) {
    if (!helpers::can_expand("expressions", context))
      break;
    helpers::write_expr(native->getExpr(i), *payload->add_expressions(),
                        context);
  }
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
