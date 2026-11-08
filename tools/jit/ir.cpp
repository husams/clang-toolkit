#include "ir.hpp"
#include "analysis.hpp"
#include "local_operations.hpp"
#include "semantic.hpp"
#include "documents.hpp"
#include "matcher_parser.hpp"
#include "platform/compiler_channel.hpp"
#include "scoped_match.hpp"
#include "value_access.hpp"
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
#include <llvm/ADT/SmallPtrSet.h>
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
  Targets(std::unique_ptr<clang::ASTUnit> ast, llvm::StringRef file, llvm::StringRef database,
          const LoadTarget& load)
      : ast(retain_ast(std::move(ast), 1))
      , file(file)
      , load(load)
      , local(database) {}

  AstHandle ast;
  llvm::StringRef file;
  const LoadTarget& load;
  llvm::StringMap<AstHandle> files;
  LocalState state;
  LocalOperations local;

  std::uint64_t next_generation = 2;

  AstHandle own(std::unique_ptr<clang::ASTUnit> unit) {
    return retain_ast(std::move(unit), next_generation++);
  }

  Bindings bindings(const ScriptArguments& arguments) const {
    auto args = std::make_shared<Record>();
    for (const auto& [key, value] : arguments)
      args->set(key, {value});
    if (!file.empty() && !args->fields.contains("file"))
      args->set("file", {file.str()});
    Bindings bindings;
    bindings.try_emplace("arg", Value{std::move(args)});
    return bindings;
  }

  llvm::Expected<AstHandle> select(llvm::StringRef path) {
    if (ast && path == file)
      return ast;
    std::error_code error;
    auto full = std::filesystem::absolute(std::filesystem::path(path.str()), error);
    if (error)
      return llvm::errorCodeToError(error);
    auto key = full.lexically_normal().string();
    if (ast && key == file)
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

class RuntimeCompiler;

struct IrContext {
  explicit IrContext(Targets& targets, Bindings& bindings, MatcherCache& matchers,
                     RuntimeCompiler& compiler)
      : targets(targets)
      , values(this, bindings, targets.state, output, error)
      , matchers(matchers)
      , compiler(compiler) {}

  Targets& targets;
  std::vector<const FunctionDecl*> rows;
  llvm::ArrayRef<const FunctionDecl*> active_rows;
  std::size_t next = 0;
  std::string error;
  std::string output;
  Values values;
  MatcherCache& matchers;
  RuntimeCompiler& compiler;
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
  if (!context->targets.ast) {
    context->error = "match requires a target file";
    return 1;
  }
  finder.matchAST(*context->targets.ast);
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
  return runtime.hold({context->targets.own(std::move(*unit))});
}

struct MatchTarget {
  AstHandle ast;
  std::shared_ptr<clang::DynTypedNode> root;
  std::shared_ptr<clang::DynTypedNode> parent;
};

bool append_target(IrContext& context, std::vector<MatchTarget>& targets, const Value& value) {
  using namespace value_access;
  if (const auto* ast = as<AstHandle>(value)) {
    targets.push_back({*ast, {}});
  } else if (const auto* path = as<std::string>(value)) {
    auto loaded = context.targets.select(*path);
    if (!loaded) {
      context.values.fail(llvm::toString(loaded.takeError()));
      return false;
    }
    targets.push_back({*loaded, {}});
  } else if (const auto* selected = retained_node(value)) {
    targets.push_back({selected->ast, selected->node, selected->parent});
  } else if (context.targets.local.is_target(value)) {
    auto loaded = context.targets.local.target(value);
    if (!loaded) {
      context.values.fail(llvm::toString(loaded.takeError()));
      return false;
    }
    targets.push_back({*loaded, {}});
  } else if (const auto* row = object<Record>(value)) {
    auto root = row->fields.find("root");
    if (root != row->fields.end() && object<NativeNode>(root->second)) {
      return append_target(context, targets, root->second);
    }
    context.values.fail("match row has no root binding");
    return false;
  } else {
    context.values.fail("match requires a target AST, file path, or retained node");
    return false;
  }
  return true;
}

extern "C" const Value* ctk_jit_match_value_v2(IrContext* context, const Value* expression,
                                               const Value* target, const char* scope) {
  auto& runtime = context->values;
  const auto* value = std::get_if<MatcherValue>(&expression->data);
  if (!value)
    return runtime.fail("match requires a matcher expression");
  const llvm::StringRef scope_name(scope);
  const bool self = scope_name == "self" || scope_name == "root_only";
  const bool children = scope_name == "children";
  if (!self && !children && scope_name != "subtree") {
    return runtime.fail("match scope requires children, self, root_only or subtree");
  }

  std::vector<MatchTarget> targets;
  if (!target) {
    if (!context->targets.ast)
      return runtime.fail("match requires a target");
    targets.push_back({context->targets.ast, {}});
  } else {
    const auto manifest = semantic_length(*target) ? semantic_iteration(*target) : std::nullopt;
    const auto* items = value_access::object<Sequence>(manifest ? *manifest : *target);
    if (items) {
      for (const auto& item : items->items)
        if (!append_target(*context, targets, item))
          return nullptr;
    } else if (!append_target(*context, targets, *target)) {
      return nullptr;
    }
  }

  if (children) {
    std::vector<Value> rows;
    for (const auto& selected : targets) {
      if (!selected.root) return runtime.fail("children scope requires a retained node");
      NativeNode node{selected.ast, selected.root, {}, selected.parent};
      const auto* result = navigate(runtime, node, value, "children", 0, {}, false, false, false);
      if (!result) return nullptr;
      const auto& items = value_access::object<Sequence>(*result)->items;
      if (items.size() > value_access::max_items - rows.size())
        return runtime.fail("match exceeds item limit");
      rows.insert(rows.end(), items.begin(), items.end());
    }
    return runtime.hold(value_access::list(std::move(rows)));
  }

  auto compiled = context->matchers.find(value->text);
  if (compiled == context->matchers.end()) {
    llvm::StringRef source(value->text);
    dynamic::Diagnostics diagnostics;
    auto matcher = clang_layer::parse_matcher_expression(source, diagnostics);
    if (!matcher)
      return runtime.fail(diagnostics.toString());
    if (auto root = matcher->tryBind("root"))
      matcher = std::move(root);
    if (context->matchers.size() == 128)
      context->matchers.clear();
    compiled = context->matchers.try_emplace(value->text, std::move(*matcher)).first;
  }

  struct CollectRows final : MatchFinder::MatchCallback {
    void run(const MatchFinder::MatchResult& result) override {
      if (rows->items.size() == value_access::max_items) {
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

  CollectRows collect;
  MatchFinder finder;
  const auto& query = compiled->second;
  if (!finder.addDynamicMatcher(query, &collect)) {
    return runtime.fail("could not register the matcher");
  }
  for (const auto& selected : targets) {
    collect.ast = selected.ast;
    if (!selected.root) {
      finder.matchAST(*selected.ast);
    } else if (self) {
      finder.match(*selected.root, *selected.ast);
    } else {
      if (!(selected.root->get<clang::Decl>() || selected.root->get<clang::Stmt>()) ||
          !(query.canConvertTo<clang::Decl>() || query.canConvertTo<clang::Stmt>())) {
        return runtime.fail("subtree requires a Decl/Stmt root and matcher");
      }
      if (clang_layer::requires_translation_unit_match_metadata(value->text)) {
        MatchFinder descendants;
        descendants.addDynamicMatcher(clang_layer::scoped_matcher(*selected.root, query), &collect);
        descendants.matchAST(*selected.ast);
      } else {
        clang_layer::match_subtree(*selected.root, finder, *selected.ast,
                                   [&] { return !collect.overflow && runtime.tick(); });
      }
    }
    if (collect.overflow)
      return runtime.fail("match exceeds item limit");
    if (runtime.fatal)
      return nullptr;
  }
  return runtime.hold({std::move(collect.rows)});
}

extern "C" const Value* ctk_jit_local_operation_v1(
    IrContext* context, const char* command, const Value* arguments, const char* options,
    std::int32_t display) {
  return context->targets.local.execute(context->values, command,
      *value_access::object<Sequence>(*arguments), options, display);
}

extern "C" const Value* ctk_jit_analyze_v1(IrContext* context, const char* operation,
                                              const Value* target, const Value* operand,
                                              const char* options, std::int32_t display) {
  if (!target) {
    if (!context->targets.ast) return context->values.fail("analysis requires a target");
    return analyze(context->values, operation, context->targets.ast, nullptr, operand,
                   options, display);
  }
  if (const auto* selected = retained_node(*target)) {
    return analyze(context->values, operation, selected->ast, selected, operand,
                   options, display);
  }
  if (const auto* ast = value_access::as<AstHandle>(*target)) {
    return analyze(context->values, operation, *ast, nullptr, operand, options, display);
  }
  if (const auto* path = value_access::as<std::string>(*target)) {
    auto ast = context->targets.select(*path);
    if (!ast) return context->values.fail(llvm::toString(ast.takeError()));
    return analyze(context->values, operation, *ast, nullptr, operand, options, display);
  }
  if (context->targets.local.is_target(*target)) {
    auto ast = context->targets.local.target(*target);
    if (!ast) return context->values.fail(llvm::toString(ast.takeError()));
    return analyze(context->values, operation, *ast, nullptr, operand, options, display);
  }
  return context->values.fail("analysis requires a file path, parsed tree or retained node");
}

extern "C" const Value* ctk_jit_navigate_v1(IrContext* context, const Value* target,
                                               const Value* matcher, const char* axis,
                                               std::uint64_t maximum, std::uint64_t index,
                                               std::int32_t has_index, std::int32_t step,
                                               std::int32_t display) {
  const auto* node = retained_node(*target);
  if (!node) return context->values.fail("navigation requires a retained native binding");
  const auto* query = matcher ? value_access::as<MatcherValue>(*matcher) : nullptr;
  if (matcher && !query) return context->values.fail("navigation requires a matcher expression");
  return navigate(context->values, *node, query, axis, maximum,
                  has_index ? std::optional{index} : std::nullopt, step, display);
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

extern "C" const Value* ctk_jit_import_v1(IrContext* context, const Value* path);
extern "C" const Value* ctk_jit_eval_v1(IrContext* context, const Value* arguments,
                                        const Value* keywords);

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
  expose("ctk_jit_match_value_v2", &ctk_jit_match_value_v2);
  expose("ctk_jit_local_operation_v1", &ctk_jit_local_operation_v1);
  expose("ctk_jit_analyze_v1", &ctk_jit_analyze_v1);
  expose("ctk_jit_navigate_v1", &ctk_jit_navigate_v1);
  expose("ctk_jit_import_v1", &ctk_jit_import_v1);
  expose("ctk_jit_eval_v1", &ctk_jit_eval_v1);
  if (auto error = expose_values(**jit)) {
    return std::move(error);
  }
  if (auto error = expose_documents(**jit)) {
    return error;
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

class RuntimeCompiler {
public:
  explicit RuntimeCompiler(llvm::orc::LLJIT& jit)
      : jit(jit) {}

  llvm::Expected<CompiledCommand> compile(llvm::StringRef source, llvm::StringRef path,
                                          bool library) {
    // Library contents are checked on every import. Existing function
    // bindings keep their previous machine code alive across library edits.
    const auto key = library ? path.str() : source.str();
    auto& cache = library ? libraries : expressions;
    const auto cached = cache.find(key);
    if (cached != cache.end() && cached->second.source == source)
      return cached->second.command;

    auto lowered = channel.lower(source, path, library);
    if (!lowered)
      return lowered.takeError();
    const auto symbol = "ctk_jit_runtime_entry_" + std::to_string(next++);
    auto tracker = jit.getMainJITDylib().createResourceTracker();
    auto code = std::make_shared<CommandCode>(tracker);
    if (auto error = add_ir(jit, *lowered, tracker, symbol))
      return error;
    auto entry = lookup_ir_entry(jit, symbol);
    if (!entry)
      return entry.takeError();
    CompiledCommand command{*entry, std::move(code)};
    if (cache.size() == 64)
      cache.clear();
    cache.insert_or_assign(key, Cached{source.str(), command});
    return command;
  }

  std::vector<std::string> import_stack;

private:
  struct Cached {
    std::string source;
    CompiledCommand command;
  };

  llvm::orc::LLJIT& jit;
  CompilerChannel channel;
  llvm::StringMap<Cached> libraries;
  llvm::StringMap<Cached> expressions;
  std::uint64_t next = 0;
};

class LibrarySnapshot {
public:
  explicit LibrarySnapshot(Bindings& bindings)
      : bindings(bindings)
      , previous(bindings) {
    using namespace value_access;
    std::vector<Value> work;
    for (const auto& [name, value] : bindings)
      work.push_back(value);
    llvm::SmallPtrSet<const void*, 16> visited;
    while (!work.empty()) {
      auto value = std::move(work.back());
      work.pop_back();
      if (const auto* sequence = as<std::shared_ptr<Sequence>>(value)) {
        if (!visited.insert(sequence->get()).second)
          continue;
        work.insert(work.end(), (*sequence)->items.begin(), (*sequence)->items.end());
        sequences.emplace_back(*sequence, **sequence);
      } else if (const auto* record = as<std::shared_ptr<Record>>(value)) {
        if (!visited.insert(record->get()).second)
          continue;
        for (const auto& [name, item] : (*record)->fields)
          work.push_back(item);
        records.emplace_back(*record, **record);
      } else if (const auto* runnable = object<Runnable>(value)) {
        if (!visited.insert(runnable).second)
          continue;
        for (const auto& scope : runnable->captured)
          for (const auto& [name, item] : scope.bindings)
            work.push_back(item);
      }
    }
  }

  void restore() {
    for (auto& [target, saved] : sequences)
      *target = std::move(saved);
    for (auto& [target, saved] : records)
      *target = std::move(saved);
    bindings = std::move(previous);
  }

private:
  Bindings& bindings;
  Bindings previous;
  std::vector<std::pair<std::shared_ptr<Sequence>, Sequence>> sequences;
  std::vector<std::pair<std::shared_ptr<Record>, Record>> records;
};

const Value* execute_compiled(IrContext& context, const CompiledCommand& command) {
  auto& runtime = context.values;
  auto code = std::exchange(runtime.code, command.code);
  auto saved_path = runtime.source_path;
  const auto* previous_result = std::exchange(runtime.result, nullptr);
  const auto status = command.entry(&context);
  const auto* result = std::exchange(runtime.result, previous_result);
  runtime.code = std::move(code);
  runtime.source_path = std::move(saved_path);
  return status ? nullptr : result ? result : runtime.hold({});
}

extern "C" const Value* ctk_jit_import_v1(IrContext* context, const Value* path) {
  auto& runtime = context->values;
  const auto* filename = value_access::as<std::string>(*path);
  if (!filename || filename->empty() || filename->find('\0') != std::string::npos)
    return runtime.fail("import requires a nonempty file path");
  namespace fs = std::filesystem;
  const auto source = fs::path(runtime.source_path);
  const auto selected = source.empty() ? fs::path(*filename) : source.parent_path() / *filename;
  std::error_code error;
  const auto file = fs::canonical(selected, error).string();
  if (error)
    return runtime.fail(llvm::Twine("cannot read library ") + selected.string() + ": " +
                        error.message());

  auto& stack = context->compiler.import_stack;
  if (file == runtime.source_path || llvm::is_contained(stack, file))
    return runtime.fail(llvm::Twine("import cycle: ") + file);
  if (stack.size() >= 64)
    return runtime.fail("library import depth exceeds 64");

  auto contents = llvm::MemoryBuffer::getFile(file);
  if (!contents)
    return runtime.fail(llvm::Twine("cannot read library ") + file + ": " +
                        contents.getError().message());
  const auto text = (*contents)->getBuffer();
  if (text.size() > 1024 * 1024)
    return runtime.fail("library exceeds byte limit");
  auto compiled = context->compiler.compile(text, file, true);
  if (!compiled)
    return runtime.fail(llvm::toString(compiled.takeError()));

  LibrarySnapshot snapshot(runtime.globals);
  auto scopes = std::move(runtime.scopes);
  const auto frame = std::exchange(runtime.frame_depth, 0);
  stack.push_back(file);
  const auto* result = execute_compiled(*context, *compiled);
  stack.pop_back();
  runtime.scopes = std::move(scopes);
  runtime.frame_depth = frame;
  if (!result) {
    snapshot.restore();
    return runtime.fail(llvm::Twine(file) + ": " + runtime.error);
  }
  return runtime.hold({});
}

extern "C" const Value* ctk_jit_eval_v1(IrContext* context, const Value* arguments,
                                        const Value* keywords) {
  using namespace value_access;
  auto& runtime = context->values;
  const auto& positional = object<Sequence>(*arguments)->items;
  const auto* source = positional.size() == 1 ? as<std::string>(positional[0]) : nullptr;
  if (!source || !object<Record>(*keywords)->keys.empty())
    return runtime.fail("ctk expects one command string");
  if (source->size() > 1024 * 1024)
    return runtime.fail("CTK command exceeds byte limit");
  if (runtime.call_depth >= 64)
    return runtime.fail("CTK call depth exceeds 64");
  auto command = context->compiler.compile(*source, "", false);
  if (!command)
    return runtime.fail(llvm::toString(command.takeError()));
  const auto previous_frame = std::exchange(runtime.frame_depth, runtime.scopes.size());
  ++runtime.call_depth;
  const auto* result = execute_compiled(*context, *command);
  --runtime.call_depth;
  runtime.scopes.resize(runtime.frame_depth);
  runtime.frame_depth = previous_frame;
  return result;
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

llvm::Error run_ir(std::unique_ptr<llvm::MemoryBuffer> input, std::unique_ptr<clang::ASTUnit> ast,
                   bool precompiled, llvm::StringRef file, llvm::StringRef database,
                   const LoadTarget& load, const ScriptArguments& arguments) {
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
  RuntimeCompiler compiler(**jit);
  Targets targets(std::move(ast), file, database, load);
  auto bindings = targets.bindings(arguments);
  MatcherCache matchers;
  IrContext runtime(targets, bindings, matchers, compiler);
  auto result = call_ir_entry(*entry, runtime);
  llvm::outs() << runtime.output;
  return result;
}

llvm::Error repl_ir(std::unique_ptr<clang::ASTUnit> ast, llvm::StringRef file, llvm::StringRef database,
                    const LoadTarget& load, const ScriptArguments& arguments) {
  auto jit = create_ir_jit();
  if (!jit) {
    return jit.takeError();
  }
  RuntimeCompiler compiler(**jit);
  Targets targets(std::move(ast), file, database, load);
  auto bindings = targets.bindings(arguments);
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
    IrContext runtime(targets, bindings, matchers, compiler);
    if (!result) {
      if (cached == commands.end()) {
        return failure("unknown REPL command slot");
      }
      runtime.values.code = cached->second.code;
      result = call_ir_entry(cached->second.entry, runtime);
    }
    llvm::outs() << llvm::json::Value(llvm::json::Object{
                        {"compiled", compiled},
                        {"exit", runtime.values.exit_requested},
                        {"output", std::move(runtime.output)},
                        {"error", llvm::toString(std::move(result))},
                    })
                 << '\n';
    llvm::outs().flush();
  }
  return llvm::Error::success();
}

} // namespace ctk::jit
