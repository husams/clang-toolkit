#include "simple_temporary_object.hpp"
namespace ctk::clang_layer::control_flow {
void SimpleTemporaryObjectConstructionContextSerializer::serialize(
    const clang::SimpleTemporaryObjectConstructionContext &native,
    ctk::analysis::v1::CfgConstructionContext &output, Context &context) const {
  namespace helpers = serialization::helpers;
  output.set_kind(
      ctk::analysis::v1::CfgConstructionContext::SIMPLE_TEMPORARY_OBJECT);
  if (auto *value = native.getCXXBindTemporaryExpr())
    helpers::write_expr(value, *output.mutable_temporary_binding(), context);
  if (auto *value = native.getMaterializedTemporaryExpr())
    helpers::write_expr(value, *output.mutable_materialization(), context);
}
} // namespace ctk::clang_layer::control_flow
