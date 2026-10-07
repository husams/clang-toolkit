#include "cfg_cxx_record_typed_call.hpp"
namespace ctk::clang_layer::control_flow {
void CFGCXXRecordTypedCallSerializer::serialize(
    const clang::CFGElement &source, ctk::analysis::v1::CfgElement &output,
    Context &context) const {
  namespace helpers = serialization::helpers;
  const auto native = source.castAs<clang::CFGCXXRecordTypedCall>();
  output.set_kind(ctk::analysis::v1::CfgElement::CXX_RECORD_TYPED_CALL);
  auto *value = output.mutable_statement();
  helpers::write_stmt(native.getStmt(), *value->mutable_statement(), context);
  if (const auto *construction = native.getConstructionContext())
    write_construction(construction, *value->mutable_construction_context(),
                       context);
}
} // namespace ctk::clang_layer::control_flow
