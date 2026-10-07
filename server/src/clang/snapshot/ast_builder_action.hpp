#pragma once
#include "capture_action.hpp"
#include <clang/Frontend/ASTUnit.h>
#include <clang/Frontend/CompilerInvocation.h>
#include <clang/Tooling/Tooling.h>
namespace ctk::clang_layer::snapshot {
class AstBuilderAction final : public clang::tooling::ToolAction {
public:
  AstBuilderAction(std::unique_ptr<clang::ASTUnit> &unit, bool &volatile_input,
                   std::unique_ptr<NativeAstWriter> &writer)
      : unit_(unit), volatile_input_(volatile_input), writer_(writer) {}
  bool runInvocation(std::shared_ptr<clang::CompilerInvocation> invocation,
                     clang::FileManager *files,
                     std::shared_ptr<clang::PCHContainerOperations> containers,
                     clang::DiagnosticConsumer *consumer) override {
    auto diagnostics = clang::CompilerInstance::createDiagnostics(
        files->getVirtualFileSystem(), invocation->getDiagnosticOpts(),
        consumer, false);
    auto options = std::make_shared<clang::DiagnosticOptions>(
        invocation->getDiagnosticOpts());
    auto unit = clang::ASTUnit::create(invocation, options, diagnostics,
                                       clang::CaptureDiagsKind::None, false);
    unit->getFileManager().setVirtualFileSystem(
        clang::createVFSFromCompilerInvocation(
            *invocation, *diagnostics, files->getVirtualFileSystemPtr()));
    CaptureAction action(volatile_input_, writer_);
    if (!clang::ASTUnit::LoadFromCompilerInvocationAction(
            invocation, std::move(containers), options, diagnostics, &action,
            unit.get()))
      return false;
    unit_ = std::move(unit);
    return true;
  }

private:
  std::unique_ptr<clang::ASTUnit> &unit_;
  bool &volatile_input_;
  std::unique_ptr<NativeAstWriter> &writer_;
};
} // namespace ctk::clang_layer::snapshot
