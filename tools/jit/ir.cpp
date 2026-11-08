#include "ir.hpp"
#include "values.hpp"

#include <cstdint>
#include <filesystem>
#include <iostream>
#include <memory>
#include <string>
#include <vector>

#include <clang/ASTMatchers/ASTMatchFinder.h>
#include <clang/ASTMatchers/Dynamic/Parser.h>
#include <clang/ASTMatchers/Dynamic/Registry.h>
#include <clang/Frontend/ASTUnit.h>
#include <llvm/ADT/ArrayRef.h>
#include <llvm/ADT/DenseMap.h>
#include <llvm/ADT/StringMap.h>
#include <llvm/AsmParser/Parser.h>
#include <llvm/ExecutionEngine/Orc/CompileUtils.h>
#include <llvm/ExecutionEngine/Orc/LLJIT.h>
#include <llvm/IR/Verifier.h>
#include <llvm/Support/JSON.h>
#include <llvm/Support/SourceMgr.h>
#include <llvm/Target/TargetMachine.h>
#include <llvm/TargetParser/Host.h>

namespace ctk::jit {
namespace {

namespace dynamic = clang::ast_matchers::dynamic;
using clang::FunctionDecl;
using clang::ast_matchers::MatchFinder;
using DynamicMatcher = clang::ast_matchers::internal::DynTypedMatcher;
using MatcherCache = llvm::StringMap<DynamicMatcher>;

// Layout of the generated LLVM IR's %arg on the runner's target.
struct MatcherArg {
  const char* name;
  const char* literal;
  const MatcherArg* children;
  std::uint32_t count;
};

struct Targets {
  Targets(clang::ASTContext& ast, llvm::StringRef file, const LoadTarget& load)
      : ast(&ast, [](clang::ASTContext*) {})
      , file(file)
      , load(load) {}

  AstHandle ast;
  llvm::StringRef file;
  const LoadTarget& load;
  llvm::StringMap<AstHandle> files;

  static AstHandle own(std::unique_ptr<clang::ASTUnit> unit) {
    auto* ast = &unit->getASTContext();
    return AstHandle(std::shared_ptr<clang::ASTUnit>(std::move(unit)), ast);
  }

  Bindings bindings() const {
    auto args = std::make_shared<Record>();
    args->set("file", {file.str()});
    Bindings bindings;
    bindings.try_emplace("arg", Value{std::move(args)});
    return bindings;
  }

  llvm::Expected<AstHandle> select(llvm::StringRef path) {
    if (path == file)
      return ast;
    std::error_code error;
    auto full = std::filesystem::absolute(std::filesystem::path(path.str()), error);
    if (error)
      return llvm::errorCodeToError(error);
    auto key = full.lexically_normal().string();
    if (key == file)
      return ast;
    if (auto it = files.find(key); it != files.end())
      return it->second;
    TargetRequest request;
    request.file = key;
    auto unit = load(request);
    if (!unit)
      return unit.takeError();
    auto result = own(std::move(*unit));
    if (files.size() == 128)
      files.clear();
    files.try_emplace(key, result);
    return result;
  }
};

struct IrContext {
  explicit IrContext(Targets& targets, Bindings& bindings, MatcherCache& matchers)
      : ast(*targets.ast)
      , targets(targets)
      , values(this, bindings, output, error)
      , matchers(matchers) {}

  clang::ASTContext& ast;
  Targets& targets;
  std::vector<const FunctionDecl*> rows;
  llvm::ArrayRef<const FunctionDecl*> active_rows;
  std::size_t next = 0;
  std::string error;
  std::string output;
  Values values;
  MatcherCache& matchers;
};

using IrEntry = int (*)(IrContext*);
constexpr auto ir_entry_symbol = "ctk_jit_run_ir_v1";

struct CommandCode {
  explicit CommandCode(llvm::orc::ResourceTrackerSP tracker)
      : tracker(std::move(tracker)) {}

  ~CommandCode() {
    if (auto error = tracker->remove())
      llvm::logAllUnhandledErrors(std::move(error), llvm::errs());
  }

