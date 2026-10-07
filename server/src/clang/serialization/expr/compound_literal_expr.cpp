#include "compound_literal_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool CompoundLiteralExprSerializer::serialize(
    const clang::DynTypedNode &node, ctk::match::v1::MatchBinding &binding,
    SerializationContext &context) const {
  const auto *native = node.get<clang::CompoundLiteralExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_compound_literal_expr();
  helpers::write_common(*native, *payload, context);
  helpers::write_type(native->getType(), *payload->mutable_literal_type(),
                      context);
  if (auto *value = native->getInitializer())
    helpers::write_expr(value, *payload->mutable_initializer(), context);
  payload->set_is_file_scope(native->isFileScope());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
