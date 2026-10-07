#include "cfg_loop_exit.hpp"
namespace ctk::clang_layer::control_flow {
void CFGLoopExitSerializer::serialize(const clang::CFGElement &source,
                                      ctk::analysis::v1::CfgElement &output,
                                      Context &context) const {
  namespace helpers = serialization::helpers;
  const auto native = source.castAs<clang::CFGLoopExit>();
  output.set_kind(ctk::analysis::v1::CfgElement::LOOP_EXIT);
  helpers::write_stmt(native.getLoopStmt(),
                      *output.mutable_loop_exit()->mutable_loop(), context);
}
} // namespace ctk::clang_layer::control_flow
