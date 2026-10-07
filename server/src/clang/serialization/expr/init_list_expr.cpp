#include "init_list_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool InitListExprSerializer::serialize(const clang::DynTypedNode &node,
                                       ctk::match::v1::MatchBinding &binding,
                                       SerializationContext &context) const {
  const auto *native = node.get<clang::InitListExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_init_list_expr();
  helpers::write_common(*native, *payload, context);
  for (const auto *value : native->inits()) {
    if (!helpers::can_expand("initializers", context))
      break;
    helpers::write_expr(value, *payload->add_initializers(), context);
  }
  if (auto *syntax = native->getSyntacticForm()) {
    for (const auto *value : syntax->inits()) {
      if (!helpers::can_expand("syntactic_initializers", context))
        break;
      helpers::write_expr(value, *payload->add_syntactic_initializers(),
                          context);
    }
  } else if (!native->isSemanticForm()) {
    for (const auto *value : native->inits()) {
      if (!helpers::can_expand("syntactic_initializers", context))
        break;
      helpers::write_expr(value, *payload->add_syntactic_initializers(),
                          context);
    }
  }
  if (auto *value = native->getArrayFiller())
    helpers::write_expr(value, *payload->mutable_array_filler(), context);
  payload->set_is_union(native->getType()->isUnionType());
  payload->set_is_semantic_form(native->isSemanticForm());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
