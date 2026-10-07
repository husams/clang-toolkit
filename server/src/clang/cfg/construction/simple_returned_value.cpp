#include "simple_returned_value.hpp"
namespace ctk::clang_layer::control_flow {
void SimpleReturnedValueConstructionContextSerializer::serialize(
    const clang::SimpleReturnedValueConstructionContext &native,
    ctk::analysis::v1::CfgConstructionContext &output, Context &context) const {
  namespace helpers = serialization::helpers;
  output.set_kind(
      ctk::analysis::v1::CfgConstructionContext::SIMPLE_RETURNED_VALUE);
  helpers::write_stmt(native.getReturnStmt(), *output.mutable_returned_value(),
                      context);
}
} // namespace ctk::clang_layer::control_flow
