#include "size_of_pack_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool SizeOfPackExprSerializer::serialize(const clang::DynTypedNode &node,
                                         ctk::match::v1::MatchBinding &binding,
                                         SerializationContext &context) const {
  const auto *native = node.get<clang::SizeOfPackExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_size_of_pack_expr();
  helpers::write_common(*native, *payload, context);
  if (auto *value = native->getPack())
    helpers::write_symbol(*value, *payload->mutable_pack_declaration(),
                          context);
  if (!native->isValueDependent())
    payload->set_pack_size(native->getPackLength());
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
