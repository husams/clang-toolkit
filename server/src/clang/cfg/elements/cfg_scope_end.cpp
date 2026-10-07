#include "cfg_scope_end.hpp"
namespace ctk::clang_layer::control_flow {
void CFGScopeEndSerializer::serialize(const clang::CFGElement &source,
                                      ctk::analysis::v1::CfgElement &output,
                                      Context &context) const {
  namespace helpers = serialization::helpers;
  const auto native = source.castAs<clang::CFGScopeEnd>();
  output.set_kind(ctk::analysis::v1::CfgElement::SCOPE_END);
  auto *value = output.mutable_scope();
  if (const auto *variable = native.getVarDecl())
    helpers::write_symbol(*variable, *value->mutable_variable(), context);
  if (native.getTriggerStmt())
    helpers::write_stmt(native.getTriggerStmt(), *value->mutable_trigger(),
                        context);
}
} // namespace ctk::clang_layer::control_flow