  llvm::orc::ResourceTrackerSP tracker;
};

struct CompiledCommand {
  IrEntry entry;
  std::shared_ptr<CommandCode> code;
};

dynamic::VariantMatcher construct_matcher(const MatcherArg& arg,
                                          dynamic::Diagnostics& diagnostics) {
  auto ctor = dynamic::Registry::lookupMatcherCtor(arg.name);
  if (!ctor) {
    diagnostics.addError({}, dynamic::Diagnostics::ET_RegistryMatcherNotFound) << arg.name;
    return {};
  }
  std::vector<dynamic::ParserValue> args;
  args.reserve(arg.count);
  for (std::uint32_t index = 0; index < arg.count; ++index) {
    const auto& child = arg.children[index];
    auto& value = args.emplace_back().Value;
    if (child.literal) {
      value.setString(child.literal);
    } else {
      auto matcher = construct_matcher(child, diagnostics);
      if (matcher.isNull()) {
        return {};
      }
      value.setMatcher(matcher);
    }
  }
  return dynamic::Registry::constructMatcher(*ctor, {}, args, &diagnostics);
}

extern "C" int ctk_jit_match_v1(IrContext* context, const MatcherArg* root, const char* binding) {
  dynamic::Diagnostics diagnostics;
  auto matcher = construct_matcher(*root, diagnostics).getSingleMatcher();
  // Bind explicitly so an empty binding ID has the same behavior as .bind("").
  auto bound = matcher ? matcher->tryBind(binding) : std::nullopt;
  if (!bound) {
    context->error = diagnostics.errors().empty() ? "could not bind the IR query's matcher"
                                                  : diagnostics.toString();
    return 1;
  }

  struct CollectRows final : MatchFinder::MatchCallback {
    CollectRows(llvm::StringRef binding, std::vector<const FunctionDecl*>& rows)
        : binding(binding)
        , rows(rows) {}

    void run(const MatchFinder::MatchResult& result) override {
      if (const auto* decl = result.Nodes.getNodeAs<FunctionDecl>(binding)) {
        rows.push_back(decl);
      }
    }

    llvm::StringRef binding;
    std::vector<const FunctionDecl*>& rows;
  };

  CollectRows collect(binding, context->rows);
  MatchFinder finder;
  if (!finder.addDynamicMatcher(*bound, &collect)) {
    context->error = "could not register the IR query's matcher";
    return 1;
  }
  finder.matchAST(context->ast);
  context->active_rows = context->rows;
  return 0;
}

extern "C" const FunctionDecl* ctk_jit_next_row_v1(IrContext* context) {
  return context->next == context->active_rows.size() ? nullptr
                                                      : context->active_rows[context->next++];
}

extern "C" void ctk_jit_print_decl_name_v1(const FunctionDecl* decl) {
  llvm::outs() << decl->getNameAsString() << '\n';
}

extern "C" void ctk_jit_print_qualified_name_v1(const FunctionDecl* decl) {
  llvm::outs() << decl->getQualifiedNameAsString() << '\n';
}

extern "C" Values* ctk_jit_value_context_v1(IrContext* context) { return &context->values; }

extern "C" const Value* ctk_jit_parse_v1(IrContext* context, const Value* file) {
  const auto* path = std::get_if<std::string>(&file->data);
  if (!path || path->empty())
    return context->values.fail("parse requires a file path");
  auto ast = context->targets.select(*path);
  if (!ast)
    return context->values.fail(llvm::toString(ast.takeError()));
  return context->values.hold({*ast});
}

extern "C" const Value* ctk_jit_parse_cpp_v1(IrContext* context, const Value* code,
                                             const Value* options) {
  auto& runtime = context->values;
  TargetRequest request;
  bool translation_unit = false;
  std::string source;
  if (options) {
    if (const auto* path = std::get_if<std::string>(&options->data)) {
      request.file = *path;
    } else if (const auto* record = std::get_if<std::shared_ptr<Record>>(&options->data)) {
      for (const auto& [key, option] : (*record)->fields) {
        if (key == "file" || key == "working_directory" || key == "compilation_database") {
          const auto* value = std::get_if<std::string>(&option.data);
          if (!value)
            return runtime.fail(llvm::Twine(key) + " must be a string");
          if (key == "file")
            request.file = *value;
          else if (key == "working_directory")
            request.directory = *value;
          else
            request.compilation_database = *value;
        } else if (key == "translation_unit") {
          const auto* value = std::get_if<bool>(&option.data);
          if (!value)
            return runtime.fail("translation_unit must be a bool");
          translation_unit = *value;
        } else if (key == "compile_arguments" || key == "includes") {
          const auto* list = std::get_if<std::shared_ptr<Sequence>>(&option.data);
          if (!list || (*list)->tuple)
            return runtime.fail(llvm::Twine(key) + " requires a list");
          for (const auto& item : (*list)->items) {
            const auto* value = std::get_if<std::string>(&item.data);
            if (!value)
              return runtime.fail(llvm::Twine(key) + " requires a list of strings");
            if (key == "compile_arguments") {
              request.arguments.push_back(*value);
            } else {
              const llvm::StringRef header(*value);
              if (header.empty() || header.contains('\n') || header.contains('\r') ||
                  header.contains('\0')) {
                return runtime.fail("invalid snippet include");
              }
              source += "#include ";
              if ((header.starts_with("<") && header.ends_with(">")) ||
                  (header.starts_with("\"") && header.ends_with("\""))) {
                source += *value;
              } else {
                source += "\"" + *value + "\"";
              }
              source += '\n';
            }
          }
        } else {
          return runtime.fail(llvm::Twine("unknown parse cpp option: ") + key);
        }
      }
    } else {
      return runtime.fail("parse cpp using requires a file path or options record");
    }
  }
  if (!translation_unit)
    source += "inline void ctk_snippet() {\n";
  source += "#line 1\n" + std::get<std::string>(code->data) + '\n';
  if (!translation_unit)
    source += "}\n";
  request.source = std::move(source);
  auto unit = context->targets.load(request);
  if (!unit)
    return runtime.fail(llvm::toString(unit.takeError()));
  return runtime.hold({Targets::own(std::move(*unit))});
}

extern "C" const Value* ctk_jit_match_value_v1(IrContext* context, const Value* expression,
                                               const Value* target) {
  auto& runtime = context->values;
  const auto* value = std::get_if<MatcherValue>(&expression->data);
  if (!value)
    return runtime.fail("match requires a matcher expression");
  auto ast = context->targets.ast;
  if (target) {
    if (const auto* selected = std::get_if<AstHandle>(&target->data)) {
      ast = *selected;
    } else if (const auto* path = std::get_if<std::string>(&target->data)) {
      auto loaded = context->targets.select(*path);
      if (!loaded)
        return runtime.fail(llvm::toString(loaded.takeError()));
      ast = *loaded;
    } else {
      return runtime.fail("match requires a target AST or file path");
    }
  }

  auto compiled = context->matchers.find(value->text);
  if (compiled == context->matchers.end()) {
    llvm::StringRef source(value->text);
    dynamic::Diagnostics diagnostics;
    auto matcher = dynamic::Parser::parseMatcherExpression(source, &diagnostics);
    if (!matcher) {
      return runtime.fail(diagnostics.errors().empty() ? "Clang rejected the matcher"
                                                       : diagnostics.toString());
    }
    if (auto root = matcher->tryBind("root"))
      matcher = std::move(root);
    if (context->matchers.size() == 128)
      context->matchers.clear();
    compiled = context->matchers.try_emplace(value->text, std::move(*matcher)).first;
  }

  struct CollectRows final : MatchFinder::MatchCallback {
    explicit CollectRows(AstHandle ast)
        : ast(std::move(ast)) {}

    void run(const MatchFinder::MatchResult& result) override {
      if (rows->items.size() == 10000) {
        overflow = true;
        return;
      }
      auto row = std::make_shared<Record>();
      for (const auto& [name, node] : result.Nodes.getMap()) {
        row->set(name, {std::make_shared<NativeNode>(
                           NativeNode{ast, std::make_shared<clang::DynTypedNode>(node)})});
      }
      rows->items.push_back({std::move(row)});
    }

    AstHandle ast;
    std::shared_ptr<Sequence> rows = std::make_shared<Sequence>();
    bool overflow = false;
  };

  CollectRows collect(ast);
  MatchFinder finder;
  if (!finder.addDynamicMatcher(compiled->second, &collect)) {
    return runtime.fail("could not register the matcher");
  }
  finder.matchAST(*ast);
  if (collect.overflow)
    return runtime.fail("match exceeds item limit");
  return runtime.hold({std::move(collect.rows)});
}

llvm::Error failure(const llvm::Twine& message) {
  return llvm::createStringError(llvm::inconvertibleErrorCode(), message);
}

llvm::Expected<std::unique_ptr<llvm::Module>> parse_ir(llvm::StringRef source,
                                                       llvm::LLVMContext& context,
                                                       const llvm::Triple& triple,
                                                       const llvm::DataLayout& layout) {
  llvm::SMDiagnostic diagnostic;
  auto module = llvm::parseAssemblyString(source, diagnostic, context);
  if (!module) {
    diagnostic.print("ctk-jit", llvm::errs());
    return failure("could not parse generated LLVM IR");
  }
  module->setDataLayout(layout);
  module->setTargetTriple(triple);
  if (llvm::verifyModule(*module, &llvm::errs())) {
    return failure("generated LLVM IR failed verification");
  }
  return module;
}

llvm::Expected<std::unique_ptr<llvm::orc::LLJIT>> create_ir_jit() {
  auto jit = llvm::orc::LLJITBuilder().create();
  if (!jit) {
    return jit.takeError();
  }

  llvm::orc::SymbolMap symbols;
  auto expose = [&](llvm::StringRef name, auto* function) {
    symbols[(*jit)->mangleAndIntern(name)] = {llvm::orc::ExecutorAddr::fromPtr(function),
                                              llvm::JITSymbolFlags::Exported |
                                                  llvm::JITSymbolFlags::Callable};
  };
  expose("ctk_jit_match_v1", &ctk_jit_match_v1);
  expose("ctk_jit_next_row_v1", &ctk_jit_next_row_v1);
  expose("ctk_jit_print_decl_name_v1", &ctk_jit_print_decl_name_v1);
  expose("ctk_jit_print_qualified_name_v1", &ctk_jit_print_qualified_name_v1);
  expose("ctk_jit_value_context_v1", &ctk_jit_value_context_v1);
  expose("ctk_jit_parse_v1", &ctk_jit_parse_v1);
  expose("ctk_jit_parse_cpp_v1", &ctk_jit_parse_cpp_v1);
  expose("ctk_jit_match_value_v1", &ctk_jit_match_value_v1);
  if (auto error = expose_values(**jit)) {
    return std::move(error);
  }
  auto& dylib = (*jit)->getMainJITDylib();
  if (auto error = dylib.define(llvm::orc::absoluteSymbols(std::move(symbols)))) {
    return error;
  }
  return std::move(*jit);
}

llvm::Error add_ir(llvm::orc::LLJIT& jit, llvm::StringRef source,
                   llvm::orc::ResourceTrackerSP tracker, llvm::StringRef entry_name = {}) {
  auto context = std::make_unique<llvm::LLVMContext>();
  auto module = parse_ir(source, *context, jit.getTargetTriple(), jit.getDataLayout());
  if (!module) {
    return module.takeError();
  }
  if (!entry_name.empty()) {
    auto* entry = (*module)->getFunction(ir_entry_symbol);
    if (!entry || entry->isDeclaration()) {
      return failure("generated LLVM IR has no entry point");
    }
    entry->setName(entry_name);
  }
  return jit.addIRModule(std::move(tracker), {std::move(*module), std::move(context)});
}

llvm::Expected<IrEntry> lookup_ir_entry(llvm::orc::LLJIT& jit, llvm::StringRef name) {
  auto entry = jit.lookup(name);
  if (!entry) {
    return entry.takeError();
  }
  return entry->toPtr<IrEntry>();
}

llvm::Error call_ir_entry(IrEntry entry, IrContext& runtime) {
  if (entry(&runtime) != 0) {
    return failure(llvm::Twine("LLVM IR query: ") + runtime.error);
  }
  return llvm::Error::success();
}

} // namespace

llvm::Error compile_ir(llvm::StringRef source) {
  // Keep the object compatible with the runner's generic process target.
  llvm::orc::JITTargetMachineBuilder target{llvm::Triple(llvm::sys::getProcessTriple())};
  target.setRelocationModel(llvm::Reloc::PIC_);
  auto machine = target.createTargetMachine();
  if (!machine) {
    return machine.takeError();
  }

  llvm::LLVMContext context;
  auto module =
      parse_ir(source, context, (*machine)->getTargetTriple(), (*machine)->createDataLayout());
  if (!module) {
    return module.takeError();
  }
  auto object = llvm::orc::SimpleCompiler(**machine)(**module);
  if (!object) {
    return object.takeError();
  }
  llvm::outs() << (*object)->getBuffer();
  return llvm::Error::success();
}

llvm::Error run_ir(std::unique_ptr<llvm::MemoryBuffer> input, clang::ASTContext& ast,
                   bool precompiled, llvm::StringRef file, const LoadTarget& load) {
  auto jit = create_ir_jit();
  if (!jit) {
    return jit.takeError();
  }
  auto loaded = precompiled ? (*jit)->addObjectFile(std::move(input))
                            : add_ir(**jit, input->getBuffer(),
                                     (*jit)->getMainJITDylib().getDefaultResourceTracker());
  if (loaded) {
    return loaded;
  }
  auto entry = lookup_ir_entry(**jit, ir_entry_symbol);
  if (!entry) {
    return entry.takeError();
  }
  Targets targets(ast, file, load);
  auto bindings = targets.bindings();
  MatcherCache matchers;
  IrContext runtime(targets, bindings, matchers);
  auto result = call_ir_entry(*entry, runtime);
  llvm::outs() << runtime.output;
  return result;
}

llvm::Error repl_ir(clang::ASTContext& ast, llvm::StringRef file, const LoadTarget& load) {
  auto jit = create_ir_jit();
  if (!jit) {
    return jit.takeError();
  }
  Targets targets(ast, file, load);
  auto bindings = targets.bindings();
  MatcherCache matchers;
  llvm::DenseMap<std::int64_t, CompiledCommand> commands;
  std::uint64_t entry_number = 0;
  llvm::outs() << "{\"ready\":true,\"protocol\":3}\n";
  llvm::outs().flush();

  // Requests identify a cache slot and supply LLVM IR only on a miss.
  std::string line;
  while (std::getline(std::cin, line)) {
    auto request = llvm::json::parse(line);
    if (!request) {
      return request.takeError();
    }
    const auto* command = request->getAsObject();
    const auto slot = command ? command->getInteger("slot") : std::nullopt;
    if (!slot || *slot < 0) {
      return failure("expected a REPL command slot");
    }

    auto cached = commands.find(*slot);
    bool compiled = false;
    llvm::Error result = llvm::Error::success();
    if (auto source = command->getString("ir")) {
      // The previous entry remains usable until the replacement links.
      const auto name = "ctk_jit_repl_entry_" + std::to_string(entry_number++);
      auto tracker = (*jit)->getMainJITDylib().createResourceTracker();
      result = add_ir(**jit, *source, tracker, name);
      if (!result) {
        auto entry = lookup_ir_entry(**jit, name);
        if (!entry) {
          result = entry.takeError();
        } else {
          auto code = std::make_shared<CommandCode>(tracker);
          cached = commands.insert_or_assign(*slot, CompiledCommand{*entry, std::move(code)}).first;
          compiled = true;
        }
      }
      if (!compiled) {
        if (auto cleanup = tracker->remove()) {
          return llvm::joinErrors(std::move(result), std::move(cleanup));
        }
      }
    }

    // A cached entry runs against the session's current bindings on every call.
    IrContext runtime(targets, bindings, matchers);
    if (!result) {
      if (cached == commands.end()) {
        return failure("unknown REPL command slot");
      }
      runtime.values.code = cached->second.code;
      result = call_ir_entry(cached->second.entry, runtime);
    }
    llvm::outs() << llvm::json::Value(llvm::json::Object{
                        {"compiled", compiled},
                        {"output", std::move(runtime.output)},
                        {"error", llvm::toString(std::move(result))},
                    })
                 << '\n';
    llvm::outs().flush();
  }
  return llvm::Error::success();
}

} // namespace ctk::jit
