#include "argument.hpp"
namespace ctk::clang_layer::control_flow {
void ArgumentConstructionContextSerializer::serialize(
    const clang::ArgumentConstructionContext &native,
    ctk::analysis::v1::CfgConstructionContext &output, Context &context) const {
  namespace helpers = serialization::helpers;
  output.set_kind(ctk::analysis::v1::CfgConstructionContext::ARGUMENT);
  helpers::write_expr(native.getCallLikeExpr(),
                      *output.mutable_call_like_expression(), context);
  output.set_argument_index(native.getIndex());
  if (auto *value = native.getCXXBindTemporaryExpr())
    helpers::write_expr(value, *output.mutable_temporary_binding(), context);
}
} // namespace ctk::clang_layer::control_flow
