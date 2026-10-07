#include "cxx_inherited_ctor_init_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool CXXInheritedCtorInitExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::CXXInheritedCtorInitExpr>();
  if (!native)
    return false;
  auto *payload =
      binding.mutable_node()->mutable_cxx_inherited_ctor_init_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getConstructor())
    helpers::write_symbol(*value, *payload->mutable_constructor(), context);
  helpers::unavailable("constructing_constructor",
                       "Clang stores the inherited base constructor but not "
                       "the enclosing constructing constructor",
                       context);
  helpers::unavailable(
      "is_constructed_in_class",
      "Clang inherited constructor initialization stores base construction and "
      "virtual-base flags, not this schema predicate",
      context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
