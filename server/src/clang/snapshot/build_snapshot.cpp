#include "build_snapshot.hpp"
#include "ast_builder_action.hpp"
#include <clang/Basic/Diagnostic.h>
#include <clang/Basic/SourceManager.h>
#if __has_include(<clang/Options/Options.h>)
#include <clang/Options/Options.h>
#else
#include <clang/Driver/Options.h>
#endif
#include <clang/Tooling/CompilationDatabase.h>
#include <llvm/Option/Arg.h>
#include <llvm/Option/ArgList.h>
namespace ctk::clang_layer::snapshot {
namespace {
class ParseDiagnostics final : public clang::DiagnosticConsumer {
public:
  void HandleDiagnostic(clang::DiagnosticsEngine::Level level,
                        const clang::Diagnostic &diagnostic) override {
    clang::DiagnosticConsumer::HandleDiagnostic(level, diagnostic);
    if (level < clang::DiagnosticsEngine::Error || count_ >= 8)
      return;
    ++count_;
    llvm::SmallString<256> message;
    diagnostic.FormatDiagnostic(message);
    if (!text_.empty())
      text_ += '\n';
    if (diagnostic.hasSourceManager() && diagnostic.getLocation().isValid()) {
      const auto location = diagnostic.getSourceManager().getPresumedLoc(
          diagnostic.getLocation());
      if (location.isValid())
        text_ += std::string(location.getFilename()) + ":" +
                 std::to_string(location.getLine()) + ":" +
                 std::to_string(location.getColumn()) + ": ";
    }
    text_ +=
        level == clang::DiagnosticsEngine::Fatal ? "fatal error: " : "error: ";
    text_ += message.str().str();
    if (text_.size() > 8192) {
      text_.resize(8192);
      text_ += " [diagnostics truncated]";
      count_ = 8;
    }
  }

  const std::string &text() const { return text_; }

private:
  std::string text_;
  unsigned count_ = 0;
};
} // namespace
std::unique_ptr<clang::ASTUnit>
build_snapshot(const std::string &path,
               const std::vector<std::string> &arguments,
               const std::string &tool,
               llvm::IntrusiveRefCntPtr<llvm::vfs::FileSystem> filesystem,
               bool &volatile_input, std::unique_ptr<NativeAstWriter> &writer,
               std::string &diagnostic_text) {
  diagnostic_text.clear();
  auto diagnostics = std::make_unique<ParseDiagnostics>();
  std::unique_ptr<clang::ASTUnit> unit;
  AstBuilderAction action(unit, volatile_input, writer);
  auto files = llvm::makeIntrusiveRefCnt<clang::FileManager>(
      clang::FileSystemOptions(), filesystem);
  std::vector<std::string> command{tool, "-fsyntax-only"};
  for (const auto &argument : arguments)
    if (argument.starts_with("-working-directory="))
      if (auto error =
              filesystem->setCurrentWorkingDirectory(argument.substr(19))) {
        diagnostic_text =
            "cannot use compilation working directory: " + argument.substr(19) +
            ": " + error.message();
        return {};
      }
  auto cwd = filesystem->getCurrentWorkingDirectory();
  if (!cwd) {
    diagnostic_text = "cannot determine compilation working directory: " +
                      cwd.getError().message();
    return {};
  }
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
  if (missing_count) {
    diagnostic_text =
        "missing argument for compiler option: " + adjusted.at(missing_index);
    return {};
  }
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
  invocation.setDiagnosticConsumer(diagnostics.get());
  const bool success = invocation.run();
  diagnostic_text = diagnostics->text();
  // ASTUnit retains the diagnostic client; transfer its ownership before the
  // invocation's client leaves this scope, including on failed parses.
  if (unit)
    unit->getDiagnostics().setClient(diagnostics.release(), true);
  if (!success)
    return {};
  return unit;
}
} // namespace ctk::clang_layer::snapshot
