#include "cfg_value_helpers.hpp"
#include "construction/argument.hpp"
#include "construction/cxx17_elided_copy_constructor_initializer.hpp"
#include "construction/cxx17_elided_copy_returned_value.hpp"
#include "construction/cxx17_elided_copy_variable.hpp"
#include "construction/elided_temporary_object.hpp"
#include "construction/lambda_capture.hpp"
#include "construction/new_allocated_object.hpp"
#include "construction/simple_constructor_initializer.hpp"
#include "construction/simple_returned_value.hpp"
#include "construction/simple_temporary_object.hpp"
#include "construction/simple_variable.hpp"
namespace ctk::clang_layer::control_flow {
void write_construction(const clang::ConstructionContext *source,
                        ctk::analysis::v1::CfgConstructionContext &output,
                        Context &context) {
  if (!source)
    return;
  serialization::helpers::ExpansionFrame frame("cfg.construction_context",
                                               context);
  if (!frame.allowed)
    return;
  switch (source->getKind()) {
  case clang::ConstructionContext::SimpleVariableKind:
    SimpleVariableConstructionContextSerializer{}.serialize(
        *llvm::cast<clang::SimpleVariableConstructionContext>(source), output,
        context);
    break;
  case clang::ConstructionContext::CXX17ElidedCopyVariableKind:
    CXX17ElidedCopyVariableConstructionContextSerializer{}.serialize(
        *llvm::cast<clang::CXX17ElidedCopyVariableConstructionContext>(source),
        output, context);
    break;
  case clang::ConstructionContext::SimpleConstructorInitializerKind:
    SimpleConstructorInitializerConstructionContextSerializer{}.serialize(
        *llvm::cast<clang::SimpleConstructorInitializerConstructionContext>(
            source),
        output, context);
    break;
  case clang::ConstructionContext::CXX17ElidedCopyConstructorInitializerKind:
    CXX17ElidedCopyConstructorInitializerConstructionContextSerializer{}
        .serialize(
            *llvm::cast<
                clang::
                    CXX17ElidedCopyConstructorInitializerConstructionContext>(
                source),
            output, context);
    break;
  case clang::ConstructionContext::NewAllocatedObjectKind:
    NewAllocatedObjectConstructionContextSerializer{}.serialize(
        *llvm::cast<clang::NewAllocatedObjectConstructionContext>(source),
        output, context);
    break;
  case clang::ConstructionContext::SimpleTemporaryObjectKind:
    SimpleTemporaryObjectConstructionContextSerializer{}.serialize(
        *llvm::cast<clang::SimpleTemporaryObjectConstructionContext>(source),
        output, context);
    break;
  case clang::ConstructionContext::ElidedTemporaryObjectKind:
    ElidedTemporaryObjectConstructionContextSerializer{}.serialize(
        *llvm::cast<clang::ElidedTemporaryObjectConstructionContext>(source),
        output, context);
    break;
  case clang::ConstructionContext::SimpleReturnedValueKind:
    SimpleReturnedValueConstructionContextSerializer{}.serialize(
        *llvm::cast<clang::SimpleReturnedValueConstructionContext>(source),
        output, context);
    break;
  case clang::ConstructionContext::CXX17ElidedCopyReturnedValueKind:
    CXX17ElidedCopyReturnedValueConstructionContextSerializer{}.serialize(
        *llvm::cast<clang::CXX17ElidedCopyReturnedValueConstructionContext>(
            source),
        output, context);
    break;
  case clang::ConstructionContext::ArgumentKind:
    ArgumentConstructionContextSerializer{}.serialize(
        *llvm::cast<clang::ArgumentConstructionContext>(source), output,
        context);
    break;
  case clang::ConstructionContext::LambdaCaptureKind:
    LambdaCaptureConstructionContextSerializer{}.serialize(
        *llvm::cast<clang::LambdaCaptureConstructionContext>(source), output,
        context);
    break;
  }
  if (const auto *loop = source->getArrayInitLoop())
    serialization::helpers::write_expr(
        loop, *output.mutable_array_initialization_loop(), context);
}
} // namespace ctk::clang_layer::control_flow
