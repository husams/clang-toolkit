#include "simple_constructor_initializer.hpp"
namespace ctk::clang_layer::control_flow {
void SimpleConstructorInitializerConstructionContextSerializer::serialize(
    const clang::SimpleConstructorInitializerConstructionContext &native,
    ctk::analysis::v1::CfgConstructionContext &output, Context &context) const {
  namespace helpers = serialization::helpers;
  output.set_kind(ctk::analysis::v1::CfgConstructionContext::
                      SIMPLE_CONSTRUCTOR_INITIALIZER);
  write_initializer(*native.getCXXCtorInitializer(),
                    *output.mutable_initializer(), context);
}
} // namespace ctk::clang_layer::control_flow
