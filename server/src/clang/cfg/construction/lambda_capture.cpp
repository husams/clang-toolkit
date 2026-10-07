#include "lambda_capture.hpp"
namespace ctk::clang_layer::control_flow {
void LambdaCaptureConstructionContextSerializer::serialize(
    const clang::LambdaCaptureConstructionContext &native,
    ctk::analysis::v1::CfgConstructionContext &output, Context &context) const {
  namespace helpers = serialization::helpers;
  output.set_kind(ctk::analysis::v1::CfgConstructionContext::LAMBDA_CAPTURE);
  helpers::write_expr(native.getLambdaExpr(),
                      *output.mutable_lambda_expression(), context);
  output.set_capture_index(native.getIndex());
  if (auto *value = native.getInitializer())
    helpers::write_expr(value, *output.mutable_capture_initializer(), context);
  helpers::write_symbol(*native.getFieldDecl(), *output.mutable_capture_field(),
                        context);
}
} // namespace ctk::clang_layer::control_flow
