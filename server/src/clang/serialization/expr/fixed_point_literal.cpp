#include "fixed_point_literal.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool FixedPointLiteralSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::FixedPointLiteral>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_fixed_point_literal();
  helpers::write_common(*native, *payload, context);
  helpers::write_apint(native->getValue(), *payload->mutable_scaled_value());
  payload->set_scale(native->getScale());
  payload->set_integer_bits(
      context.ast_context.getFixedPointSemantics(native->getType())
          .getIntegralBits());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
