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
#include <llvm/ADT/StringExtras.h>
#include <llvm/Config/llvm-config.h>
#include <llvm/Support/Error.h>
#include <llvm/Support/FileSystem.h>
#include <llvm/Support/JSON.h>
#include <llvm/Support/MemoryBuffer.h>
#include <llvm/Support/TargetSelect.h>
#include <llvm/Support/VirtualFileSystem.h>
#include <llvm/Support/raw_ostream.h>
#include <llvm/TargetParser/Host.h>
#include <llvm/TargetParser/Triple.h>

#include "ctk/jit/runtime.hpp"
#include "grammar/lower.hpp"
#include "grammar/syntax.hpp"
#include "ir.hpp"
#include "native_prompt.hpp"
#include "native_workspace.hpp"
#include "platform/launch.hpp"
#include "script_artifact.hpp"

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
  } else {
    if (fs::is_directory(database_path))
      database_path /= "compile_commands.json";
    database = tooling::JSONCompilationDatabase::loadFromFile(
        database_path.string(), message, tooling::JSONCommandLineSyntax::AutoDetect);
    if (!database)
      return failure(llvm::Twine("compilation database: ") + message);
    database = tooling::inferTargetAndDriverMode(tooling::expandResponseFiles(
        std::move(database), llvm::vfs::getRealFileSystem()));
  }
  if (!database) {
    database = std::make_unique<tooling::FixedCompilationDatabase>(
        fs::path(file).parent_path().string(),
        std::vector<std::string>{fs::path(file).extension() == ".c"
                                     ? "-std=c17" : "-std=c++20"});
  } else {
    database = tooling::inferToolLocation(std::move(database));
  }

  const auto commands = database->getCompileCommands(file);
  if (commands.empty())
    return failure(llvm::Twine("no compile command for ") + file);
  if (commands.size() != 1)
    return failure(llvm::Twine("multiple compile commands for ") + file);
  if (commands.front().CommandLine.empty())
    return failure(llvm::Twine("compile command has no driver for ") + file);

  // FixedCompilationDatabase supplies this placeholder when there is no
  // project driver, including for compile_flags.txt.
  const bool use_default_toolchain =
      fs::path(commands.front().CommandLine.front()).filename() == "clang-tool" &&
      database->getAllFiles().empty();

  tooling::ClangTool tool(*database, {file});
  tool.setDiagnosticConsumer(&diagnostics);
  const auto directory = fs::absolute(commands.front().Directory);
  tool.appendArgumentsAdjuster(
      [&](const tooling::CommandLineArguments &arguments, llvm::StringRef) {
        auto normalized = arguments;
        const auto driver = fs::path(normalized.front());
        if (driver.has_parent_path() && !driver.is_absolute())
          normalized.front() = (directory / driver).string();
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
  const bool use_default_sysroot = use_default_toolchain ||
      ctk::jit::apple_driver_needs_sdk(commands.front().CommandLine,
                                      commands.front().Directory);
  if (use_default_sysroot && llvm::StringRef(CTK_JIT_SYSROOT) != "") {
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

llvm::Error initialize_native_target() {
  if (llvm::InitializeNativeTarget() ||
      llvm::InitializeNativeTargetAsmPrinter())
    return failure("could not initialize LLVM's native target");
  return llvm::Error::success();
}

llvm::Error run(llvm::StringRef mode, const char *target_path,
                const char *database_path, const char *source_dir,
                const char *prelude, const char *script_arguments,
                std::unique_ptr<llvm::MemoryBuffer> input = nullptr,
                bool *prompt_failed = nullptr) {
  if (auto error = initialize_native_target())
    return error;
  const bool interactive = mode == "repl" || mode == "workspace" || mode == "prompt";
  if (!input && !interactive) {
    auto buffer = llvm::MemoryBuffer::getSTDIN();
    if (!buffer)
      return llvm::errorCodeToError(buffer.getError());
    input = std::move(*buffer);
  }
  if (mode == "compile-ir")
    return ctk::jit::compile_ir(input->getBuffer());

  clang::DiagnosticOptions diagnostic_options;
  clang::TextDiagnosticPrinter diagnostics(llvm::errs(), diagnostic_options);
  const bool native_ir = mode == "ir" || mode == "ir-object" || interactive;
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
    std::string workspace_diagnostics;
    llvm::raw_string_ostream buffered(workspace_diagnostics);
    const bool workspace = mode == "workspace";
    auto& diagnostic_output = workspace ? static_cast<llvm::raw_ostream&>(buffered) : llvm::errs();
    clang::TextDiagnosticPrinter printer(diagnostic_output, diagnostic_options);
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
      if (!unit) {
        auto error = unit.takeError();
        if (!workspace_diagnostics.empty())
          return failure(llvm::toString(std::move(error)) + "\n" + workspace_diagnostics);
        return error;
      }
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
        unit->getDiagnostics().hasErrorOccurred()) {
      if (!workspace_diagnostics.empty())
        return failure("could not parse C++ snippet\n" + workspace_diagnostics);
      return failure("could not parse C++ snippet");
    }
    unit->getDiagnostics().setClient(new clang::IgnoringDiagConsumer());
    return unit;
  };
  auto* context_ast = ast ? &ast->getASTContext() : nullptr;
  if (mode == "workspace")
    return ctk::jit::run_native_workspace(default_file, database_path, load, arguments);
  if (mode == "prompt")
    return ctk::jit::run_native_prompt(default_file, database_path, load, arguments, *prompt_failed);
  if (mode == "repl")
    return ctk::jit::repl_ir(default_file, database_path, load, arguments);
  if (mode == "ir" || mode == "ir-object")
    return ctk::jit::run_ir(std::move(input), mode == "ir-object",
                            default_file, database_path, load, arguments, prompt_failed != nullptr);
  if (!context_ast)
    return failure("the C++ backend requires a target file");
  ctk::jit::RunContext context(*context_ast);
  if (source_dir)
    return run_source(input->getBuffer(), source_dir, prelude, context);
  return run_object(std::move(input), context);
}

} // namespace

