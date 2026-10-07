#include "cxx_temporary_object_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool CXXTemporaryObjectExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::CXXTemporaryObjectExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_cxx_temporary_object_expr();
  helpers::write_construction(*native, *payload->mutable_construction(),
                              context);
  helpers::write_type(native->getType(), *payload->mutable_target_type(),
                      context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
