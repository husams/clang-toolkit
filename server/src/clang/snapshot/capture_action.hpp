#pragma once
#include "serialization_observer.hpp"
#include "volatile_macro_observer.hpp"
#include <clang/Frontend/CompilerInstance.h>
#include <clang/Frontend/FrontendActions.h>
#include <clang/Lex/Preprocessor.h>
namespace ctk::clang_layer::snapshot {
class CaptureAction final : public clang::SyntaxOnlyAction {
public:
  CaptureAction(bool &volatile_input, std::unique_ptr<NativeAstWriter> &writer)
      : volatile_input_(volatile_input), writer_(writer) {}

protected:
  std::unique_ptr<clang::ASTConsumer>
  CreateASTConsumer(clang::CompilerInstance &compiler,
                    llvm::StringRef) override {
    writer_ = std::make_unique<NativeAstWriter>(compiler.getCodeGenOpts());
    return std::make_unique<SerializationObserver>(*writer_);
  }
  bool BeginSourceFileAction(clang::CompilerInstance &compiler) override {
    compiler.getPreprocessor().addPPCallbacks(
        std::make_unique<VolatileMacroObserver>(volatile_input_));
    return clang::SyntaxOnlyAction::BeginSourceFileAction(compiler);
  }

private:
  bool &volatile_input_;
  std::unique_ptr<NativeAstWriter> &writer_;
};
} // namespace ctk::clang_layer::snapshot
