#include "member_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool MemberExprSerializer::serialize(const clang::DynTypedNode &node,
                                     ctk::match::v1::MatchBinding &binding,
                                     SerializationContext &context) const {
  const auto *native = node.get<clang::MemberExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_member_expr();
  helpers::write_common(*native, *payload, context);
  helpers::write_name(native->getMemberNameInfo().getName(),
                      *payload->mutable_member_name(), context);
  helpers::write_nested_name(native->getQualifier(),
                             *payload->mutable_qualifier(), context);
  for (const auto &argument : native->template_arguments()) {
    if (!helpers::can_expand("template_arguments", context))
      break;
    helpers::write_template_argument(
        argument.getArgument(), *payload->add_template_arguments(), context);
  }
  if (auto *value = native->getBase())
    helpers::write_expr(value, *payload->mutable_base(), context);
  if (auto *value = native->getMemberDecl())
    helpers::write_symbol(*value, *payload->mutable_member_declaration(),
                          context);
  payload->set_is_arrow(native->isArrow());
  const auto *method =
      llvm::dyn_cast<clang::CXXMethodDecl>(native->getMemberDecl());
  payload->set_is_virtual_call(
      method && method->isVirtual() &&
      native->performsVirtualDispatch(context.ast_context.getLangOpts()));
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
