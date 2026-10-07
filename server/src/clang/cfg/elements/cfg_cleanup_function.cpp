#include "cfg_cleanup_function.hpp"
namespace ctk::clang_layer::control_flow {
void CFGCleanupFunctionSerializer::serialize(
    const clang::CFGElement &source, ctk::analysis::v1::CfgElement &output,
    Context &context) const {
  namespace helpers = serialization::helpers;
  const auto native = source.castAs<clang::CFGCleanupFunction>();
  output.set_kind(ctk::analysis::v1::CfgElement::CLEANUP_FUNCTION);
  auto *value = output.mutable_cleanup();
  if (const auto *variable = native.getVarDecl())
    helpers::write_symbol(*variable, *value->mutable_variable(), context);
  if (const auto *function = native.getFunctionDecl())
    helpers::write_symbol(*function, *value->mutable_function(), context);
}
} // namespace ctk::clang_layer::control_flow