static void public_usage(llvm::StringRef command) {
  if (command == "run")
    llvm::outs() << "usage: ctk-jit run SCRIPT | --bundle BUNDLE [--file FILE] [--compdb COMPDB]\n"
                    "       [--arg NAME=VALUE] [--no-cache] [--llvm-ir | --cpp-jit] [--runner RUNNER]\n";
  else if (command == "precompile")
    llvm::outs() << "usage: ctk-jit precompile SCRIPT -o BUNDLE [--no-cache]\n"
                    "       [--llvm-ir | --cpp-jit] [--runner RUNNER]\n";
  else if (command == "repl")
    llvm::outs() << "usage: ctk-jit repl [--ui [prompt|workspace]] [--file FILE] [--compdb COMPDB]\n"
                    "       [--arg NAME=VALUE] [--runner RUNNER]\n";
  else
    llvm::outs() << "usage: ctk-jit {run,repl,precompile} [options]\n";
}

static llvm::Error public_cli(int argc, char **argv, bool &prompt_failed) {
  const llvm::StringRef command(argv[1]);
  const bool repl = command == "repl";
  const bool build = command == "precompile";
  std::string script, bundle, output, file, database, runner;
  llvm::json::Object arguments;
  std::optional<bool> backend;
  bool workspace = false;
  bool no_cache = false;
  std::vector<char *> forward{argv[0], argv[1]};
  for (int index = 2; index < argc; ++index) {
    const int first = index;
    const llvm::StringRef argument(argv[index]);
    const auto [flag, inline_value] = argument.split('=');
    const bool assigned = argument.contains('=');
    if (!assigned && (flag == "--help" || flag == "-h")) {
      public_usage(command);
      return llvm::Error::success();
    }
    if (!argument.starts_with("-")) {
      if (repl || !script.empty())
        return failure(llvm::Twine("unexpected argument ") + argument);
      script = argument.str();
    } else if (repl && (flag == "--ui" || flag == "--u")) {
      auto ui = assigned ? inline_value : llvm::StringRef("workspace");
      if (!assigned && index + 1 < argc && argv[index + 1][0] != '-')
        ui = argv[++index];
      if (ui != "prompt" && ui != "workspace")
        return failure("--ui expects prompt or workspace");
      workspace = ui == "workspace";
    } else if (!repl && !assigned && (flag == "--llvm-ir" || flag == "--cpp-jit")) {
      const bool ir = flag == "--llvm-ir";
      if (backend && *backend != ir)
        return failure("--llvm-ir and --cpp-jit are mutually exclusive");
      backend = ir;
    } else if (!repl && !assigned && flag == "--no-cache") {
      no_cache = true;
    } else {
      std::string *destination = nullptr;
      if (flag == "--runner") destination = &runner;
      else if (!build && flag == "--file") destination = &file;
      else if (!build && flag == "--compdb") destination = &database;
      else if (build && (flag == "--output" || flag == "-o")) destination = &output;
      else if (!repl && !build && flag == "--bundle") destination = &bundle;
      else if (build || flag != "--arg")
        return failure(llvm::Twine("unknown option ") + flag);
      if (!assigned && (index + 1 == argc || llvm::StringRef(argv[index + 1]).starts_with("--")))
        return failure(llvm::Twine("missing value for ") + flag);
      const auto value = assigned ? inline_value : llvm::StringRef(argv[++index]);
      if (destination) {
        *destination = value.str();
        if (flag == "--runner")
          continue;
      } else {
        const auto [name, item] = value.split('=');
        if (!value.contains('=') || name.empty() ||
            !(llvm::isAlpha(name.front()) || name.front() == '_') ||
            !llvm::all_of(name, [](char ch) { return llvm::isAlnum(ch) || ch == '_'; }))
          return failure("--arg expects NAME=VALUE");
        if (arguments.get(name))
          return failure(llvm::Twine("duplicate script argument '") + name + "'");
        arguments[name] = item;
      }
    }
    forward.insert(forward.end(), argv + first, argv + index + 1);
  }

  if (file.empty())
    if (auto target = arguments.getString("file"))
      file = target->str();
  auto encoded = llvm::formatv("{0}", llvm::json::Value(std::move(arguments))).str();
  if (!runner.empty()) {
    forward.push_back(nullptr);
    return ctk::jit::launch_cli(runner, forward.data());
  }
  if (repl) {
    ctk::jit::configure_ast_cache();
    return run(workspace ? "workspace" : "prompt", file.c_str(), database.c_str(),
               nullptr, nullptr, encoded.c_str(), nullptr, &prompt_failed);
  }

  if (script.empty() == bundle.empty())
    return failure("provide either a script or --bundle");
  if (build && output.empty())
    return failure("precompile requires --output");
  if (backend && script.empty())
    return failure("a backend option requires a source script");
  const auto extension = fs::path(script).extension();
  if (!script.empty() && extension != ".ctk" && extension != ".cpp")
    return failure("expected a .ctk script or .cpp extension");
  const bool ir = backend.value_or(extension == ".ctk");
  if (ir && extension != ".ctk")
    return failure("--llvm-ir requires a .ctk script");
  static int executable_anchor;
  const auto executable = llvm::sys::fs::getMainExecutable(argv[0], &executable_anchor);
  const ctk::jit::ScriptToolchain toolchain{
      CTK_JIT_COMPILER, script_flags(), executable, CTK_JIT_SDK_INCLUDE "/ctk/jit/runtime.hpp",
      {CTK_JIT_COMPILER, CTK_JIT_CLANG_LIBRARY, CTK_JIT_LLVM_LIBRARY,
       CTK_JIT_ICU_LIBRARY, CTK_JIT_ICU_DATA, CTK_JIT_YAML_LIBRARY}};
  if (auto error = initialize_native_target())
    return error;
  if (build)
    return ctk::jit::precompile_script(script, output, ir, no_cache, toolchain);

  auto program = bundle.empty() ? ctk::jit::script_program(script, ir, no_cache, toolchain)
                               : ctk::jit::read_script_bundle(bundle, toolchain);
  if (!program)
    return program.takeError();
  if (!program->llvm_ir && encoded != "{}")
    return failure("--arg is available for the LLVM IR backend");
  ctk::jit::configure_ast_cache();
  const auto mode = program->llvm_ir ? (program->object ? "ir-object" : "ir")
                                   : (program->object ? "object" : "source");
  return run(mode, file.c_str(), database.c_str(),
             program->object ? nullptr : program->quote_directory.c_str(),
             nullptr, encoded.c_str(), std::move(program->input), &prompt_failed);
}

