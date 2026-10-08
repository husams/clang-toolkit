#include "expr_with_cleanups.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool ExprWithCleanupsSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::ExprWithCleanups>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_expr_with_cleanups();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getSubExpr())
    helpers::write_expr(value, *payload->mutable_subexpression(), context);
  for (const auto &object : native->getObjects()) {
    if (!helpers::can_expand(*payload, "cleanups", context))
      break;

    auto *cleanup = payload->add_cleanups();
    if (const auto *block = object.dyn_cast<clang::BlockDecl *>())
      cleanup->mutable_block()->set_clang_class(
          std::string(block->clang::Decl::getDeclKindName()) + "Decl");
    else if (const auto *literal =
                 object.dyn_cast<clang::CompoundLiteralExpr *>())
      helpers::write_expr(literal, *cleanup->mutable_compound_literal(),
                          context);
  }
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
