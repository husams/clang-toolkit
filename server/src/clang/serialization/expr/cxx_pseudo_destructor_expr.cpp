#include "cxx_pseudo_destructor_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool CXXPseudoDestructorExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::CXXPseudoDestructorExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_cxx_pseudo_destructor_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getBase())
    helpers::write_expr(value, *payload->mutable_base(), context);
  helpers::write_nested_name(native->getQualifier(),
                             *payload->mutable_qualifier(), context);
  helpers::write_type(native->getDestroyedType(),
                      *payload->mutable_destroyed_type(), context);
  payload->set_is_arrow(native->isArrow());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
