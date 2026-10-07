#include "addr_label_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool AddrLabelExprSerializer::serialize(const clang::DynTypedNode &node,
                                        ctk::match::v1::MatchBinding &binding,
                                        SerializationContext &context) const {
  const auto *native = node.get<clang::AddrLabelExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_addr_label_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getLabel())
    helpers::write_symbol(*value, *payload->mutable_label(), context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
