#include "ir.hpp"

#include <cstdint>
#include <iostream>
#include <memory>
#include <string>
#include <variant>
#include <vector>

#include <clang/ASTMatchers/ASTMatchFinder.h>
#include <clang/ASTMatchers/Dynamic/Registry.h>
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

// Layout of the generated LLVM IR's %arg on the runner's target.
struct MatcherArg {
  const char* name;
  const char* literal;
  const MatcherArg* children;
  std::uint32_t count;
};

struct MatchedRows {
  std::string binding;
  std::vector<const FunctionDecl*> declarations;
};

using Bindings = llvm::StringMap<std::variant<clang::ASTContext*, MatchedRows>>;

struct IrContext {
  explicit IrContext(clang::ASTContext& ast, Bindings* bindings = nullptr)
      : ast(ast)
      , bindings(bindings) {}

  clang::ASTContext& ast;
  Bindings* bindings;
  std::vector<const FunctionDecl*> rows;
  llvm::ArrayRef<const FunctionDecl*> active_rows;
  std::size_t next = 0;
  std::string error;
  std::string output;
};

using IrEntry = int (*)(IrContext*);
constexpr auto ir_entry_symbol = "ctk_jit_run_ir_v1";

struct CompiledCommand {
  IrEntry entry;
  llvm::orc::ResourceTrackerSP tracker;
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

extern "C" int ctk_jit_repl_bind_target_v1(IrContext* context, const char* name) {
  context->bindings->insert_or_assign(name, &context->ast);
  return 0;
}

extern "C" int ctk_jit_repl_match_v1(IrContext* context, const MatcherArg* root,
                                     const char* binding, const char* target, const char* name) {
  const auto entry = context->bindings->find(target);
  if (entry == context->bindings->end() ||
      !std::holds_alternative<clang::ASTContext*>(entry->second)) {
    context->error = (llvm::Twine("expected a target binding named '") + target + "'").str();
    return 1;
  }
  if (const auto status = ctk_jit_match_v1(context, root, binding)) {
    return status;
  }
  context->active_rows = {};
  context->bindings->insert_or_assign(name, MatchedRows{binding, std::move(context->rows)});
  return 0;
}

extern "C" int ctk_jit_repl_select_rows_v1(IrContext* context, const char* name,
                                           const char* binding) {
  const auto entry = context->bindings->find(name);
  const auto* rows =
      entry == context->bindings->end() ? nullptr : std::get_if<MatchedRows>(&entry->second);
  if (!rows) {
    context->error = (llvm::Twine("expected a match binding named '") + name + "'").str();
    return 1;
  }
  if (rows->binding != binding) {
    context->error =
        (llvm::Twine("match binding '") + name + "' has no node named '" + binding + "'").str();
    return 1;
  }
  context->active_rows = rows->declarations;
  return 0;
}

extern "C" void ctk_jit_repl_print_v1(IrContext* context, const FunctionDecl* decl, int qualified) {
  context->output += qualified ? decl->getQualifiedNameAsString() : decl->getNameAsString();
  context->output += '\n';
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

llvm::Expected<std::unique_ptr<llvm::orc::LLJIT>> create_ir_jit(bool repl) {
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
  if (repl) {
    expose("ctk_jit_repl_bind_target_v1", &ctk_jit_repl_bind_target_v1);
    expose("ctk_jit_repl_match_v1", &ctk_jit_repl_match_v1);
    expose("ctk_jit_repl_select_rows_v1", &ctk_jit_repl_select_rows_v1);
    expose("ctk_jit_repl_print_v1", &ctk_jit_repl_print_v1);
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
                   bool precompiled) {
  auto jit = create_ir_jit(false);
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
  IrContext runtime(ast);
  return call_ir_entry(*entry, runtime);
}

llvm::Error repl_ir(clang::ASTContext& ast) {
  auto jit = create_ir_jit(true);
  if (!jit) {
    return jit.takeError();
  }
  Bindings bindings;
  llvm::DenseMap<std::int64_t, CompiledCommand> commands;
  std::uint64_t entry_number = 0;
  llvm::outs() << "{\"ready\":true,\"protocol\":2}\n";
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
          if (cached != commands.end()) {
            if (auto cleanup = cached->second.tracker->remove()) {
              return cleanup;
            }
          }
          cached = commands.insert_or_assign(*slot, CompiledCommand{*entry, tracker}).first;
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
    IrContext runtime(ast, &bindings);
    if (!result) {
      if (cached == commands.end()) {
        return failure("unknown REPL command slot");
      }
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
