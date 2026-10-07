#include "cxx17_elided_copy_returned_value.hpp"
namespace ctk::clang_layer::control_flow {
void CXX17ElidedCopyReturnedValueConstructionContextSerializer::serialize(
    const clang::CXX17ElidedCopyReturnedValueConstructionContext &native,
    ctk::analysis::v1::CfgConstructionContext &output, Context &context) const {
  namespace helpers = serialization::helpers;
  output.set_kind(ctk::analysis::v1::CfgConstructionContext::
                      CXX17_ELIDED_COPY_RETURNED_VALUE);
  helpers::write_stmt(native.getReturnStmt(), *output.mutable_returned_value(),
                      context);
  helpers::write_expr(native.getCXXBindTemporaryExpr(),
                      *output.mutable_temporary_binding(), context);
}
} // namespace ctk::clang_layer::control_flow
