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
#include <llvm/Config/llvm-config.h>
#include <llvm/Support/Error.h>
#include <llvm/Support/JSON.h>
#include <llvm/Support/MemoryBuffer.h>
#include <llvm/Support/TargetSelect.h>
#include <llvm/Support/raw_ostream.h>
#include <llvm/TargetParser/Host.h>
#include <llvm/TargetParser/Triple.h>

#include "ctk/jit/runtime.hpp"
#include "ir.hpp"

namespace {

namespace fs = std::filesystem;
namespace tooling = clang::tooling;

using EntryPoint = void (*)(ctk::jit::RunContext *);
constexpr auto entry_symbol = "ctk_jit_run_v1";

llvm::Error failure(const llvm::Twine &message) {
  return llvm::createStringError(llvm::inconvertibleErrorCode(), message);
}

llvm::Expected<std::unique_ptr<clang::ASTUnit>>
parse_target(const fs::path &target_path, fs::path database_path,
             clang::DiagnosticConsumer &diagnostics,
             llvm::ArrayRef<std::string> overrides = {},
             std::optional<llvm::StringRef> source = std::nullopt) {
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
  if (!overrides.empty()) {
    tool.appendArgumentsAdjuster(tooling::getInsertArgumentAdjuster(
        tooling::CommandLineArguments(overrides.begin(), overrides.end()),
        tooling::ArgumentInsertPosition::END));
  }
  if (source)
    tool.mapVirtualFile(file, *source);
  std::vector<std::unique_ptr<clang::ASTUnit>> asts;
  if (tool.buildASTs(asts) != 0 || asts.size() != 1 ||
      diagnostics.getNumErrors() != 0 ||
      asts.front()->getDiagnostics().hasErrorOccurred())
    return failure(llvm::Twine("could not parse target ") + file);
  return std::move(asts.front());
}

std::vector<const char *> script_flags() {
  // Distro clang drivers can use a different vendor triple than the
  // interpreter.
  static const auto target = "--target=" + llvm::sys::getProcessTriple();
  // PIC lets ELF JIT code reference host data outside the small code range.
  std::vector<const char *> args{
      "-std=c++20",          "-fPIC", target.c_str(),       "-resource-dir",
      CTK_JIT_RESOURCE_DIR,  "-I",    CTK_JIT_SDK_INCLUDE,  "-I",
      CTK_JIT_CLANG_INCLUDE, "-I",    CTK_JIT_LLVM_INCLUDE,
  };
  if (llvm::StringRef(CTK_JIT_SYSROOT) != "") {
    args.push_back("-isysroot");
    args.push_back(CTK_JIT_SYSROOT);
  }
  return args;
}

void print_config() {
  llvm::json::Array flags;
  for (const auto *flag : script_flags())
    flags.emplace_back(flag);
  const llvm::Triple target(llvm::sys::getProcessTriple());
  // Incremental PCH code generation is verified on Apple arm64 with LLVM 22.
  const bool use_prelude =
      LLVM_VERSION_MAJOR >= 22 && target.isOSDarwin() && target.isAArch64();
  llvm::outs()
      << llvm::json::Value(llvm::json::Object{
             {"compiler", CTK_JIT_COMPILER},
             {"flags", std::move(flags)},
             {"llvm", LLVM_VERSION_STRING},
             {"target", target.str()},
             {"prelude", use_prelude ? llvm::json::Value(CTK_JIT_PRELUDE)
                                     : llvm::json::Value(nullptr)},
             {"libraries",
              llvm::json::Array{CTK_JIT_CLANG_LIBRARY, CTK_JIT_LLVM_LIBRARY}},
             {"runtime_header", CTK_JIT_SDK_INCLUDE "/ctk/jit/runtime.hpp"},
         })
      << '\n';
}

llvm::Error run_source(llvm::StringRef source, const char *source_dir,
                       const char *prelude, ctk::jit::RunContext &context) {
  auto args = script_flags();
  if (*source_dir) {
    args.push_back("-iquote");
    args.push_back(source_dir);
  }
  if (prelude) {
    args.push_back("-include-pch");
    args.push_back(prelude);
  }
  clang::IncrementalCompilerBuilder builder;
  builder.SetCompilerArgs(args);
  auto compiler = builder.CreateCpp();
  if (!compiler)
    return compiler.takeError();
  auto interpreter = clang::Interpreter::create(std::move(*compiler));
  if (!interpreter)
    return interpreter.takeError();
  if (auto error = (*interpreter)->ParseAndExecute(source))
    return error;

  auto entry = (*interpreter)->getSymbolAddress(entry_symbol);
  if (!entry)
    return entry.takeError();
  entry->toPtr<EntryPoint>()(&context);
  return llvm::Error::success();
}

llvm::Error run_object(std::unique_ptr<llvm::MemoryBuffer> object,
                       ctk::jit::RunContext &context) {
  auto jit = llvm::orc::LLJITBuilder().create();
  if (!jit)
    return jit.takeError();
  if (auto error = (*jit)->addObjectFile(std::move(object)))
    return error;
  auto entry = (*jit)->lookup(entry_symbol);
  if (!entry)
    return entry.takeError();
  auto &dylib = (*jit)->getMainJITDylib();
  if (auto error = (*jit)->initialize(dylib))
    return error;
  entry->toPtr<EntryPoint>()(&context);
  return (*jit)->deinitialize(dylib);
}

llvm::Error run(llvm::StringRef mode, const char *target_path,
                const char *database_path, const char *source_dir,
                const char *prelude) {
  if (llvm::InitializeNativeTarget() ||
      llvm::InitializeNativeTargetAsmPrinter())
    return failure("could not initialize LLVM's native target");

  std::unique_ptr<llvm::MemoryBuffer> input;
  if (mode != "repl") {
    auto buffer = llvm::MemoryBuffer::getSTDIN();
    if (!buffer)
      return llvm::errorCodeToError(buffer.getError());
    input = std::move(*buffer);
  }
  if (mode == "compile-ir")
    return ctk::jit::compile_ir(input->getBuffer());

  clang::DiagnosticOptions diagnostic_options;
  clang::TextDiagnosticPrinter diagnostics(llvm::errs(), diagnostic_options);
  auto ast = parse_target(target_path, database_path, diagnostics);
  if (!ast)
    return ast.takeError();

  const auto default_file =
      fs::absolute(target_path).lexically_normal().string();
  const ctk::jit::LoadTarget load = [&](const ctk::jit::TargetRequest &request)
      -> llvm::Expected<std::unique_ptr<clang::ASTUnit>> {
    clang::TextDiagnosticPrinter printer(llvm::errs(), diagnostic_options);
    auto file = fs::path(request.file);
    if (!file.empty() && !file.is_absolute() && !request.directory.empty())
      file = fs::path(request.directory) / file;
    if (!file.empty() || !request.source) {
      const auto database = request.compilation_database.empty()
                                ? fs::path(database_path)
                                : fs::path(request.compilation_database);
      const auto source = request.source
                              ? std::optional<llvm::StringRef>(*request.source)
                              : std::nullopt;
      auto unit =
          parse_target(file, database, printer, request.arguments, source);
      if (!unit)
        return unit.takeError();
      (*unit)->getDiagnostics().setClient(new clang::IgnoringDiagConsumer());
      return unit;
    }

    std::vector<std::string> args{"-std=c++20", std::string("-resource-dir=") +
                                                    CTK_JIT_RESOURCE_DIR};
    if (llvm::StringRef(CTK_JIT_SYSROOT) != "") {
      args.push_back("-isysroot");
      args.push_back(CTK_JIT_SYSROOT);
    }
    args.insert(args.end(), request.arguments.begin(), request.arguments.end());
    const auto snippet =
        fs::absolute(fs::path(request.directory) / ".ctk-snippet.cpp");
    auto unit = tooling::buildASTFromCodeWithArgs(
        *request.source, args, snippet.string(), CTK_JIT_COMPILER,
        std::make_shared<clang::PCHContainerOperations>(),
        tooling::getClangStripDependencyFileAdjuster(), {}, &printer);
    if (!unit || printer.getNumErrors() ||
        unit->getDiagnostics().hasErrorOccurred())
      return failure("could not parse C++ snippet");
    unit->getDiagnostics().setClient(new clang::IgnoringDiagConsumer());
    return unit;
  };
  if (mode == "repl")
    return ctk::jit::repl_ir((*ast)->getASTContext(), default_file, load);
  if (mode == "ir" || mode == "ir-object")
    return ctk::jit::run_ir(std::move(input), (*ast)->getASTContext(),
                            mode == "ir-object", default_file, load);
  ctk::jit::RunContext context((*ast)->getASTContext());
  if (source_dir)
    return run_source(input->getBuffer(), source_dir, prelude, context);
  return run_object(std::move(input), context);
}

} // namespace

