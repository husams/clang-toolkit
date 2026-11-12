#include "ir.hpp"
#include "grammar/lower.hpp"
#include "completion.hpp"
#include "native_history.hpp"
#include "file_values.hpp"
#include "filters.hpp"
#include "analysis.hpp"
#include "local_operations.hpp"
#include "semantic.hpp"
#include "settings.hpp"
#include "documents.hpp"
#include "matcher_parser.hpp"
#include "platform/compiler_channel.hpp"
#include "platform/repl_cancellation.hpp"
#include "scoped_match.hpp"
#include "value_access.hpp"
#include "values.hpp"
#include "workspace.hpp"

#include <cstdint>
#include <filesystem>
#include <iostream>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

#include <clang/ASTMatchers/ASTMatchFinder.h>
#include <clang/ASTMatchers/Dynamic/Parser.h>
#include <clang/ASTMatchers/Dynamic/Registry.h>
#include <clang/Frontend/ASTUnit.h>
#include <llvm/ADT/ArrayRef.h>
#include <llvm/ADT/STLFunctionalExtras.h>
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
  Targets(llvm::StringRef file, llvm::StringRef database, const LoadTarget& load)
      : file(file)
      , load(load)
      , state{.default_database = database.str(), .compilation_database = database.str()}
      , local(state)
      , loaded_database(database) {}

  AstHandle ast;
  llvm::StringRef file;
  const LoadTarget& load;
  llvm::StringMap<AstHandle> files;
  LocalState state;
  LocalOperations local;
  std::string loaded_database;
  std::vector<std::string> loaded_arguments;

  std::uint64_t next_generation = 1;

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
    if (local.scoped()) return local.target_path(path);
    if (loaded_database != state.compilation_database || loaded_arguments != state.compilation_arguments) {
      files.clear();
      ast.reset();
      loaded_database = state.compilation_database;
      loaded_arguments = state.compilation_arguments;
    }
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
    request.compilation_database = loaded_database;
    request.arguments = loaded_arguments;
    auto unit = load(request);
    if (!unit)
      return unit.takeError();
    auto result = own(std::move(*unit));
    if (files.size() == 128)
      files.clear();
    files.try_emplace(key, result);
    if (key == file) ast = result;
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
  if (context->targets.state.spelled_only)
    bound = bound->withTraversalKind(clang::TK_IgnoreUnlessSpelledInSource);
  if (!finder.addDynamicMatcher(*bound, &collect)) {
    context->error = "could not register the IR query's matcher";
    return 1;
  }
  if (context->targets.file.empty()) {
    context->error = "match requires a target file";
    return 1;
  }
  auto ast = context->targets.select(context->targets.file);
  if (!ast) {
    context->error = llvm::toString(ast.takeError());
    return 1;
  }
  finder.matchAST(**ast);
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
  const auto* path = file_path(*file);
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
  request.compilation_database = context->targets.state.compilation_database;
  request.arguments = context->targets.state.compilation_arguments;
  bool translation_unit = false;
  std::vector<std::string> includes;
  std::string source;
  if (options) {
    if (const auto* path = file_path(*options)) {
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
              includes.push_back(*value);
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
  if (context->targets.local.scoped()) {
    auto ast = context->targets.local.parse_snippet(
        request, std::get<std::string>(code->data), includes, translation_unit);
    return ast ? runtime.hold({*ast}) : runtime.fail(llvm::toString(ast.takeError()));
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
    if (!context.targets.local.accepts(*ast)) {
      context.values.fail("AST is outside the resource scope manifest");
      return false;
    }
    targets.push_back({*ast, {}});
  } else if (const auto* path = file_path(value)) {
    auto loaded = context.targets.select(*path);
    if (!loaded) {
      context.values.fail(llvm::toString(loaded.takeError()));
      return false;
    }
    targets.push_back({*loaded, {}});
  } else if (object<FileEntry>(value)) {
    context.values.fail("match files cannot include directories or other values");
    return false;
  } else if (const auto* selected = retained_node(value)) {
    if (!context.targets.local.accepts(selected->ast)) {
      context.values.fail("AST is outside the resource scope manifest");
      return false;
    }
    targets.push_back({selected->ast, selected->node, selected->parent});
  } else if (context.targets.local.is_target(value)) {
    auto loaded = context.targets.local.target(value);
    if (!loaded) {
      context.values.fail(llvm::toString(loaded.takeError()));
      return false;
    }
    targets.push_back({*loaded, {}});
  } else if (is_streamed_binding(value)) {
    context.values.fail("streamed bindings are semantic snapshots; native continuation requires a completed match result");
    return false;
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

const Value* match_rows(IrContext* context, const Value* expression, const Value* target,
                        const char* scope, llvm::function_ref<bool(const Sequence&)> consume = {}) {
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
  std::optional<Value> expanded;
  if (target) {
    if (const auto* path = file_path(*target, true)) {
      auto files = match_paths(*path);
      if (!files) return runtime.fail(llvm::toString(files.takeError()));
      if (*files) {
        std::vector<Value> values;
        for (auto& file : **files) values.push_back({std::move(file)});
        expanded = value_access::list(std::move(values));
        target = &*expanded;
      }
    }
  }
  const auto scoped = !target && context->targets.local.scoped()
      ? std::optional(context->targets.local.scoped_inputs()) : std::nullopt;
  if (scoped) target = &*scoped;
  if (!target) {
    const auto* configured = value_access::object<Sequence>(context->targets.state.default_targets);
    if (configured && !configured->items.empty()) target = &context->targets.state.default_targets;
  }
  if (!target) {
    if (context->targets.file.empty()) return runtime.fail("match requires a target");
    auto ast = context->targets.select(context->targets.file);
    if (!ast) return runtime.fail(llvm::toString(ast.takeError()));
    targets.push_back({*ast, {}});

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
    std::size_t count = 0;
    for (const auto& selected : targets) {
      if (!selected.root) return runtime.fail("children scope requires a retained node");
      NativeNode node{selected.ast, selected.root, {}, selected.parent};
      const auto* result = navigate(runtime, node, value, "children", 0, {}, false, false, false);
      if (!result) return nullptr;
      const auto& found = *value_access::object<Sequence>(*result);
      if (found.items.size() > value_access::max_items - count)
        return runtime.fail(consume ? "match do exceeds 10000 rows" : "match exceeds item limit");
      count += found.items.size();
      if (consume) {
        if (!consume(found)) return nullptr;
      } else {
        rows.insert(rows.end(), found.items.begin(), found.items.end());
      }
    }
    auto result = value_access::list(std::move(rows));
    value_access::object<Sequence>(result)->match_snapshot = true;
    return runtime.hold(std::move(result));
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
      if (count == value_access::max_items) {
        overflow = true;
        return;
      }
      ++count;
      auto row = std::make_shared<Record>();
      row->match_row = true;
      row->source_file = source_file;
      for (const auto& [name, node] : result.Nodes.getMap()) {
        row->set(name, {std::make_shared<NativeNode>(
                           NativeNode{ast, std::make_shared<clang::DynTypedNode>(node), {}, {}, name, ordinal})});
      }
      ++ordinal;
      rows->items.push_back({std::move(row)});
    }
    AstHandle ast;
    std::optional<std::string> source_file;
    std::size_t count = 0;
    std::int64_t ordinal = 0;
    std::shared_ptr<Sequence> rows = std::make_shared<Sequence>();
    bool overflow = false;
  };

  CollectRows collect;
  MatchFinder finder;
  const auto query = context->targets.state.spelled_only
      ? compiled->second.withTraversalKind(clang::TK_IgnoreUnlessSpelledInSource)
      : compiled->second;
  if (!finder.addDynamicMatcher(query, &collect)) {
    return runtime.fail("could not register the matcher");
  }
  for (const auto& selected : targets) {
    collect.ast = selected.ast;
    collect.ordinal = 0;
    collect.source_file = native_source_file(selected.ast);
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
      return runtime.fail(consume ? "match do exceeds 10000 rows" : "match exceeds item limit");
    if (runtime.fatal)
      return nullptr;
    // Execute after Clang has finished this traversal. A body may run another
    // matcher against the same retained AST.
    if (consume) {
      if (!consume(*collect.rows)) return nullptr;
      collect.rows->items.clear();
    }
  }
  collect.rows->match_snapshot = true;
  return runtime.hold({std::move(collect.rows)});
}

extern "C" const Value* ctk_jit_match_value_v2(IrContext* context, const Value* expression,
                                               const Value* target, const char* scope) {
  return match_rows(context, expression, target, scope);
}

extern "C" const Value* ctk_jit_match_block_v1(IrContext* context, const Value* expression,
                                               const Value* target, const char* scope,
                                               const Value* body, std::int32_t statement) {
  using namespace value_access;
  auto& runtime = context->values;
  const auto* parent = runtime.match_output;
  MatchOutput capture{{}, statement && runtime.consume_depth == 0 &&
                             (!parent || parent->route_to_file)};
  auto* previous_output = std::exchange(runtime.match_output, &capture);
  const auto previous_consume = std::exchange(runtime.consume_depth, 0);
  const auto* previous_printed = runtime.last_printed;
  const Value keywords{std::make_shared<Record>()};
  std::size_t index = 0;
  const auto* matched = match_rows(context, expression, target, scope, [&](const Sequence& rows) {
    for (const auto& row : rows.items) {
      if (!runtime.tick()) return false;
      const auto& fields = *object<Record>(row);
      auto bindings = std::make_shared<Record>();
      for (const auto& name : fields.keys) {
        const auto* node = object<NativeNode>(fields.fields.at(name));
        if (node) {
          auto copied = streamed_binding(*node, fields.source_file);
          if (!copied) {
            runtime.fail("could not serialize a match binding");
            return false;
          }
          bindings->set(name, {std::move(copied)});
        }
      }
      const auto mark = runtime.temporaries.size();
      const Value arguments{std::move(bindings)};
      const auto* result = ctk_jit_value_invoke_v1(&runtime, body, &arguments, &keywords);
      runtime.last_printed = previous_printed;
      runtime.temporaries.resize(mark);
      if (runtime.exit_requested) return false;
      if (!result) {
        const auto error = runtime.error;
        runtime.fail(llvm::Twine("match row ") + llvm::Twine(index) + ": " + error +
                     " (line " + llvm::Twine(capture.line) + ", column " +
                     llvm::Twine(capture.column) + ")");
        return false;
      }
      ++index;
    }
    return true;
  });
  runtime.match_output = previous_output;
  runtime.consume_depth = previous_consume;
  runtime.last_printed = previous_printed;
  if (!matched && !runtime.exit_requested)
    return nullptr;
  if (!statement)
    return runtime.hold({std::move(capture.text)});
  // File-routed prints were already written at their original position.
  if (!capture.text.empty()) {
    auto destination = std::exchange(runtime.state.output_path, {});
    const auto emitted = emit_text(runtime, capture.text);
    runtime.state.output_path = std::move(destination);
    if (!emitted) return nullptr;
  }
  return runtime.hold({});
}

extern "C" const Value* ctk_jit_setting_v1(
    IrContext* context, const char* name, const Value* value, std::int32_t user, std::int32_t append) {
  try {
    return update_setting(context->values, name, value, user, append);
  } catch (const std::exception& error) {
    return context->values.fail(error.what());
  }
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
    if (!context->targets.ast || !context->targets.local.accepts(context->targets.ast))
      return context->values.fail("analysis requires a target in the active scope");
    return analyze(context->values, operation, context->targets.ast, nullptr, operand,
                   options, display);
  }
  if (const auto* selected = retained_node(*target)) {
    if (!context->targets.local.accepts(selected->ast))
      return context->values.fail("AST is outside the resource scope manifest");
    return analyze(context->values, operation, selected->ast, selected, operand,
                   options, display);
  }
  if (const auto* ast = value_access::as<AstHandle>(*target)) {
    if (!context->targets.local.accepts(*ast))
      return context->values.fail("AST is outside the resource scope manifest");
    return analyze(context->values, operation, *ast, nullptr, operand, options, display);
  }
  if (const auto* path = file_path(*target)) {
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
  if (!context->targets.local.accepts(node->ast))
    return context->values.fail("AST is outside the resource scope manifest");
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

extern "C" const Value* ctk_jit_history_v1(IrContext* context, const char* action,
                                          const Value* value);
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
  expose("ctk_jit_glob_v1", &ctk_jit_glob_v1);
  expose("ctk_jit_parse_v1", &ctk_jit_parse_v1);
  expose("ctk_jit_parse_cpp_v1", &ctk_jit_parse_cpp_v1);
  expose("ctk_jit_match_value_v2", &ctk_jit_match_value_v2);
  expose("ctk_jit_match_block_v1", &ctk_jit_match_block_v1);
  expose("ctk_jit_setting_v1", &ctk_jit_setting_v1);
  expose("ctk_jit_local_operation_v1", &ctk_jit_local_operation_v1);
  expose("ctk_jit_analyze_v1", &ctk_jit_analyze_v1);
  expose("ctk_jit_navigate_v1", &ctk_jit_navigate_v1);
  expose("ctk_jit_import_v1", &ctk_jit_import_v1);
  expose("ctk_jit_history_v1", &ctk_jit_history_v1);
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
  explicit RuntimeCompiler(llvm::orc::LLJIT& jit, NativeHistory* native_history = nullptr)
      : jit(jit), channel(native_history == nullptr), native_history(native_history) {}

  llvm::Expected<CompiledCommand> compile(llvm::StringRef source, llvm::StringRef path,
                                          bool library) {
    // Library contents are checked on every import. Existing function
    // bindings keep their previous machine code alive across library edits.
    const auto key = library ? path.str() : source.str();
    auto& cache = library ? libraries : expressions;
    const auto cached = cache.find(key);
    if (cached != cache.end() && cached->second.source == source)
      return cached->second.command;

    auto lowered = channel.available() ? channel.lower(source, path, library) :
                                        lower_ctk(source, false, path, library);
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

  bool has_frontend() const { return channel.available(); }

  std::optional<std::string> present(llvm::StringRef kind, llvm::json::Value value) {
    return channel.render(kind, std::move(value));
  }

  llvm::Error history(llvm::StringRef action, const std::string* value) {
    return native_history ? native_history->action(action, value) : channel.history(action, value);
  }

  std::vector<std::string> import_stack;

private:
  struct Cached {
    std::string source;
    CompiledCommand command;
  };

  llvm::orc::LLJIT& jit;
  CompilerChannel channel;
  NativeHistory* native_history;
  llvm::StringMap<Cached> libraries;
  llvm::StringMap<Cached> expressions;
  std::uint64_t next = 0;
};

extern "C" const Value* ctk_jit_history_v1(IrContext* context, const char* action,
                                          const Value* value) {
  const auto* text = value ? value_access::as<std::string>(*value) : nullptr;
  if (value && !text)
    return context->values.fail("history requires a string");
  if (auto error = context->compiler.history(action, text))
    return context->values.fail(llvm::toString(std::move(error)));
  return context->values.hold({});
}

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

std::optional<std::string> Values::present(llvm::StringRef kind, const Value& value) {
  auto& compiler = static_cast<IrContext*>(context)->compiler;
  if (!compiler.has_frontend())
    return std::nullopt;
  return compiler.present(kind, preview_value(value));
}

std::optional<std::string> Values::present(llvm::StringRef kind,
                                           const google::protobuf::Message& message) {
  auto& compiler = static_cast<IrContext*>(context)->compiler;
  if (!compiler.has_frontend())
    return std::nullopt;
  return compiler.present(kind, preview_message(message));
}

bool Values::accepts_ast(const AstHandle& ast) const {
  return static_cast<const IrContext*>(context)->targets.local.accepts(ast);
}

llvm::Expected<std::unique_ptr<llvm::MemoryBuffer>> compile_ir_object(llvm::StringRef source) {
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
  return llvm::orc::SimpleCompiler(**machine)(**module);
}

llvm::Error compile_ir(llvm::StringRef source) {
  auto object = compile_ir_object(source);
  if (!object) {
    return object.takeError();
  }
  llvm::outs() << (*object)->getBuffer();
  return llvm::Error::success();
}

llvm::Error run_ir(std::unique_ptr<llvm::MemoryBuffer> input, bool precompiled, llvm::StringRef file,
                   llvm::StringRef database, const LoadTarget& load, const ScriptArguments& arguments,
                   bool standalone) {
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
  std::optional<NativeHistory> history;
  if (standalone)
    history.emplace();
  RuntimeCompiler compiler(**jit, history ? &*history : nullptr);
  std::mutex output_mutex;
  Targets targets(file, database, load);
  targets.local.set_events([&](std::string event) {
    std::lock_guard lock(output_mutex);
    llvm::outs() << event << '\n';
    llvm::outs().flush();
  });
  auto bindings = targets.bindings(arguments);
  MatcherCache matchers;
  IrContext runtime(targets, bindings, matchers, compiler);
  if (!load_settings(runtime.values)) return failure(runtime.error);
  if (!file.empty()) {
    auto target = targets.select(file);
    if (!target) return target.takeError();
  }
  auto result = call_ir_entry(*entry, runtime);
  targets.local.finish();
  {
    std::lock_guard lock(output_mutex);
    llvm::outs() << runtime.output;
  }
  return result;
}

llvm::Error repl_ir(llvm::StringRef file, llvm::StringRef database,
                    const LoadTarget& load, const ScriptArguments& arguments,
                    const ReplIO* io) {
  auto jit = create_ir_jit();
  if (!jit) {
    return jit.takeError();
  }
  std::optional<NativeHistory> history;
  if (io)
    history.emplace();
  RuntimeCompiler compiler(**jit, history ? &*history : nullptr);
  std::mutex output_mutex;
  auto reply = [&](llvm::json::Object response) {
    std::lock_guard lock(output_mutex);
    if (io) {
      io->send(std::move(response));
    } else {
      llvm::outs() << llvm::json::Value(std::move(response)) << '\n';
      llvm::outs().flush();
    }
  };
  Targets targets(file, database, load);
  targets.local.set_events([&](std::string event) { reply(llvm::json::Object{{"event", std::move(event)}}); });
  auto bindings = targets.bindings(arguments);
  Workspace workspace(bindings, reply);
  MatcherCache matchers;
  {
    IrContext runtime(targets, bindings, matchers, compiler);
    if (!load_settings(runtime.values)) return failure(runtime.error);
  }
  if (!file.empty()) {
    auto target = targets.select(file);
    if (!target) return target.takeError();
  }
  llvm::DenseMap<std::int64_t, CompiledCommand> commands;
  std::uint64_t entry_number = 0;
  install_repl_cancellation();
  llvm::json::Object ready{{"ready", true}, {"protocol", 3}};
  if (history) {
    auto commands = history->read();
    if (commands)
      ready["history"] = std::move(*commands);
    else
      ready["history_error"] = llvm::toString(commands.takeError());
  }
  if (io) {
    reply(std::move(ready));
  } else {
    llvm::outs() << "{\"ready\":true,\"protocol\":3}\n";
    llvm::outs().flush();
  }

  auto receive = [&]() -> llvm::Expected<std::optional<llvm::json::Object>> {
    if (io)
      return io->receive();
    std::string line;
    if (!std::getline(std::cin, line))
      return std::nullopt;
    auto request = llvm::json::parse(line);
    if (!request)
      return request.takeError();
    if (auto* object = request->getAsObject())
      return std::move(*object);
    return failure("expected a REPL command object");
  };

  // Requests identify a cache slot and supply code only on a miss.
  for (;;) {
    auto request = receive();
    if (!request)
      return request.takeError();
    if (!*request)
      break;
    const auto* command = &**request;
    if (command) {
      if (const auto inspect = command->getString("inspect")) {
        if (*inspect == "outline") {
          reply(llvm::json::Object{{"value", workspace.outline(*command)}});
        } else if (*inspect == "complete_fields") {
          IrContext runtime(targets, bindings, matchers, compiler);
          const auto reference = command->getString("reference").value_or("");
          const auto presence = command->getBoolean("presence").value_or(false);
          reply(llvm::json::Object{{"value", complete_fields(runtime.values, reference, presence)}});
        } else if (*inspect == "resources" || *inspect == "status") {
          auto value = targets.local.workspace_state(*inspect);
          if (*inspect == "resources") {
            std::size_t number = 1;
            while (bindings.contains("attached" + std::to_string(number)))
              ++number;
            (*value.getAsObject())["attach_name"] = "attached" + std::to_string(number);
          }
          reply(llvm::json::Object{{"value", std::move(value)}});
        } else if (*inspect == "batch_status" || *inspect == "batch_cancel") {
          IrContext runtime(targets, bindings, matchers, compiler);
          const auto id = command->getString("run_id").value_or("");
          const auto* value = targets.local.execute(
              runtime.values, *inspect, Sequence{{Value{id.str()}}}, "", false);
          reply(llvm::json::Object{{"value", value ? preview_value(*value) : nullptr},
                                  {"error", std::move(runtime.error)}});
        } else {
          reply(llvm::json::Object{{"error", "unknown workspace request"}});
        }
        continue;
      }
    }
    const auto slot = command->getInteger("slot");
    if (!slot || *slot < 0) {
      return failure("expected a REPL command slot");
    }

    clear_repl_cancellation();
    auto cached = commands.find(*slot);
    bool compiled = false;
    bool incomplete = false;
    llvm::Error result = llvm::Error::success();
    auto ir = command->getString("ir");
    std::string native_ir;
    if (auto source = command->getString("source")) {
      if (ir) {
        result = failure("provide CTK source or LLVM IR");
      } else {
        auto lowered = lower_ctk(*source, true, {}, false, &incomplete);
        if (!lowered) {
          result = lowered.takeError();
        } else {
          native_ir = std::move(*lowered);
          ir = native_ir;
        }
      }
    }
    if (history && !(incomplete && command->getBoolean("prompt").value_or(false))) {
      if (auto source = command->getString("history")) {
        if (auto error = history->append(*source))
          reply(llvm::json::Object{{"history_error", llvm::toString(std::move(error))}});
      }
    }
    if (ir && !result) {
      // The previous entry remains usable until the replacement links.
      const auto name = "ctk_jit_repl_entry_" + std::to_string(entry_number++);
      auto tracker = (*jit)->getMainJITDylib().createResourceTracker();
      result = add_ir(**jit, *ir, tracker, name);
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
    if (command->getBoolean("workspace").value_or(false))
      runtime.values.workspace = &workspace;
    runtime.values.cancellable =
        runtime.values.workspace || command->getBoolean("prompt").value_or(false);
    if (!result) {
      if (cached == commands.end()) {
        return failure("unknown REPL command slot");
      }
      runtime.values.code = cached->second.code;
      result = call_ir_entry(cached->second.entry, runtime);
    }
    clear_repl_cancellation();
    llvm::json::Array previews;
    for (auto& item : runtime.values.previews)
      previews.push_back(llvm::json::Object{{"offset", static_cast<std::int64_t>(item.offset)},
                                            {"id", item.id}, {"kind", std::move(item.kind)},
                                            {"key", std::move(item.key)},
                                            {"markdown", std::move(item.markdown)}});
    reply(llvm::json::Object{
        {"compiled", compiled},
        {"incomplete", incomplete},
        {"previews", std::move(previews)},
        {"exit", runtime.values.exit_requested},
        {"history_cleared", history && history->take_cleared()},
        {"output", std::move(runtime.output)},
        {"error", llvm::toString(std::move(result))},
    });
  }
  targets.local.finish();
  return llvm::Error::success();
}

} // namespace ctk::jit
