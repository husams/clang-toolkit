#include "cfg_statement.hpp"
namespace ctk::clang_layer::control_flow {
void CFGStmtSerializer::serialize(const clang::CFGElement &source,
                                  ctk::analysis::v1::CfgElement &output,
                                  Context &context) const {
  namespace helpers = serialization::helpers;
  const auto native = source.castAs<clang::CFGStmt>();
  output.set_kind(ctk::analysis::v1::CfgElement::STATEMENT);
  auto *value = output.mutable_statement();
  helpers::write_stmt(native.getStmt(), *value->mutable_statement(), context);
}
} // namespace ctk::clang_layer::control_flow
