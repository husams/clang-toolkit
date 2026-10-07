#include "cxx17_elided_copy_variable.hpp"
namespace ctk::clang_layer::control_flow {
void CXX17ElidedCopyVariableConstructionContextSerializer::serialize(
    const clang::CXX17ElidedCopyVariableConstructionContext &native,
    ctk::analysis::v1::CfgConstructionContext &output, Context &context) const {
  namespace helpers = serialization::helpers;
  output.set_kind(
      ctk::analysis::v1::CfgConstructionContext::CXX17_ELIDED_COPY_VARIABLE);
  helpers::write_stmt(native.getDeclStmt(), *output.mutable_decl_statement(),
                      context);
  helpers::write_expr(native.getCXXBindTemporaryExpr(),
                      *output.mutable_temporary_binding(), context);
}
} // namespace ctk::clang_layer::control_flow
