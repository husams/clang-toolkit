#include "build_snapshot.hpp"
#include "ast_builder_action.hpp"
#if __has_include(<clang/Options/Options.h>)
#include <clang/Options/Options.h>
#else
#include <clang/Driver/Options.h>
#endif
#include <clang/Tooling/CompilationDatabase.h>
#include <llvm/Option/Arg.h>
#include <llvm/Option/ArgList.h>
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
  for (const auto &argument : arguments)
    if (argument.starts_with("-working-directory="))
      if (filesystem->setCurrentWorkingDirectory(argument.substr(19)))
        return {};
  auto cwd = filesystem->getCurrentWorkingDirectory();
  if (!cwd)
    return {};
  auto database = clang::tooling::expandResponseFiles(
      std::make_unique<clang::tooling::FixedCompilationDatabase>(*cwd,
                                                                 arguments),
      filesystem);
  auto expanded = database->getCompileCommands(path).front().CommandLine;
  expanded.erase(expanded.begin());
  auto adjusted =
      clang::tooling::getClangStripDependencyFileAdjuster()(expanded, path);
  adjusted = clang::tooling::getClangStripOutputAdjuster()(adjusted, path);
  adjusted = clang::tooling::getClangSyntaxOnlyAdjuster()(adjusted, path);
  std::vector<const char *> argv;
  for (const auto &argument : adjusted)
    argv.push_back(argument.c_str());
  unsigned missing_index = 0, missing_count = 0;
#if __has_include(<clang/Options/Options.h>)
  const auto &options = clang::getDriverOptTable();
  const auto input_option = clang::options::OPT_INPUT;
#else
  const auto &options = clang::driver::getDriverOptTable();
  const auto input_option = clang::driver::options::OPT_INPUT;
#endif
  const auto parsed = options.ParseArgs(argv, missing_index, missing_count);
  if (missing_count)
    return {};
  llvm::opt::ArgStringList rendered;
  for (const auto *argument : parsed) {
    if (argument->getOption().getID() == input_option)
      continue;
    argument->render(parsed, rendered);
  }
  for (const auto *argument : rendered)
    command.emplace_back(argument);
  command.push_back(path);
  clang::tooling::ToolInvocation invocation(
      command, &action, files.get(),
      std::make_shared<clang::PCHContainerOperations>());
  if (!invocation.run())
    return {};
  return unit;
}
} // namespace ctk::clang_layer::snapshot