int main(int argc, char **argv) {
  const llvm::StringRef mode = argc >= 2 ? argv[1] : "";
  if (argc == 2 && mode == "config") {
    print_config();
    return 0;
  }
  const bool source = mode == "source" && (argc == 5 || argc == 6);
  const bool query = argc == 4 && (mode == "object" || mode == "ir" ||
                                  mode == "ir-object" || mode == "repl");
  const bool compile = argc == 2 && mode == "compile-ir";
  if (!source && !query && !compile) {
    llvm::errs()
        << "usage: ctk-jit-runner source FILE COMPDB SCRIPT_DIRECTORY [PCH]\n"
           "       ctk-jit-runner object|ir|ir-object|repl FILE COMPDB\n"
           "       ctk-jit-runner compile-ir\n";
    return 2;
  }
  try {
    if (auto error = run(mode, compile ? nullptr : argv[2],
                         compile ? nullptr : argv[3], source ? argv[4] : nullptr,
                         argc == 6 ? argv[5] : nullptr)) {
      llvm::logAllUnhandledErrors(std::move(error), llvm::errs(), "ctk-jit: ");
      return 1;
    }
  } catch (const std::exception &error) {
    llvm::errs() << "ctk-jit: " << error.what() << '\n';
    return 1;
  }
  return 0;
}
