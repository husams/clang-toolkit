#include "lambda_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool LambdaExprSerializer::serialize(const clang::DynTypedNode &node,
                                     ctk::match::v1::MatchBinding &binding,
                                     SerializationContext &context) const {
  const auto *native = node.get<clang::LambdaExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_lambda_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getLambdaClass())
    helpers::write_symbol(*value, *payload->mutable_closure_class(), context);
  if (auto *value = native->getCallOperator())
    helpers::write_symbol(*value, *payload->mutable_call_operator(), context);
  payload->set_is_generic_lambda(native->isGenericLambda());
  payload->set_is_mutable(native->isMutable());
  for (const auto &capture : native->captures()) {
    if (!helpers::can_expand(*payload, "captures", context))
      break;

    auto *target = payload->add_captures();
    switch (capture.getCaptureKind()) {
    case clang::LCK_This:
      target->set_kind(ctk::ast::v1::LAMBDA_CAPTURE_KIND_THIS);
      break;
    case clang::LCK_StarThis:
      target->set_kind(ctk::ast::v1::LAMBDA_CAPTURE_KIND_STAR_THIS);
      break;
    case clang::LCK_ByCopy:
      target->set_kind(ctk::ast::v1::LAMBDA_CAPTURE_KIND_BY_COPY);
      break;
    case clang::LCK_ByRef:
      target->set_kind(ctk::ast::v1::LAMBDA_CAPTURE_KIND_BY_REFERENCE);
      break;
    case clang::LCK_VLAType:
      target->set_kind(ctk::ast::v1::LAMBDA_CAPTURE_KIND_VLA_TYPE);
      break;
    }
    if (capture.capturesVariable())
      helpers::write_symbol(*capture.getCapturedVar(),
                            *target->mutable_variable(), context);
    target->set_is_implicit(capture.isImplicit());
    target->set_is_pack_expansion(capture.isPackExpansion());
  }
  for (const auto *initializer : native->capture_inits()) {
    if (!helpers::can_expand(*payload, "capture_initializers", context))
      break;

    if (initializer)
      helpers::write_expr(initializer, *payload->add_capture_initializers(),
                          context);
  }
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
