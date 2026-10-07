#include "cxx17_elided_copy_constructor_initializer.hpp"
namespace ctk::clang_layer::control_flow {
void CXX17ElidedCopyConstructorInitializerConstructionContextSerializer::
    serialize(
        const clang::CXX17ElidedCopyConstructorInitializerConstructionContext
            &native,
        ctk::analysis::v1::CfgConstructionContext &output,
        Context &context) const {
  namespace helpers = serialization::helpers;
  output.set_kind(ctk::analysis::v1::CfgConstructionContext::
                      CXX17_ELIDED_COPY_CONSTRUCTOR_INITIALIZER);
  write_initializer(*native.getCXXCtorInitializer(),
                    *output.mutable_initializer(), context);
  helpers::write_expr(native.getCXXBindTemporaryExpr(),
                      *output.mutable_temporary_binding(), context);
}
} // namespace ctk::clang_layer::control_flow
