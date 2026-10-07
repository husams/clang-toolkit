#include "integer_literal.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool IntegerLiteralSerializer::serialize(const clang::DynTypedNode &node,
                                         ctk::match::v1::MatchBinding &binding,
                                         SerializationContext &context) const {
  const auto *native = node.get<clang::IntegerLiteral>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_integer_literal();
  helpers::write_common(*native, *payload, context);
  helpers::write_apint(native->getValue(), *payload->mutable_value());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
