#include "simple_variable.hpp"
namespace ctk::clang_layer::control_flow {
void SimpleVariableConstructionContextSerializer::serialize(
    const clang::SimpleVariableConstructionContext &native,
    ctk::analysis::v1::CfgConstructionContext &output, Context &context) const {
  namespace helpers = serialization::helpers;
  output.set_kind(ctk::analysis::v1::CfgConstructionContext::SIMPLE_VARIABLE);
  helpers::write_stmt(native.getDeclStmt(), *output.mutable_decl_statement(),
                      context);
}
} // namespace ctk::clang_layer::control_flow
