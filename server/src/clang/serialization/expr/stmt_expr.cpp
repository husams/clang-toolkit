#include "stmt_expr.hpp"
#include "../expression_helpers.hpp"
#include "../semantic_helpers.hpp"
// Source: installed Clang 22 AST/Expr.h and AST/ExprCXX.h native getters.
namespace ctk::clang_layer::serialization {

bool StmtExprSerializer::serialize(const clang::DynTypedNode &node,
                                   ctk::match::v1::MatchBinding &binding,
                                   SerializationContext &context) const {
  const auto *native = node.get<clang::StmtExpr>();
  if (!native)
    return false;
  auto *payload = binding.mutable_node()->mutable_stmt_expr();
  helpers::write_common(*native, *payload, context);
  helpers::write_stmt(native->getSubStmt(),
                      *payload->mutable_compound_statement(), context);
  helpers::finish_binding(binding, context);
  return true;
}

} // namespace ctk::clang_layer::serialization