static llvm::json::Array syntax_json(const ctk::jit::Syntax& tree) {
  llvm::json::Array value;
  value.emplace_back(tree.name);
  if (!tree.text.empty())
    value.emplace_back(tree.text);
  for (const auto& child : tree.children)
    value.push_back(syntax_json(child));
  return value;
}

int main(int argc, char **argv) {
  const llvm::StringRef mode = argc >= 2 ? argv[1] : "";
  if (mode == "--help" || mode == "-h" || argc == 1) {
    public_usage({});
    return argc == 1 ? 2 : 0;
  }
  const bool internal_repl = mode == "repl" && (argc == 4 || argc == 5) &&
      fs::path(argv[0]).filename() != "ctk-jit" && argv[2][0] != '-';
  if (mode == "run" || mode == "precompile" || (mode == "repl" && !internal_repl)) {
    try {
      bool prompt_failed = false;
      if (auto error = public_cli(argc, argv, prompt_failed)) {
        llvm::logAllUnhandledErrors(std::move(error), llvm::errs(), "ctk-jit: ");
        return 1;
      }
      return prompt_failed ? 1 : 0;
    } catch (const std::exception &error) {
      llvm::errs() << "ctk-jit: " << error.what() << '\n';
      return 1;
    }
  }
  if (argc == 2 && (mode == "parse-ctk" || mode == "lower-ctk")) {
    auto input = llvm::MemoryBuffer::getSTDIN();
    if (!input) {
      llvm::errs() << "ctk-jit: " << input.getError().message() << '\n';
      return 1;
    }
    if (mode == "lower-ctk") {
      auto ir = ctk::jit::lower_ctk((*input)->getBuffer());
      if (!ir) {
        llvm::logAllUnhandledErrors(ir.takeError(), llvm::errs(), "ctk-jit: ");
        return 1;
      }
      llvm::outs() << *ir;
      return 0;
    }
    auto tree = ctk::jit::parse_ctk((*input)->getBuffer());
    if (!tree) {
      llvm::logAllUnhandledErrors(tree.takeError(), llvm::errs(), "ctk-jit: ");
      return 1;
    }
    llvm::outs() << llvm::json::Value(syntax_json(*tree)) << '\n';
    return 0;
  }
  if (argc == 2 && mode == "config") {
    print_config();
    return 0;
  }
  const bool source = mode == "source" && (argc == 5 || argc == 6);
  const bool ir = (argc == 4 || argc == 5) &&
                  (mode == "ir" || mode == "ir-object" || mode == "repl" || mode == "workspace");
  const bool query = (argc == 4 && mode == "object") || ir;
  const bool compile = argc == 2 && mode == "compile-ir";
  if (!source && !query && !compile) {
    llvm::errs()
        << "usage: ctk-jit-runner source FILE COMPDB SCRIPT_DIRECTORY [PCH]\n"
           "       ctk-jit-runner object|ir|ir-object|repl|workspace FILE COMPDB\n"
           "       ctk-jit-runner compile-ir\n";
    return 2;
  }
  try {
    if (!compile)
      ctk::jit::configure_ast_cache();
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
