#include "floating_literal.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool FloatingLiteralSerializer::serialize(const clang::DynTypedNode &node,
                                          ctk::match::v1::MatchBinding &binding,
                                          SerializationContext &context) const {
  const auto *native = node.get<clang::FloatingLiteral>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_floating_literal();
  helpers::write_common(*native, *payload, context);
  helpers::write_apfloat(native->getValue(), *payload->mutable_value());
  payload->set_is_exact(native->isExact());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
