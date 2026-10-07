#include "cfg_initializer.hpp"
namespace ctk::clang_layer::control_flow {
void CFGInitializerSerializer::serialize(const clang::CFGElement &source,
                                         ctk::analysis::v1::CfgElement &output,
                                         Context &context) const {
  namespace helpers = serialization::helpers;
  const auto native = source.castAs<clang::CFGInitializer>();
  output.set_kind(ctk::analysis::v1::CfgElement::INITIALIZER);
  if (const auto *initializer = native.getInitializer())
    write_initializer(*initializer,
                      *output.mutable_initializer()->mutable_initializer(),
                      context);
}
} // namespace ctk::clang_layer::control_flow
