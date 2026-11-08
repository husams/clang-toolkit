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
  const auto file = fs::absolute(target_path).lexically_normal().string();
  std::string message;
  std::unique_ptr<tooling::CompilationDatabase> database;
  if (database_path.empty()) {
    database = tooling::CompilationDatabase::autoDetectFromSource(file, message);
    if (!database) {
      database = std::make_unique<tooling::FixedCompilationDatabase>(
          fs::path(file).parent_path().string(),
          std::vector<std::string>{fs::path(file).extension() == ".c" ? "-std=c17" : "-std=c++20"});
    }
  } else {
    if (fs::is_directory(database_path))
      database_path /= "compile_commands.json";
    database = tooling::JSONCompilationDatabase::loadFromFile(
        database_path.string(), message, tooling::JSONCommandLineSyntax::AutoDetect);
    if (!database)
      return failure(llvm::Twine("compilation database: ") + message);
  }

  const auto commands = database->getCompileCommands(file);
  if (commands.empty())
    return failure(llvm::Twine("no compile command for ") + file);
  if (commands.size() != 1)
    return failure(llvm::Twine("multiple compile commands for ") + file);

  tooling::ClangTool tool(*database, {file});
  tool.setDiagnosticConsumer(&diagnostics);
  const auto directory = fs::absolute(commands.front().Directory);
  tool.appendArgumentsAdjuster(
      [&](const tooling::CommandLineArguments &arguments, llvm::StringRef) {
        auto normalized = arguments;
        // The AST's input spelling is visible to file matchers.
        for (std::size_t index = 1; index < normalized.size(); ++index) {
          auto &argument = normalized[index];
          if (argument.empty() || argument.front() == '-')
            continue;
          if ((directory / argument).lexically_normal() == file)
            argument = file;
        }
        return normalized;
      });
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
              llvm::json::Array{CTK_JIT_CLANG_LIBRARY, CTK_JIT_LLVM_LIBRARY,
                                CTK_JIT_ICU_LIBRARY, CTK_JIT_ICU_DATA, CTK_JIT_YAML_LIBRARY}},
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
                const char *prelude, const char *script_arguments) {
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
  const bool native_ir = mode == "ir" || mode == "ir-object" || mode == "repl";
  std::unique_ptr<clang::ASTUnit> ast;
  std::string default_file;
  if (*target_path) {
    default_file = fs::absolute(target_path).lexically_normal().string();
    if (!native_ir) {
      auto loaded = parse_target(target_path, database_path, diagnostics);
      if (!loaded)
        return loaded.takeError();
      ast = std::move(*loaded);
    }
  }
  ctk::jit::ScriptArguments arguments;
  if (script_arguments) {
    auto decoded = llvm::json::parse(script_arguments);
    if (!decoded)
      return decoded.takeError();
    const auto* object = decoded->getAsObject();
    if (!object)
      return failure("script arguments must be a JSON object");
    for (const auto& [name, value] : *object) {
      const auto text = value.getAsString();
      if (!text)
        return failure("script arguments must be strings");
      arguments.emplace_back(name.str(), text->str());
    }
  }
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
  auto* context_ast = ast ? &ast->getASTContext() : nullptr;
  if (mode == "repl")
    return ctk::jit::repl_ir(default_file, database_path, load, arguments);
  if (mode == "ir" || mode == "ir-object")
    return ctk::jit::run_ir(std::move(input), mode == "ir-object",
                            default_file, database_path, load, arguments);
  if (!context_ast)
    return failure("the C++ backend requires a target file");
  ctk::jit::RunContext context(*context_ast);
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
  const bool ir = (argc == 4 || argc == 5) &&
                  (mode == "ir" || mode == "ir-object" || mode == "repl");
  const bool query = (argc == 4 && mode == "object") || ir;
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
                         source && argc == 6 ? argv[5] : nullptr,
                         ir && argc == 5 ? argv[4] : nullptr)) {
      llvm::logAllUnhandledErrors(std::move(error), llvm::errs(), "ctk-jit: ");
      return 1;
    }
  } catch (const std::exception &error) {
    llvm::errs() << "ctk-jit: " << error.what() << '\n';
    return 1;
  }
  return 0;
}
