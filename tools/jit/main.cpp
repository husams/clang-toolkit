#include <exception>
#include <filesystem>
#include <memory>
#include <string>
#include <vector>

// LLVM 21's Interpreter header defaults a unique_ptr to this type.
#include <llvm/ExecutionEngine/Orc/LLJIT.h>

#include <clang/Basic/DiagnosticOptions.h>
#include <clang/Frontend/ASTUnit.h>
#include <clang/Frontend/CompilerInstance.h>
#include <clang/Frontend/TextDiagnosticPrinter.h>
#include <clang/Interpreter/Interpreter.h>
#include <clang/Tooling/ArgumentsAdjusters.h>
#include <clang/Tooling/JSONCompilationDatabase.h>
#include <clang/Tooling/Tooling.h>
#include <llvm/Support/Error.h>
#include <llvm/Support/MemoryBuffer.h>
#include <llvm/Support/TargetSelect.h>
#include <llvm/Support/raw_ostream.h>

#include "ctk/jit/runtime.hpp"

namespace {

namespace fs = std::filesystem;
namespace tooling = clang::tooling;

llvm::Error failure(const llvm::Twine &message) {
  return llvm::createStringError(llvm::inconvertibleErrorCode(), message);
}

llvm::Expected<std::unique_ptr<clang::ASTUnit>>
parse_target(const fs::path &target_path, fs::path database_path,
             clang::DiagnosticConsumer &diagnostics) {
  if (fs::is_directory(database_path))
    database_path /= "compile_commands.json";

  std::string message;
  auto database = tooling::JSONCompilationDatabase::loadFromFile(
      database_path.string(), message,
      tooling::JSONCommandLineSyntax::AutoDetect);
  if (!database)
    return failure(llvm::Twine("compilation database: ") + message);

  const auto file = fs::absolute(target_path).lexically_normal().string();
  const auto commands = database->getCompileCommands(file);
  if (commands.empty())
    return failure(llvm::Twine("no compile command for ") + file);
  if (commands.size() != 1)
    return failure(llvm::Twine("multiple compile commands for ") + file);

  tooling::ClangTool tool(*database, {file});
  tool.setDiagnosticConsumer(&diagnostics);
  tooling::CommandLineArguments defaults{std::string("-resource-dir=") +
                                         CTK_JIT_RESOURCE_DIR};
  if (llvm::StringRef(CTK_JIT_SYSROOT) != "") {
    defaults.push_back("-isysroot");
    defaults.push_back(CTK_JIT_SYSROOT);
  }
  tool.appendArgumentsAdjuster(tooling::getInsertArgumentAdjuster(
      defaults, tooling::ArgumentInsertPosition::BEGIN));
  std::vector<std::unique_ptr<clang::ASTUnit>> asts;
  if (tool.buildASTs(asts) != 0 || asts.size() != 1 ||
      diagnostics.getNumErrors() != 0 ||
      asts.front()->getDiagnostics().hasErrorOccurred())
    return failure(llvm::Twine("could not parse target ") + file);
  return std::move(asts.front());
}

llvm::Error run(const char *target_path, const char *database_path,
                const char *source_dir) {
  if (llvm::InitializeNativeTarget() ||
      llvm::InitializeNativeTargetAsmPrinter())
    return failure("could not initialize LLVM's native target");

  auto source = llvm::MemoryBuffer::getSTDIN();
  if (!source)
    return llvm::errorCodeToError(source.getError());

  clang::DiagnosticOptions diagnostic_options;
  clang::TextDiagnosticPrinter diagnostics(llvm::errs(), diagnostic_options);
  auto ast = parse_target(target_path, database_path, diagnostics);
  if (!ast)
    return ast.takeError();

  // PIC lets ELF JIT code reference host data outside the small code range.
  std::vector<const char *> args{
      "-std=c++20",
      "-fPIC",
      "-resource-dir",
      CTK_JIT_RESOURCE_DIR,
      "-I",
      CTK_JIT_SDK_INCLUDE,
      "-I",
      CTK_JIT_CLANG_INCLUDE,
      "-I",
      CTK_JIT_LLVM_INCLUDE,
      "-iquote",
      source_dir,
  };
  if (llvm::StringRef(CTK_JIT_SYSROOT) != "") {
    args.push_back("-isysroot");
    args.push_back(CTK_JIT_SYSROOT);
  }
  clang::IncrementalCompilerBuilder builder;
  builder.SetCompilerArgs(args);
  auto compiler = builder.CreateCpp();
  if (!compiler)
    return compiler.takeError();
  auto interpreter = clang::Interpreter::create(std::move(*compiler));
  if (!interpreter)
    return interpreter.takeError();
  if (auto error = (*interpreter)->ParseAndExecute((*source)->getBuffer()))
    return error;
  if (auto error =
          (*interpreter)
              ->ParseAndExecute(
                  R"cpp(extern "C" void ctk_jit_run_v1(ctk::jit::RunContext *ctx) {
                   run(*ctx);
                 })cpp"))
    return error;

  auto entry = (*interpreter)->getSymbolAddress("ctk_jit_run_v1");
  if (!entry)
    return entry.takeError();
  ctk::jit::RunContext context((*ast)->getASTContext());
  entry->toPtr<void (*)(ctk::jit::RunContext *)>()(&context);
  return llvm::Error::success();
}

} // namespace

int main(int argc, char **argv) {
  if (argc != 4) {
    llvm::errs() << "usage: ctk-jit-runner FILE COMPDB SCRIPT_DIRECTORY\n";
    return 2;
  }
  try {
    if (auto error = run(argv[1], argv[2], argv[3])) {
      llvm::logAllUnhandledErrors(std::move(error), llvm::errs(), "ctk-jit: ");
      return 1;
    }
  } catch (const std::exception &error) {
    llvm::errs() << "ctk-jit: " << error.what() << '\n';
    return 1;
  }
  return 0;
}
