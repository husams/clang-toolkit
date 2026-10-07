#include "new_allocated_object.hpp"
namespace ctk::clang_layer::control_flow {
void NewAllocatedObjectConstructionContextSerializer::serialize(
    const clang::NewAllocatedObjectConstructionContext &native,
    ctk::analysis::v1::CfgConstructionContext &output, Context &context) const {
  namespace helpers = serialization::helpers;
  output.set_kind(
      ctk::analysis::v1::CfgConstructionContext::NEW_ALLOCATED_OBJECT);
  helpers::write_expr(native.getCXXNewExpr(), *output.mutable_allocation(),
                      context);
}
} // namespace ctk::clang_layer::control_flow
