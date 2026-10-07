#include "cxx_member_call_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool CXXMemberCallExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::CXXMemberCallExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_cxx_member_call_expr();
  helpers::write_call(*native, *payload->mutable_call(), context);
  if (auto *value = native->getImplicitObjectArgument())
    helpers::write_expr(value, *payload->mutable_implicit_object_argument(),
                        context);
  helpers::write_type(native->getObjectType(), *payload->mutable_object_type(),
                      context);
  if (auto *value = native->getMethodDecl())
    helpers::write_symbol(*value, *payload->mutable_method_declaration(),
                          context);
  if (auto *value = native->getRecordDecl())
    helpers::write_symbol(*value, *payload->mutable_record_declaration(),
                          context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
