#include "build_snapshot.hpp"
#include "ast_builder_action.hpp"
namespace ctk::clang_layer::snapshot {
std::unique_ptr<clang::ASTUnit>
build_snapshot(const std::string &path,
               const std::vector<std::string> &arguments,
               const std::string &tool,
               llvm::IntrusiveRefCntPtr<llvm::vfs::FileSystem> filesystem,
               bool &volatile_input, std::unique_ptr<NativeAstWriter> &writer) {
  std::unique_ptr<clang::ASTUnit> unit;
  AstBuilderAction action(unit, volatile_input, writer);
  auto files = llvm::makeIntrusiveRefCnt<clang::FileManager>(
      clang::FileSystemOptions(), filesystem);
  std::vector<std::string> command{tool, "-fsyntax-only"};
  const auto adjusted =
      clang::tooling::getClangStripDependencyFileAdjuster()(arguments, path);
  command.insert(command.end(), adjusted.begin(), adjusted.end());
  command.push_back(path);
  clang::tooling::ToolInvocation invocation(
      command, &action, files.get(),
      std::make_shared<clang::PCHContainerOperations>());
  if (!invocation.run())
    return {};
  return unit;
}
} // namespace ctk::clang_layer::snapshot
