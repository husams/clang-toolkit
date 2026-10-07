#include "unary_expr_or_type_trait_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool UnaryExprOrTypeTraitExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::UnaryExprOrTypeTraitExpr>();
  if (!native)
    return false;
  auto *payload =
      binding.mutable_node()->mutable_unary_expr_or_type_trait_expr();
  helpers::write_common(*native, *payload, context);
  payload->set_trait(native->getKind() == clang::UETT_SizeOf
                         ? ctk::ast::v1::UNARY_EXPR_TRAIT_SIZEOF
                         : (native->getKind() == clang::UETT_AlignOf
                                ? ctk::ast::v1::UNARY_EXPR_TRAIT_ALIGNOF
                                : ctk::ast::v1::UNARY_EXPR_TRAIT_OTHER));
  payload->set_is_type_argument(native->isArgumentType());
  if (native->isArgumentType()) {
    helpers::write_type(native->getArgumentType(),
                        *payload->mutable_argument_type(), context);
  } else {
    if (auto *value = native->getArgumentExpr())
      helpers::write_expr(value, *payload->mutable_argument_expression(),
                          context);
  }
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
