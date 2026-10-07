#include "cxx_paren_list_init_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool CXXParenListInitExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::CXXParenListInitExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_cxx_paren_list_init_expr();
  helpers::write_common(*native, *payload, context);
  for (const auto *value : native->getInitExprs()) {
    if (!helpers::can_expand("initializers", context))
      break;
    helpers::write_expr(value, *payload->add_initializers(), context);
  }
  if (auto *filler = native->getArrayFiller())
    helpers::write_type(filler->getType(),
                        *payload->mutable_array_filler_type(), context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
