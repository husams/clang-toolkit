#include "elided_temporary_object.hpp"
namespace ctk::clang_layer::control_flow {
void ElidedTemporaryObjectConstructionContextSerializer::serialize(
    const clang::ElidedTemporaryObjectConstructionContext &native,
    ctk::analysis::v1::CfgConstructionContext &output, Context &context) const {
  namespace helpers = serialization::helpers;
  output.set_kind(
      ctk::analysis::v1::CfgConstructionContext::ELIDED_TEMPORARY_OBJECT);
  if (auto *value = native.getCXXBindTemporaryExpr())
    helpers::write_expr(value, *output.mutable_temporary_binding(), context);
  if (auto *value = native.getMaterializedTemporaryExpr())
    helpers::write_expr(value, *output.mutable_materialization(), context);
  helpers::write_expr(native.getConstructorAfterElision(),
                      *output.mutable_constructor_after_elision(), context);
  write_construction(native.getConstructionContextAfterElision(),
                     *output.mutable_context_after_elision(), context);
}
} // namespace ctk::clang_layer::control_flow
