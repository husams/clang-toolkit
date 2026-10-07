#include "cfg_new_allocator.hpp"
namespace ctk::clang_layer::control_flow {
void CFGNewAllocatorSerializer::serialize(const clang::CFGElement &source,
                                          ctk::analysis::v1::CfgElement &output,
                                          Context &context) const {
  namespace helpers = serialization::helpers;
  const auto native = source.castAs<clang::CFGNewAllocator>();
  output.set_kind(ctk::analysis::v1::CfgElement::NEW_ALLOCATOR);
  helpers::write_expr(native.getAllocatorExpr(),
                      *output.mutable_allocator()->mutable_allocation(),
                      context);
}
} // namespace ctk::clang_layer::control_flow
