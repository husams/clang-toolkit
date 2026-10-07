#include "user_defined_literal.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool UserDefinedLiteralSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::UserDefinedLiteral>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_user_defined_literal();
  helpers::write_call(*native, *payload->mutable_call(), context);
  payload->set_literal_suffix(native->getUDSuffix()->getName().str());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
