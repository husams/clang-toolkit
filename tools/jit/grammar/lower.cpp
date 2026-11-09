#include "lower.hpp"
#include "help.hpp"
#include "syntax.hpp"
#include "ctk/support/algorithm.hpp"

#include <algorithm>
#include <charconv>
#include <cstdint>
#include <initializer_list>
#include <limits>
#include <memory>
#include <stdexcept>
#include <string_view>
#include <utility>

#include <llvm/ADT/STLFunctionalExtras.h>
#include <llvm/ADT/SmallVector.h>
#include <llvm/ADT/StringExtras.h>
#include <llvm/ADT/StringMap.h>
#include <llvm/IR/IRBuilder.h>
#include <llvm/IR/Module.h>
#include <llvm/IR/Verifier.h>
#include <llvm/Support/FormatVariadic.h>
#include <llvm/Support/JSON.h>
#include <llvm/Support/raw_ostream.h>

namespace ctk::jit {
namespace {

using IrValue = llvm::Value;
using Kind = std::string_view;
using Children = llvm::SmallVector<const Syntax *, 8>;

Kind kind(const Syntax &node) {
  auto name = node.name;
  if (ctk::compat::starts_with(name, "proto_"))
    name.remove_prefix(6);
  else if (ctk::compat::starts_with(name, "legacy_"))
    name.remove_prefix(7);
  return name;
}

Children terms(const Syntax &node) {
  Children result;
  for (const auto &child : node.children) {
    const auto name = kind(child);
    if (name != "separators" && name != "soft_newlines" &&
        child.name != "PROTO_NEWLINE")
      result.push_back(&child);
  }
  return result;
}

const Syntax &unbox(const Syntax &node) {
  const auto name = kind(node);
  if (name == "comparison" || name == "pipe_expr" || name == "recovery_expr" ||
      name == "grouped_expression" || name == "inner_expression") {
    const auto children = terms(node);
    if (children.size() == 1)
      return unbox(*children.front());
  }
  return node;
}

class Lowering {
public:
  explicit Lowering(llvm::StringRef source)
      : source(source), module("ctk", context), builder(context) {}

  std::string lower(const Syntax &tree, bool display, llvm::StringRef path,
                    bool library) {
    auto *type = llvm::FunctionType::get(builder.getInt32Ty(),
                                         {builder.getPtrTy()}, false);
    function = llvm::Function::Create(type, llvm::GlobalValue::ExternalLinkage,
                                      "ctk_jit_run_ir_v1", module);
    runtime = function->getArg(0);
    builder.SetInsertPoint(block("entry"));
    error = block("error");
    values = call("ctk_jit_value_context_v1", builder.getPtrTy(), {runtime});
    if (!path.empty())
      native("set_source", builder.getVoidTy(), {string(path)});
    if (library) {
      for (const auto *item : terms(tree)) {
        const auto name = kind(unbox(*item));
        if (name == "let_stmt" || name == "runnable_definition")
          continue;
        if (name == "host_statement" || name == "host_expression") {
          const auto command = kind(unbox(*item).children.front());
          if (command == "import_command" || command == "matcher_definition")
            continue;
        }
        fail(*item, "libraries accept let definitions and import statements");
      }
    }
    auto *result = statements(tree, display);
    native("set_result", builder.getVoidTy(), {result});
    builder.CreateRet(builder.getInt32(0));
    builder.SetInsertPoint(error);
    builder.CreateRet(builder.getInt32(1));

    std::string ir;
    llvm::raw_string_ostream output(ir);
    if (llvm::verifyModule(module, &output))
      throw std::runtime_error("invalid native CTK IR: " + ir);
    module.print(output, nullptr);
    return ir;
  }

private:
  [[noreturn]] void fail(const Syntax &node, llvm::Twine message) const {
    const auto prefix = source.take_front(node.begin);
    const auto line = ctk::compat::count(prefix, '\n') + 1;
    const auto newline = prefix.rfind('\n');
    const auto previous = newline == llvm::StringRef::npos
                              ? prefix
                              : prefix.drop_front(newline + 1);
    const auto column =
        ctk::compat::count_if(previous,
                              [](char byte) {
                                return (static_cast<unsigned char>(byte) &
                                        0xc0) != 0x80;
                              }) +
        1;
    throw std::runtime_error(
        llvm::formatv("line {0}, column {1}: {2}", line, column, message.str())
            .str());
  }

  llvm::BasicBlock *block(llvm::StringRef name) {
    return llvm::BasicBlock::Create(context, name, function);
  }

  llvm::ConstantPointerNull *null() {
    return llvm::ConstantPointerNull::get(builder.getPtrTy());
  }

  IrValue *call(llvm::StringRef name, llvm::Type *type,
                llvm::ArrayRef<IrValue *> args, bool checked = false) {
    llvm::SmallVector<llvm::Type *, 8> parameters;
    for (auto *arg : args)
      parameters.push_back(arg->getType());
    auto callee = module.getOrInsertFunction(
        name, llvm::FunctionType::get(type, parameters, false));
    auto *result = builder.CreateCall(callee, args);
    if (checked)
      guard(builder.CreateIsNotNull(result));
    return result;
  }

  IrValue *native(llvm::StringRef name, llvm::Type *type,
                  std::initializer_list<IrValue *> args = {},
                  unsigned abi = 1) {
    llvm::SmallVector<IrValue *, 8> operands{values};
    operands.append(args.begin(), args.end());
    const auto symbol =
        ("ctk_jit_value_" + name + "_v" + llvm::Twine(abi)).str();
    return call(symbol, type, operands, type->isPointerTy());
  }

  IrValue *value(llvm::StringRef name,
                 std::initializer_list<IrValue *> args = {}, unsigned abi = 1) {
    return native(name, builder.getPtrTy(), args, abi);
  }

  void guard(IrValue *condition) {
    auto *next = block("ok");
    builder.CreateCondBr(condition, next, error);
    builder.SetInsertPoint(next);
  }

  IrValue *string(llvm::StringRef text) {
    auto [entry, fresh] = strings.try_emplace(text, nullptr);
    if (fresh)
      entry->second = builder.CreateGlobalString(text, "", 0, &module);
    return entry->second;
  }

  IrValue *literal(unsigned type, llvm::StringRef data = {}) {
    return value("literal", {string(data), builder.getInt64(data.size()),
                             builder.getInt32(type)});
  }

  IrValue *truth(IrValue *operand) {
    auto *status = native("truth", builder.getInt32Ty(), {operand});
    guard(builder.CreateICmpSGE(status, builder.getInt32(0)));
    return builder.CreateICmpEQ(status, builder.getInt32(1));
  }

  IrValue *collection(unsigned type) {
    return value("new", {builder.getInt32(type)});
  }

  void define(Kind name, IrValue *operand, IrValue *index = nullptr) {
    native("define", builder.getVoidTy(),
           {string(name), operand, index ? index : builder.getInt64(-1)});
  }

  struct Cleanup {
    const Syntax *body;
    std::int64_t depth;
    llvm::BasicBlock *failure;
  };

  struct Loop {
    llvm::BasicBlock *end;
    llvm::BasicBlock *advance;
    std::int64_t depth;
    std::size_t cleanup_count;
    std::int64_t consume;
  };

  void push() {
    native("push", builder.getVoidTy());
    ++scope_depth;
  }

  void pop() {
    native("pop", builder.getVoidTy());
    --scope_depth;
  }

  void unwind(std::int64_t depth) {
    native("unwind", builder.getVoidTy(), {builder.getInt64(depth)});
  }

  IrValue *action(const Syntax &node) {
    const auto &body =
        kind(node) == "handler_block" ? node.children.front() : node;
    if (kind(body) == "block")
      return expression(body);
    push();
    auto *result = expression(body);
    pop();
    return result;
  }

  void recover_status() {
    auto *status = native("recover", builder.getInt32Ty());
    guard(builder.CreateICmpEQ(status, builder.getInt32(0)));
  }

  template <typename Emit>
  IrValue *with_recovery(Emit &&body, const Syntax *handler) {
    if (!handler)
      return body();
    auto *outer = error;
    auto *fallback = block("recover");
    auto *done = block("recovered");
    error = fallback;
    auto *result = body();
    auto *normal = builder.GetInsertBlock();
    builder.CreateBr(done);
    builder.SetInsertPoint(fallback);
    unwind(scope_depth);
    error = outer;
    recover_status();
    auto *recovered = action(*handler);
    auto *handled = builder.GetInsertBlock();
    builder.CreateBr(done);
    builder.SetInsertPoint(done);
    auto *selected = builder.CreatePHI(builder.getPtrTy(), 2);
    selected->addIncoming(result, normal);
    selected->addIncoming(recovered, handled);
    return selected;
  }

  void execute_cleanups(std::size_t keep) {
    auto saved = cleanups;
    auto *saved_error = error;
    const auto depth = scope_depth;
    for (std::size_t index = saved.size(); index > keep; --index) {
      const auto &cleanup = saved[index - 1];
      cleanups.resize(index - 1);
      error = cleanup.failure;
      scope_depth = cleanup.depth;
      unwind(scope_depth);
      action(*cleanup.body);
    }
    cleanups = std::move(saved);
    error = saved_error;
    scope_depth = depth;
  }

  IrValue *flow(const Syntax &node, bool breaking) {
    if (loops.empty())
      fail(node, "loop control requires a scripting loop");
    const auto loop = loops.back();
    execute_cleanups(loop.cleanup_count);
    unwind(loop.depth);
    for (auto depth = loop.consume; depth < consume_depth; ++depth)
      native("consume_end", builder.getVoidTy());
    builder.CreateBr(breaking ? loop.end : loop.advance);
    builder.SetInsertPoint(block("unreachable"));
    return literal(0);
  }

  IrValue *stop() {
    execute_cleanups(0);
    native("exit", builder.getVoidTy());
    if (function->getReturnType()->isPointerTy())
      builder.CreateRet(null());
    else
      builder.CreateRet(builder.getInt32(0));
    builder.SetInsertPoint(block("after.exit"));
    return literal(0);
  }

  IrValue *condition_loop(const Children &children, bool repeat, bool collect) {
    auto *result = collect ? collection(0) : literal(0);
    auto *check = block("loop.check");
    auto *iteration = block("loop.iteration");
    auto *done = block("loop.end");
    const auto &condition = *children[repeat ? 1 : 0];
    const auto &body = *children[repeat ? 0 : 1];
    builder.CreateBr(repeat ? iteration : check);
    builder.SetInsertPoint(check);
    auto *test = truth(expression(condition));
    builder.CreateCondBr(test, repeat ? done : iteration,
                         repeat ? iteration : done);
    builder.SetInsertPoint(iteration);
    auto *status = native("tick", builder.getInt32Ty());
    guard(builder.CreateICmpEQ(status, builder.getInt32(0)));
    loops.push_back({done, check, scope_depth, cleanups.size(), consume_depth});
    push();
    auto *item = expression(body, collect);
    pop();
    loops.pop_back();
    if (collect)
      value("add", {result, null(), item});
    builder.CreateBr(check);
    builder.SetInsertPoint(done);
    return result;
  }

  IrValue *consumed(const Syntax &node) {
    auto *outer = error;
    auto *failed = block("consume.failed");
    auto *done = block("consume.done");
    error = failed;
    native("consume_begin", builder.getVoidTy());
    ++consume_depth;
    auto *result = expression(node);
    --consume_depth;
    error = outer;
    native("consume_end", builder.getVoidTy());
    builder.CreateBr(done);
    builder.SetInsertPoint(failed);
    native("consume_end", builder.getVoidTy());
    builder.CreateBr(outer);
    builder.SetInsertPoint(done);
    return result;
  }

  IrValue *statements(const Syntax &node, bool display = false,
                      bool collect = false) {
    auto items = terms(node);
    const Syntax *on_error = nullptr;
    const Syntax *on_exit = nullptr;
    auto position = items.begin();
    while (position != items.end()) {
      const auto name = kind(**position);
      if (name != "error_handler" && name != "exit_handler")
        break;
      auto *&handler = name == "error_handler" ? on_error : on_exit;
      if (handler)
        fail(**position, "duplicate CTK handler");
      handler = &(*position)->children.back();
      ++position;
    }
    const auto body = [&]() {
      return with_recovery(
          [&]() {
            auto *result = literal(0);
            for (auto current = position; current != items.end(); ++current) {
              const auto &root = unbox(**current);
              const auto name = kind(root);
              const bool visible =
                  display && name != "let_stmt" && name != "assign_stmt" &&
                  name != "print_stmt" && name != "host_statement" &&
                  name != "runnable_definition";
              auto *offset = visible
                                 ? native("output_size", builder.getInt64Ty())
                                 : nullptr;
              result = expression(root,
                                  collect && std::next(current) == items.end());
              if (offset)
                value(
                    "display",
                    {result, offset, builder.getInt32(name == "foreach_expr")},
                    2);
            }
            return result;
          },
          on_error);
    };
    if (!on_exit)
      return body();

    auto *outer = error;
    auto *failed = block("cleanup.failed");
    auto *done = block("cleanup.done");
    error = failed;
    cleanups.push_back({on_exit, scope_depth, outer});
    auto *result = body();
    cleanups.pop_back();
    error = outer;
    action(*on_exit);
    builder.CreateBr(done);
    builder.SetInsertPoint(failed);
    unwind(scope_depth);
    auto *previous = value("save_error");
    action(*on_exit);
    native("restore_error", builder.getVoidTy(), {previous});
    builder.CreateBr(outer);
    builder.SetInsertPoint(done);
    return result;
  }

  IrValue *conditional(const Syntax &node, const Children &children) {
    auto *yes = block("then");
    auto *no = block("else");
    auto *done = block("merge");
    auto *condition = truth(expression(*children[0]));
    if (kind(node) == "unless_expr")
      condition = builder.CreateNot(condition);
    builder.CreateCondBr(condition, yes, no);
    builder.SetInsertPoint(yes);
    auto *a = expression(*children[1]);
    auto *a_end = builder.GetInsertBlock();
    builder.CreateBr(done);
    builder.SetInsertPoint(no);
    auto *b = children.size() == 3 ? expression(*children[2]) : literal(0);
    auto *b_end = builder.GetInsertBlock();
    builder.CreateBr(done);
    builder.SetInsertPoint(done);
    auto *result = builder.CreatePHI(builder.getPtrTy(), 2);
    result->addIncoming(a, a_end);
    result->addIncoming(b, b_end);
    return result;
  }

  using Bindings = llvm::SmallVector<std::pair<Kind, IrValue *>, 8>;

  void pattern(const Syntax &node, IrValue *operand, Bindings &bindings) {
    const auto name = kind(node);
    const auto children = terms(node);
    if (name == "grouped_pattern") {
      pattern(*children.front(), operand, bindings);
      return;
    }
    if (name == "name_pattern") {
      const auto identifier = children.front()->text;
      if (identifier == "_")
        return;
      if (ctk::compat::any_of(bindings, [&](const auto &item) {
            return item.first == identifier;
          }))
        fail(node, "destructuring pattern has duplicate names");
      bindings.emplace_back(identifier, operand);
      return;
    }
    if (name == "discard_pattern")
      return;
    if (name == "cons_pattern") {
      auto *checked =
          value("pattern", {operand, builder.getInt32(2), builder.getInt64(1)});
      auto *head = value("at", {checked, builder.getInt64(0)});
      auto *tail = value("tail", {checked});
      pattern(*children[0], head, bindings);
      pattern(*children[1], tail, bindings);
      return;
    }
    const auto list = name == "list_pattern" || name == "empty_list_pattern";
    if (!list && name != "tuple_pattern" && name != "empty_pattern" &&
        name != "tuple_single_pattern")
      fail(node, "expected a CTK binding pattern");
    auto *checked = value("pattern", {operand, builder.getInt32(list ? 0 : 1),
                                      builder.getInt64(children.size())});
    for (std::size_t index = 0; index < children.size(); ++index) {
      auto *item = value("at", {checked, builder.getInt64(index)});
      pattern(*children[index], item, bindings);
    }
  }

  void bind(const Syntax &node, IrValue *operand, IrValue *index = nullptr) {
    if (kind(node) == "name_pattern" && node.children.front().text != "_") {
      define(node.children.front().text, operand, index);
      return;
    }
    Bindings bindings;
    pattern(node, operand, bindings);
    for (auto [name, item] : bindings)
      define(name, item);
  }

  struct Parameter {
    const Syntax *pattern = nullptr;
    Kind label;
    const Syntax *fallback = nullptr;
  };

  Parameter parameter(const Syntax &entry) {
    const auto children = terms(entry);
    const auto &first = *children.front();
    const auto name = kind(first);
    if (name == "labeled_parameter") {
      const auto &fields = first.children;
      return {&fields[1], fields.front().text,
              fields.size() == 3 ? &fields.back() : nullptr};
    }
    if (name == "shorthand_parameter" ||
        name == "shorthand_default_parameter") {
      const auto &fields = first.children;
      return {&fields.front(), fields.front().text,
              fields.size() > 1 ? &fields.back() : nullptr};
    }
    return {&first,
            kind(first) == "name_pattern" ? first.children.front().text
                                          : Kind{},
            children.size() == 2 ? children.back() : nullptr};
  }

  IrValue *parameter_labels(llvm::ArrayRef<Parameter> parameters) {
    llvm::SmallVector<llvm::Constant *, 8> names;
    for (const auto &param : parameters) {
      auto *pointer = param.label.empty() || param.label == "_"
                          ? null()
                          : string(param.label);
      names.push_back(llvm::cast<llvm::Constant>(pointer));
    }
    if (names.empty())
      return null();
    auto *type = llvm::ArrayType::get(builder.getPtrTy(), names.size());
    auto constant = std::make_unique<llvm::GlobalVariable>(
        type, true, llvm::GlobalValue::PrivateLinkage,
        llvm::ConstantArray::get(type, names));
    auto *address = constant.get();
    module.insertGlobalVariable(constant.release());
    return address;
  }

  void bind_parameters(llvm::ArrayRef<Parameter> parameters,
                       std::size_t required, IrValue *arguments,
                       IrValue *keywords) {
    auto *status = native("check_arguments", builder.getInt32Ty(),
                          {arguments, keywords, parameter_labels(parameters),
                           builder.getInt64(parameters.size()),
                           builder.getInt64(required)});
    guard(builder.CreateICmpEQ(status, builder.getInt32(0)));
    for (std::size_t index = 0; index < parameters.size(); ++index) {
      const auto &param = parameters[index];
      auto *label = param.label.empty() || param.label == "_"
                        ? null()
                        : string(param.label);
      auto *operand =
          call("ctk_jit_value_argument_v1", builder.getPtrTy(),
               {values, arguments, keywords, builder.getInt64(index), label});
      if (param.fallback) {
        auto *supplied = builder.GetInsertBlock();
        auto *missing = block("default");
        auto *done = block("argument");
        builder.CreateCondBr(builder.CreateIsNotNull(operand), done, missing);
        builder.SetInsertPoint(missing);
        auto *fallback = expression(*param.fallback);
        auto *fallback_end = builder.GetInsertBlock();
        builder.CreateBr(done);
        builder.SetInsertPoint(done);
        auto *result = builder.CreatePHI(builder.getPtrTy(), 2);
        result->addIncoming(operand, supplied);
        result->addIncoming(fallback, fallback_end);
        operand = result;
      }
      if (!param.pattern->text.empty())
        define(param.pattern->text, operand);
      else
        bind(*param.pattern, operand);
    }
  }

  IrValue *
  make_callable(Kind name, std::size_t required, std::size_t arity,
                llvm::function_ref<IrValue *(IrValue *, IrValue *)> emit_body) {
    auto *ptr = builder.getPtrTy();
    auto *type = llvm::FunctionType::get(ptr, {ptr, ptr, ptr, ptr}, false);
    auto *entry = llvm::Function::Create(
        type, llvm::GlobalValue::InternalLinkage, "ctk.runnable", module);
    {
      llvm::IRBuilderBase::InsertPointGuard saved(builder);
      auto *parent = std::exchange(function, entry);
      auto *parent_error = std::exchange(error, block("error"));
      auto *parent_runtime = std::exchange(runtime, entry->getArg(0));
      auto *parent_values = std::exchange(values, entry->getArg(1));
      auto parent_loops = std::exchange(loops, {});
      auto parent_cleanups = std::exchange(cleanups, {});
      const auto parent_scope = std::exchange(scope_depth, 0);
      const auto parent_consume = std::exchange(consume_depth, 0);
      auto *start = llvm::BasicBlock::Create(context, "entry", entry, error);
      builder.SetInsertPoint(start);
      auto *result = emit_body(entry->getArg(2), entry->getArg(3));
      builder.CreateRet(result);
      builder.SetInsertPoint(error);
      builder.CreateRet(null());
      function = parent;
      error = parent_error;
      runtime = parent_runtime;
      values = parent_values;
      loops = std::move(parent_loops);
      cleanups = std::move(parent_cleanups);
      scope_depth = parent_scope;
      consume_depth = parent_consume;
    }
    return value("runnable",
                 {string(name), entry, builder.getInt64(required),
                  builder.getInt64(arity)},
                 2);
  }

  IrValue *callable(Kind name, llvm::ArrayRef<Parameter> parameters,
                    const Syntax &body, bool match_body = false) {
    std::size_t required = parameters.size();
    bool defaulted = false;
    for (std::size_t index = 0; index < parameters.size(); ++index) {
      if (parameters[index].fallback && !defaulted) {
        defaulted = true;
        required = index;
      } else if (!parameters[index].fallback && defaulted) {
        fail(body, "required parameter after default parameter");
      }
    }
    return make_callable(name, required, parameters.size(),
                         [&](IrValue *args, IrValue *keywords) {
                           if (match_body) {
                             value("match_bindings", {args});
                             statements(body, true);
                             return literal(0);
                           }
                           bind_parameters(parameters, required, args,
                                           keywords);
                           return expression(body);
                         });
  }

  IrValue *clause_runnable(const Syntax &node, Kind name = "<inline>") {
    struct Clause {
      llvm::SmallVector<Parameter, 8> parameters;
      const Syntax *body;
    };
    std::vector<Clause> clauses;
    for (const auto *item : terms(node)) {
      const auto parts = terms(*item);
      Clause clause{{}, parts.back()};
      if (kind(*parts.front()) == "parameters")
        for (const auto *entry : terms(*parts.front())) {
          auto param = parameter(*entry);
          if (param.fallback)
            fail(*entry, "function clauses cannot have defaults");
          param.label = {};
          clause.parameters.push_back(param);
        }
      if (!clauses.empty() &&
          clause.parameters.size() != clauses.front().parameters.size())
        fail(*item, "function clauses must have the same arity");
      clauses.push_back(std::move(clause));
    }
    const auto arity = clauses.front().parameters.size();
    return make_callable(
        name, arity, arity, [&](IrValue *args, IrValue *keywords) -> IrValue * {
          auto *failure = error;
          for (const auto &clause : clauses) {
            auto *next = block("next.clause");
            push();
            error = next;
            bind_parameters(clause.parameters, arity, args, keywords);
            error = failure;
            auto *result = expression(*clause.body);
            pop();
            builder.CreateRet(result);
            builder.SetInsertPoint(next);
            native("pop", builder.getVoidTy());
            native("clear_error", builder.getVoidTy());
          }
          native("fail", builder.getVoidTy(),
                 {string("no matching clause for " + std::string(name))});
          builder.CreateBr(failure);
          builder.SetInsertPoint(block("unreachable"));
          return null();
        });
  }

  IrValue *runnable(const Syntax &node, const Children &children) {
    const bool named = kind(node) == "runnable_definition";
    const auto name = named ? children.front()->text : Kind{};
    const auto param_index = named ? 1U : 0U;
    llvm::SmallVector<Parameter, 8> parameters;
    if (kind(*children[param_index]) == "parameters")
      for (const auto *entry : terms(*children[param_index]))
        parameters.push_back(parameter(*entry));
    auto *result = callable(name, parameters, *children.back());
    if (named)
      define(name, result);
    return result;
  }

  Syntax parse_block(const Syntax &node) {
    const auto text = source.slice(node.begin + 1, node.end - 1);
    auto tree = parse_ctk(text);
    if (!tree)
      fail(node, llvm::toString(tree.takeError()));
    const auto adjust = [&](auto &&recurse, Syntax &child) -> void {
      child.begin += node.begin + 1;
      child.end += node.begin + 1;
      for (auto &part : child.children)
        recurse(recurse, part);
    };
    adjust(adjust, *tree);
    auto body = std::move(tree->children.front().children.front());
    return body;
  }

  IrValue *for_each(const Children &children) {
    const auto &pattern = *children[0];
    auto *items = value("iterate", {expression(*children[2])});
    auto *result = collection(0);
    auto *start = builder.GetInsertBlock();
    auto *header = block("foreach");
    auto *iteration = block("item");
    auto *advance = block("advance");
    auto *done = block("end");
    builder.CreateBr(header);
    builder.SetInsertPoint(header);
    auto *index = builder.CreatePHI(builder.getInt64Ty(), 2);
    index->addIncoming(builder.getInt64(0), start);
    auto *count = native("size", builder.getInt64Ty(), {items});
    builder.CreateCondBr(builder.CreateICmpULT(index, count), iteration, done);
    builder.SetInsertPoint(iteration);
    auto *status = native("tick", builder.getInt32Ty());
    guard(builder.CreateICmpEQ(status, builder.getInt32(0)));
    auto *item = native("at", builder.getPtrTy(), {items, index});
    loops.push_back(
        {done, advance, scope_depth, cleanups.size(), consume_depth});
    push();
    bind(pattern, item, index);
    auto *result_item = expression(*children[3]);
    pop();
    loops.pop_back();
    value("add", {result, null(), result_item});
    builder.CreateBr(advance);
    builder.SetInsertPoint(advance);
    index->addIncoming(builder.CreateAdd(index, builder.getInt64(1)), advance);
    builder.CreateBr(header);
    builder.SetInsertPoint(done);
    return result;
  }

  IrValue *make_collection(const Syntax &node, Children children) {
    const auto name = kind(node);
    const bool dict = name == "dict_literal";
    if ((dict || name == "list_literal") && !children.empty())
      children = terms(*children.front());
    auto *result = collection(dict ? 2 : name == "list_literal" ? 0 : 1);
    for (const auto *item : children) {
      if (dict) {
        const auto &key = item->children[0];
        const auto text = ctk::compat::ends_with(key.name, "STRING")
                              ? decode_ctk_string(key.text)
                              : std::string(key.text);
        value("add", {result, literal(4, text), expression(item->children[1])});
      } else {
        value("add", {result, null(), expression(*item)});
      }
    }
    return result;
  }

  IrValue *matcher(const Syntax &node) {
    auto *args = collection(0);
    IrValue *binding = null();
    for (const auto &child : node.children) {
      if (kind(child) == "arguments") {
        for (const auto *argument : terms(child)) {
          if (argument->text != ",")
            value("add", {args, null(), expression(*argument)});
        }
      } else if (kind(child) == "bind") {
        binding = expression(child.children[2]);
      }
    }
    return value("matcher",
                 {string(node.children.front().text), args, binding});
  }

  IrValue *host_reference(const Syntax &node,
                          std::size_t stop = std::string::npos) {
    const auto &parts = node.children;
    const auto first = parts.front().text == "$" ? 1U : 0U;
    auto *result = value("lookup", {string(parts[first].text)});
    for (std::size_t index = first + 1; index < std::min(stop, parts.size());) {
      const auto &part = parts[index + 1];
      if (parts[index].text == "[") {
        result = value("index", {result, expression(part)});
        index += 3;
        continue;
      }
      if (!part.text.empty()) {
        result = value("get", {result, string(part.text), null()});
      } else if (kind(part) == "generic_method_call") {
        const auto name = part.children.front().children.front().text;
        Children arguments;
        Syntax unlimited{"LEGACY_STRING", "'all'", part.begin, part.end, {}};
        for (const auto &field : part.children) {
          if (kind(field) != "method_arguments")
            continue;
          for (const auto &operand : field.children) {
            if (operand.text == ",")
              continue;
            const auto *argument = &operand;
            if (kind(operand) == "named_method_argument") {
              if ((name != "callers" && name != "callees") ||
                  operand.children.front().text != "depth")
                fail(operand, "unsupported method keyword argument");
              argument = &operand.children.back();
            }
            const auto &root = unbox(*argument);
            if ((name == "callers" || name == "callees") &&
                arguments.size() == 1 && kind(root) == "reference" &&
                root.children.back().text == "all")
              argument = &unlimited;
            arguments.push_back(argument);
          }
        }
        result = method(result, name, arguments);
      } else if (kind(part) == "has_field_call" ||
                 kind(part) == "has_key_call") {
        const auto name =
            kind(part) == "has_field_call" ? "hasField" : "hasKey";
        result = method(result, name, {&part.children[2]});
      } else {
        fail(part, "native lowering is unavailable for this reference method");
      }
      index += 2;
    }
    return result;
  }

  IrValue *local_operation(Kind name, IrValue *args, llvm::StringRef options,
                           bool statement) {
    return call("ctk_jit_local_operation_v1", builder.getPtrTy(),
                {runtime, string(name), args, string(options),
                 builder.getInt32(statement)},
                true);
  }

  IrValue *batch(const Syntax &node, bool statement) {
    const auto &parts = node.children;
    const bool durable = kind(node) == "durable_batch";
    const auto name = parts[durable ? 2 : 1].text;
    const auto &inputs = parts[durable ? 4 : 3];
    const auto *body = &parts.back();
    llvm::json::Object options;
    IrValue *memory = nullptr;
    IrValue *request = nullptr;
    for (const auto &item : parts) {
      const auto label = kind(item);
      if (!ctk::compat::starts_with(label, "batch_"))
        continue;
      if (label == "batch_size" || label == "batch_count" ||
          label == "batch_jobs") {
        std::uint32_t count = 0;
        const auto text = item.children[1].text;
        const auto end = text.data() + text.size();
        const auto parsed = std::from_chars(text.data(), end, count);
        if (parsed.ec != std::errc{} || parsed.ptr != end || count == 0)
          fail(item, "batch option requires a positive uint32 integer");
        if (!options.try_emplace(std::string(label.substr(6)), count).second)
          fail(item, "batch option repeated");
      } else if (label == "batch_memory") {
        if (memory)
          fail(item, "batch memory repeated");
        memory = expression(item.children[1]);
      } else if (label == "batch_request_id") {
        if (request)
          fail(item, "batch request repeated");
        request = expression(item.children[1]);
      } else if (label == "batch_error_mode") {
        if (!options
                 .try_emplace("continue_on_error",
                              item.children.back().text == "continue")
                 .second)
          fail(item, "batch error mode repeated");
      } else if (label == "batch_progress") {
        if (!options.try_emplace("progress", item.children.back().text == "on")
                 .second)
          fail(item, "batch progress repeated");
      }
    }
    auto *args = collection(0);
    value("add", {args, null(), expression(inputs)});
    value("add", {args, null(), memory ? memory : literal(0)});
    if (durable) {
      options["group_variable"] = std::string(name);
      options["body_source"] = source.slice(body->begin + 1, body->end - 1);
      value("add", {args, null(), request ? request : literal(0)});
    } else {
      const Syntax param{"PROTO_CNAME", name, node.begin, node.begin, {}};
      const Parameter parameter{&param, name, nullptr};
      auto *callback = callable({}, {parameter}, *body);
      value("add", {args, null(), callback});
    }
    return local_operation(
        durable ? "durable_batch" : "batch_statement", args,
        llvm::formatv("{0}", llvm::json::Value(std::move(options))).str(),
        statement);
  }

  IrValue *local_command(const Syntax &node, bool statement) {
    const auto name = kind(node);
    const auto &parts = node.children;
    auto *args = collection(0);
    const auto add = [&](const Syntax &part) {
      value("add", {args, null(), expression(part)});
    };
    std::string options;
    const Syntax *destination = nullptr;
    if (ctk::compat::starts_with(name, "index_")) {
      for (const auto &part : parts)
        if (part.name == "LEGACY_STRING")
          add(part);
      if (name == "index_find") {
        Kind symbol;
        bool exact = false;
        for (const auto &part : parts) {
          if (part.name == "LEGACY_NAME")
            symbol = part.text;
          exact |= part.text == "exact";
        }
        if (!symbol.empty() && symbol != "function" && symbol != "class" &&
            symbol != "variable" && symbol != "alias")
          fail(node, "kind must be function, class, variable, or alias");
        options =
            llvm::formatv(
                "{0}", llvm::json::Value(llvm::json::Object{
                           {"kind", "KIND_" + llvm::StringRef(symbol.empty()
                                                                  ? Kind("any")
                                                                  : symbol)
                                                  .upper()},
                           {"match_mode",
                            exact ? "MATCH_MODE_EXACT" : "MATCH_MODE_PREFIX"},
                           {"unique_symbols", true},
                       }))
                .str();
      }
    } else if (name == "background" || name == "script") {
      for (std::size_t index = 1; index < parts.size(); index += 2)
        add(parts[index]);
    } else if (name == "files_expression") {
      add(parts[1]);
    } else if (name == "file_list") {
      if (parts.size() > 2)
        add(parts.back());
    } else if (name == "file_open" || name == "file_refresh" ||
               name == "session_attach") {
      add(parts[2]);
      if (parts.size() == 5)
        destination = &parts.back();
    } else if (name == "file_close") {
      if (parts[2].text != "all")
        add(parts[2]);
    } else if (name == "cache_prune") {
      options = parts.size() > 2 ? parts[2].text : Kind("memory");
      if (options != "memory" && options != "disk" && options != "all")
        fail(node, "cache prune requires memory, disk or all");
    } else if (name == "cursor_open" || name == "cursor_continue" ||
               name == "cursor_restart") {
      const auto end = name == "cursor_continue" ? 5U : 4U;
      for (std::size_t index = 2; index < end; ++index)
        add(parts[index]);
      llvm::json::Object fields;
      for (std::size_t index = end; index < parts.size(); ++index) {
        const auto &part = parts[index];
        const auto option = kind(part);
        const auto text = part.children[1].text;
        if (option == "cursor_scope") {
          const auto scope = text == "root_only"  ? 1
                             : text == "subtree"  ? 2
                             : text == "children" ? 3
                                                  : 0;
          if (!scope || name != "cursor_continue")
            fail(part, "scope requires cursor continue and root_only, subtree "
                       "or children");
          if (!fields.try_emplace("scope", scope).second)
            fail(part, "duplicate cursor option scope");
        } else {
          const bool row = option == "cursor_row";
          if ((row && name != "cursor_continue") ||
              (!row && name == "cursor_open"))
            fail(part, "cursor option requires an existing cursor");
          std::uint64_t number = 0;
          const auto end = text.data() + text.size();
          const auto parsed = std::from_chars(text.data(), end, number);
          if (parsed.ec != std::errc{} || parsed.ptr != end ||
              (!row && !number))
            fail(part, "cursor row/revision must be an unsigned integer");
          if (!fields
                   .try_emplace(
                       row ? "match_index" : "expected_result_revision", text)
                   .second)
            fail(part, "duplicate cursor row/revision");
        }
      }
      options =
          llvm::formatv("{0}", llvm::json::Value(std::move(fields))).str();
    } else if (name == "file_info" || name == "session_close_retained" ||
               name == "cursor_close" || ctk::compat::starts_with(name, "batch_") ||
               (ctk::compat::starts_with(name, "session_") && name != "session_list")) {
      if (parts.size() > 2)
        add(parts[2]);
    }
    auto *result = local_operation(name, args, options, statement);
    if (destination) {
      const auto &target = destination->children;
      if (target.empty() || target.size() > 2 ||
          (target.size() == 2 && target.front().text != "$"))
        fail(*destination, "target must be a simple variable such as $source");
      define(target.back().text, result);
    }
    return result;
  }

  IrValue *document(const Syntax &node) {
    const auto name = kind(node);
    const auto &parts = node.children;
    if (name == "read_expression" || name == "load_command") {
      const bool loading = name == "load_command";
      auto *path = expression(parts[1]);
      auto *format =
          !loading && parts.size() > 3 ? string(parts[3].text) : null();
      auto *result =
          call("ctk_jit_document_read_v1", builder.getPtrTy(),
               {values, path, format, builder.getInt32(loading)}, true);
      if (loading && parts.size() > 3) {
        const auto &reference = parts[3].children;
        if (reference.empty() || reference.size() > 2 ||
            (reference.size() == 2 && reference.front().text != "$"))
          fail(parts[3], "load destination requires a simple binding name");
        define(reference.back().text, result);
      }
      return result;
    }
    auto *item = expression(parts[1]);
    if (parts.size() < 4)
      return value("print", {item}, 2);
    auto *path = expression(parts[3]);
    if (name == "save_command") {
      auto *format = parts.size() > 5 ? string(parts.back().text) : null();
      return call("ctk_jit_document_save_v1", builder.getPtrTy(),
                  {values, path, item, format}, true);
    }
    return call(
        "ctk_jit_document_print_v1", builder.getPtrTy(),
        {values, item, path, builder.getInt32(parts.back().text == "append")},
        true);
  }

  IrValue *setting(const Syntax &node) {
    const auto name = kind(node);
    const auto &parts = node.children;
    const auto user = ctk::compat::any_of(
        parts, [](const Syntax &item) { return item.text == "user"; });
    const auto append = name == "add_arg";
    Kind key;
    IrValue *operand = null();
    if (name == "clear_command") {
      key = parts.back().text;
    } else if (append) {
      key = "extra_args";
      operand = expression(parts.back());
    } else {
      const auto &setting = parts.back();
      const auto name = kind(setting);
      const auto &arguments = setting.children;
      if (name == "traversal_setting") {
        key = "traversal";
        operand = literal(4, arguments[1].text);
      } else if (name == "args_setting") {
        key = "extra_args";
        operand = expression(arguments[1]);
      } else if (name == "compilation_database_setting") {
        key = "compile_commands";
        operand = expression(arguments[1]);
      } else {
        key = name == "cache_setting"    ? "cache_dir"
              : name == "files_setting"  ? "files"
              : name == "output_setting" ? "output"
                                         : Kind{};
        if (key.empty())
          fail(setting, "unknown CTK setting");
        const bool stdout = arguments[2].text == "stdout";
        operand = stdout ? literal(4, "stdout") : expression(arguments[2]);
        if (key == "output") {
          const bool replace = arguments.back().text == "replace";
          if (stdout && replace)
            fail(setting, "replace mode requires a file destination");
          call("ctk_jit_document_output_v1", builder.getPtrTy(),
               {values, stdout ? null() : operand, builder.getInt32(!replace)},
               true);
        }
      }
    }
    return call("ctk_jit_setting_v1", builder.getPtrTy(),
                {runtime, string(key), operand, builder.getInt32(user),
                 builder.getInt32(append)},
                true);
  }

  IrValue *snippet(const Syntax &node) {
    const auto text = node.children[1].text;
    const auto raw = text.substr(4, text.size() - 5);
    std::string code;
    for (std::size_t index = 0; index < raw.size(); ++index) {
      if (raw[index] == '\\' && index + 1 < raw.size()) {
        const auto next = raw[++index];
        if (next != '`')
          code += '\\';
        code += next;
      } else {
        code += raw[index];
      }
    }
    auto *input = literal(4, code);
    auto *options =
        node.children.size() > 3 ? expression(node.children[3]) : null();
    return call("ctk_jit_parse_cpp_v1", builder.getPtrTy(),
                {runtime, input, options}, true);
  }

  IrValue *method(IrValue *base, Kind name,
                  llvm::ArrayRef<const Syntax *> operands) {
    if (name == "bind" && operands.size() == 1)
      return value("bind_matcher", {base, expression(*operands[0])});
    auto *arguments = collection(0);
    for (const auto *operand : operands)
      if (operand->text != ",")
        value("add", {arguments, null(), expression(*operand)});
    return value("method", {base, string(name), arguments});
  }

  IrValue *mutation(const Syntax &node) {
    const auto name = kind(node);
    const auto &parts = node.children;
    const auto &target = unbox(parts[1]);
    IrValue *base = nullptr;
    IrValue *key = nullptr;
    if (target.name == "legacy_reference" ||
        target.name == "legacy_mutation_target") {
      const auto &accesses = target.children;
      if (accesses.size() < 3)
        fail(target, "collection mutation requires a field or index");
      const bool subscript = accesses.back().text == "]";
      const auto stop = accesses.size() - (subscript ? 3 : 2);
      base = host_reference(target, stop);
      key = subscript ? expression(accesses[stop + 1])
                      : literal(4, accesses.back().text);
    } else {
      auto accesses = terms(target);
      if ((kind(target) != "target" && kind(target) != "postfix") ||
          accesses.size() < 2)
        fail(target, "collection mutation requires a field or index");
      const auto &last = *accesses.pop_back_val();
      base = postfix(target, accesses);
      key = kind(last) == "member_part" || kind(last) == "target_member_part"
                ? literal(4, last.children.back().text)
                : expression(last.children.front());
    }
    if (name == "delete_command") {
      auto *args = collection(0);
      value("add", {args, null(), key});
      return value("method", {base, string("delete"), args});
    }
    value("store", {base, key, expression(parts.back())});
    return base;
  }

  std::uint64_t unsigned_number(const Syntax &value, std::uint64_t minimum,
                                std::uint64_t maximum) {
    std::uint64_t result = 0;
    const auto end = value.text.data() + value.text.size();
    const auto parsed = std::from_chars(value.text.data(), end, result);
    if (parsed.ec != std::errc{} || parsed.ptr != end || result < minimum ||
        result > maximum)
      fail(value,
           llvm::formatv("expected an integer in {0}..{1}", minimum, maximum)
               .str());
    return result;
  }

  IrValue *navigate(const Syntax &node, bool statement) {
    const auto &parts = node.children;
    const auto in = ctk::compat::find_if(
        parts, [](const Syntax &item) { return item.text == "in"; });
    if (in == parts.end())
      fail(node, "navigation requires a source");
    std::optional<std::uint64_t> index;
    const Syntax *filter = nullptr;
    for (auto it = parts.begin() + 2; it != in; ++it) {
      if (it->text == "at") {
        index = unsigned_number(*++it, 0, UINT64_MAX);
      } else {
        filter = &*it;
      }
    }
    const auto end = parts.end() - in;
    if (end > 3)
      fail(node, "duplicate navigation nodes option");
    const auto maximum =
        end == 3 ? unsigned_number((in + 2)->children[1], 0, UINT64_MAX) : 0;
    auto *target = expression(*(in + 1));
    auto *predicate = filter ? expression(*filter) : null();
    return call("ctk_jit_navigate_v1", builder.getPtrTy(),
                {runtime, target, predicate, string(parts[1].text),
                 builder.getInt64(maximum), builder.getInt64(index.value_or(0)),
                 builder.getInt32(index.has_value()),
                 builder.getInt32(kind(node) == "step"),
                 builder.getInt32(statement)},
                true);
  }

  IrValue *analyze(const Syntax &node, bool statement) {
    const auto command = kind(node);
    if (command == "peek" || command == "step")
      return navigate(node, statement);
    if (command == "cfg" || command == "callgraph")
      fail(node, "analysis requires an explicit target");

    const auto &parts = node.children;
    Kind operation = command;
    std::size_t at = 1;
    IrValue *operand = null();
    if (command == "cfg_file" || command == "cfg_binding") {
      operation = "cfg";
      at = command == "cfg_file" ? 3 : 2;
      if (command == "cfg_file") {
        const auto &argument = parts[1];
        if (argument.name == "LEGACY_NAME") {
          operand = literal(4, argument.text);
        } else if (kind(argument) == "qualified_name") {
          std::string name;
          for (const auto &part : argument.children)
            name += part.text;
          operand = literal(4, name);
        } else {
          operand = expression(argument);
        }
      }
    } else if (command == "variable_flow") {
      operand = expression(parts[3]);
    } else if (command == "callgraph_file" || command == "callgraph_binding") {
      operation = "callgraph";
      at = command == "callgraph_file" ? 1 : 2;
    }
    auto *target = expression(parts[at]);
    llvm::json::Object options, projection, cfg;
    bool json_format = false;
    struct Limit {
      Kind form, key;
      std::uint64_t minimum, maximum;
    };
    constexpr Limit limits[] = {
        {"cfg_functions", "max_functions", 1, 1000},
        {"cfg_blocks", "max_blocks", 1, 100000},
        {"cfg_elements", "max_elements", 1, 1000000},
        {"traverse_depth", "max_depth", 0, 256},
        {"traverse_nodes", "max_nodes", 1, 100000},
        {"call_graph_nodes", "max_nodes", 0, UINT64_MAX},
        {"call_graph_edges", "max_edges", 1, 1000000},
        {"call_graph_sites", "max_call_sites", 1, 1000},
        {"call_graph_depth", "max_depth", 0, 32},
        {"flow_blocks", "max_blocks", 0, UINT32_MAX},
        {"flow_events", "max_events", 0, UINT32_MAX},
        {"flow_iterations", "max_iterations", 0, UINT32_MAX},
    };
    constexpr std::pair<Kind, Kind> flags[] = {
        {"traverse_implicit", "visit_implicit_code"},
        {"traverse_instantiations", "visit_template_instantiations"},
        {"call_graph_implicit", "visit_implicit_code"},
        {"call_graph_instantiations", "visit_template_instantiations"},
        {"call_graph_exclude_system", "exclude_system_headers"},
        {"call_graph_strict_node_filter", "strict_node_filter"},
    };
    for (std::size_t i = command == "variable_flow" ? 4 : at + 1;
         i < parts.size(); ++i) {
      const auto &item = parts[i];
      const auto name = kind(item);
      const auto add = [&](llvm::json::Object &into, Kind key,
                           llvm::json::Value value) {
        if (!into.try_emplace(std::string(key), std::move(value)).second)
          fail(item, llvm::Twine("duplicate analysis option ") + key);
      };
      if (name == "graph_json") {
        if (json_format)
          fail(item, "duplicate callgraph output format");
        json_format = true;
        continue;
      }
      if (name == "flow_values") {
        add(options, "value_domain", "INTERVAL");
        continue;
      }
      const auto &field = item.children[1];
      const auto text = field.text;
      if (name == "graph_projection") {
        if (text != "shallow" && text != "recursive")
          fail(field, "projection must be shallow or recursive");
        add(projection, "mode", llvm::StringRef(text).upper());
      } else if (name == "graph_main_file") {
        add(options, "main_file_only", text == "true");
      } else if (name == "graph_payload_depth" ||
                 name == "graph_payload_nodes") {
        const bool depth = name == "graph_payload_depth";
        add(projection, depth ? "max_depth" : "max_nodes",
            unsigned_number(field, 1, depth ? 64 : 100000));
      } else if (const auto limit =
                     ctk::compat::find(limits, name, &Limit::form);
                 limit != std::end(limits)) {
        if (limit->key == "max_depth" && options.get("unlimited_depth"))
          fail(item, "duplicate analysis option max_depth");
        if (name == "call_graph_depth" && text == "all") {
          if (options.get("max_depth"))
            fail(item, "duplicate analysis option max_depth");
          add(options, "unlimited_depth", true);
        } else if (name == "call_graph_nodes" && text == "all") {
          add(options, limit->key, 0);
        } else {
          add(options, limit->key,
              unsigned_number(field, limit->minimum, limit->maximum));
        }
      } else if (const auto flag = ctk::compat::find(
                     flags, name, &std::pair<Kind, Kind>::first);
                 flag != std::end(flags)) {
        add(options, flag->second, text == "true");
      } else if (name == "cfg_build_option") {
        add(cfg, text, item.children[2].text == "true");
      } else if (name == "call_graph_direction") {
        if (text != "in" && text != "out" && text != "both")
          fail(field, "direction must be in, out or both");
        add(options, "direction",
            "CALL_GRAPH_DIRECTION_" + llvm::StringRef(text).upper());
      } else if (name == "call_graph_node_filter") {
        auto matcher = decode_ctk_string(text);
        if (llvm::StringRef(matcher).trim().empty())
          fail(field, "node_filter must be non-empty matcher text");
        add(options, "node_filter", std::move(matcher));
      } else {
        fail(item, llvm::Twine("unsupported analysis option ") + name);
      }
    }
    if (!cfg.empty())
      options["options"] = std::move(cfg);
    if (!projection.empty())
      options["projection"] = std::move(projection);
    auto name = std::string(operation);
    if (json_format)
      name += "_json";
    const auto metadata =
        llvm::formatv("{0}", llvm::json::Value(std::move(options))).str();
    return call("ctk_jit_analyze_v1", builder.getPtrTy(),
                {runtime, string(name), target, operand, string(metadata),
                 builder.getInt32(statement)},
                true);
  }

  IrValue *host(const Syntax &node, bool statement) {
    const auto name = kind(node);
    const auto &children = node.children;
    if (name == "display")
      return expression(children[0]);
    if (name == "reference")
      return host_reference(node);
    if (name == "dict_value") {
      auto *result = collection(2);
      for (const auto &entry : children) {
        if (kind(entry) != "dict_entry")
          continue;
        const auto &key = entry.children.front();
        const auto label = ctk::compat::ends_with(key.name, "STRING")
                               ? decode_ctk_string(key.text)
                               : std::string(key.text);
        value("add",
              {result, literal(4, label), expression(entry.children.back())});
      }
      return result;
    }
    if (name == "nested_qualified_name") {
      std::string text;
      for (const auto &part : children)
        text += part.text;
      return literal(4, text);
    }
    if (name == "list_value") {
      auto *result = collection(0);
      for (const auto &part : children)
        if (part.text != "[" && part.text != "]" && part.text != ",")
          value("add", {result, null(), expression(part)});
      return result;
    }
    constexpr Kind analysis[] = {
        "cfg",           "cfg_file",       "cfg_binding",
        "callgraph",     "callgraph_file", "callgraph_binding",
        "variable_flow", "traverse",       "step",
        "peek"};
    if (ctk::compat::find(analysis, name) != std::end(analysis))
      return analyze(node, statement);
    if (name == "compiled_batch_statement" || name == "durable_batch")
      return batch(node, statement);
    constexpr Kind local[] = {
        "index_list",
        "index_start",
        "index_status",
        "index_rename",
        "index_pause",
        "index_resume",
        "index_cancel",
        "index_find",
        "index_lookup",
        "session_start",
        "session_add",
        "session_match",
        "session_pause",
        "session_resume",
        "session_close",
        "background",
        "batch_status",
        "batch_cancel",
        "batch_resume",
        "batch_retry",
        "batch_promote",
        "files_expression",
        "file_open",
        "file_list",
        "file_info",
        "file_close",
        "file_refresh",
        "resource_status",
        "cursor_open",
        "cursor_continue",
        "cursor_restart",
        "cursor_close",
        "session_list",
        "session_attach",
        "session_close_retained",
        "server_status",
        "cache_status",
        "cache_prune",
        "script",
    };
    if (ctk::compat::find(local, name) != std::end(local))
      return local_command(node, statement);
    if (name == "import_command")
      return call("ctk_jit_import_v1", builder.getPtrTy(),
                  {runtime, expression(children[1])}, true);
    if (name == "history_save" || name == "history_clear" ||
        name == "session_label")
      return call("ctk_jit_history_v1", builder.getPtrTy(),
                  {runtime, string(name.substr(name.find('_') + 1)),
                   children.size() > 2 ? expression(children[2]) : null()},
                  true);
    if (name == "matcher")
      return matcher(node);
    if (name == "parse_expression")
      return call("ctk_jit_parse_v1", builder.getPtrTy(),
                  {runtime, expression(children[1])}, true);
    if (name == "glob_call")
      return call("ctk_jit_glob_v1", builder.getPtrTy(),
                  {values, expression(children[2])}, true);
    if (name == "match") {
      auto *expression_value = expression(children[1]);
      IrValue *target = null();
      Kind scope = "subtree";
      std::size_t index = 2;
      if (index < children.size() && children[index].text == "in") {
        target = expression(children[index + 1]);
        index += 2;
      }
      if (index < children.size() && kind(children[index]) == "match_scope")
        scope = children[index++].children.back().text;
      if (index != children.size()) {
        const auto body = parse_block(children[index + 1]);
        auto *callback = callable({}, {}, body, true);
        auto *result = call("ctk_jit_match_block_v1", builder.getPtrTy(),
                            {runtime, expression_value, target, string(scope),
                             callback, builder.getInt32(statement)},
                            true);
        auto *requested = native("exit_requested", builder.getInt32Ty());
        auto *stop = block("stop");
        auto *proceed = block("proceed");
        builder.CreateCondBr(
            builder.CreateICmpNE(requested, builder.getInt32(0)), stop,
            proceed);
        builder.SetInsertPoint(stop);
        builder.CreateRet(function->getReturnType()->isPointerTy()
                              ? static_cast<IrValue *>(null())
                              : builder.getInt32(0));
        builder.SetInsertPoint(proceed);
        return result;
      }
      auto *rows =
          call("ctk_jit_match_value_v2", builder.getPtrTy(),
               {runtime, expression_value, target, string(scope)}, true);
      if (statement)
        value("print_match", {rows, string("")});
      return rows;
    }
    if (name == "matcher_definition") {
      llvm::SmallVector<Parameter, 8> parameters;
      for (const auto &item : children) {
        if (kind(item) != "parameters")
          continue;
        for (const auto &param : item.children)
          if (param.text != ",")
            parameters.push_back({&param, param.text, nullptr});
      }
      const auto name = children[1].text;
      auto *result = callable(name, parameters, children.back());
      define(name, result);
      return result;
    }
    if (name == "help" || name == "help_shortcut") {
      std::string topic;
      if (name == "help_shortcut") {
        llvm::SmallVector<llvm::StringRef, 8> words;
        llvm::SplitString(children.front().text, words);
        topic = llvm::join(words, " ");
      } else if (children.size() > 1) {
        for (const auto &word : children.back().children) {
          if (!topic.empty())
            topic += ' ';
          topic += word.text;
        }
      }
      auto help = native_help(topic);
      return value("help", {literal(4, help.text), string(help.markdown)});
    }
    if (name == "parse_cpp_expression")
      return snippet(node);
    if (name == "read_expression" || name == "load_command" ||
        name == "save_command" || name == "print")
      return document(node);
    if (name == "set_command" || name == "clear_command" || name == "add_arg")
      return setting(node);
    if (name == "push_command")
      return method(expression(children[1]), "push", {&children.back()});
    if (name == "pop_expression")
      return method(expression(children[1]), "pop", {});
    if (name == "set_item_command" || name == "delete_command")
      return mutation(node);
    if (name == "split_expression" || name == "join_expression" ||
        name == "flatten_expression") {
      auto *arguments = collection(0);
      const bool flatten = name == "flatten_expression";
      for (std::size_t i = flatten ? 2 : 1; i < children.size(); i += 2)
        value("add", {arguments, null(), expression(children[i])});
      const auto operation = flatten                      ? "flatten"
                             : name == "split_expression" ? "split_by"
                                                          : "join";
      return value("call", {string(operation), arguments, collection(2)});
    }
    if (name == "binding_rename" || name == "binding_drop") {
      auto *source = string(children[2].children.back().text);
      auto *target = name == "binding_rename"
                         ? string(children.back().children.back().text)
                         : null();
      return value("change_binding", {source, target});
    }
    if (name == "inspect")
      return value("inspect", {expression(children[1])});
    if (name == "bindings_list")
      return value("print", {value("bindings")}, 2);
    if (name == "quit" || name == "exit")
      return stop();
    fail(node, llvm::Twine("native lowering is unavailable for CTK command ") +
                   node.name);
  }

  IrValue *invocation(Kind name, IrValue *callee, const Syntax *parameters,
                      IrValue *first = nullptr,
                      const Syntax *callback = nullptr) {
    auto *args = collection(0);
    auto *keywords = collection(2);
    if (first)
      value("add", {args, null(), first});
    bool has_keyword = false;
    const auto add_callback = [&] {
      if (callback) {
        value("add", {args, null(), expression(*callback)});
        callback = nullptr;
      }
    };
    llvm::StringMap<bool> seen;
    if (parameters) {
      for (const auto *parameter : terms(*parameters)) {
        if (kind(*parameter) == "keyword_argument" ||
            kind(*parameter) == "natural_labeled_argument") {
          const auto label = parameter->children[0].text;
          if (!seen.try_emplace(label, true).second)
            fail(*parameter, "duplicate keyword argument");
          add_callback();
          has_keyword = true;
          value("add", {keywords, literal(4, label),
                        expression(parameter->children[1])});
        } else {
          if (has_keyword)
            fail(*parameter, "positional arguments must precede keywords");
          value("add", {args, null(), expression(*parameter)});
        }
      }
    }
    add_callback();
    if (callee)
      return value("invoke", {callee, args, keywords});
    if (name == "ctk")
      return call("ctk_jit_eval_v1", builder.getPtrTy(),
                  {runtime, args, keywords}, true);
    return value("call", {string(name), args, keywords});
  }

  IrValue *invoke_stage(const Syntax &stage, IrValue *first = nullptr,
                        const Syntax *callback = nullptr) {
    const auto name = kind(stage);
    const auto args = terms(stage);
    if (name == "reference")
      return invocation(args.back()->text, nullptr, nullptr, first, callback);
    if (name == "named_call")
      return invocation(args.front()->text, nullptr,
                        args.size() > 1 ? args[1] : nullptr, first, callback);
    if (name == "natural_call" || name == "natural_stage") {
      Syntax parameters{"proto_arguments",
                        {},
                        stage.begin,
                        stage.end,
                        {stage.children.begin() + 1, stage.children.end()}};
      return invocation(args.front()->text, nullptr, &parameters, first,
                        callback);
    }
    if (name == "trailing_stage")
      return invoke_stage(*args.front(), first, args.back());
    fail(stage, "invalid native pipeline stage");
  }

  IrValue *pipe(const Children &children) {
    auto *result = expression(*children.front());
    for (std::size_t index = 2; index < children.size(); index += 2)
      result = invoke_stage(*children[index], result);
    return result;
  }

  IrValue *comparison(const Children &children) {
    const auto &left = unbox(*children.front());
    const auto &tail = *children.back();
    const auto parts = terms(tail);
    const auto name = kind(tail);
    if (name == "comparison_tail")
      return binary(parts.front()->text, expression(left), *parts.back());
    const auto op = name.substr(0, name.size() - Kind("_tail").size());
    if (op == "is_defined" || op == "is_not_defined" || op == "is_set" ||
        op == "is_not_set") {
      if (kind(left) != "reference")
        fail(left, "binding predicate requires a reference");
      return value("binding_test",
                   {string(left.children.back().text),
                    builder.getInt32(ctk::compat::ends_with(op, "set")),
                    builder.getInt32(op.find("_not_") != Kind::npos)});
    }
    auto *operand = expression(left);
    auto *argument = op == "is_kind" || op == "is_not_kind"
                         ? literal(4, parts.back()->text)
                         : expression(*parts.back());
    return value("predicate", {string(op), operand, argument});
  }

  IrValue *binary(Kind operation, IrValue *left, const Syntax &right) {
    if (operation != "and" && operation != "or")
      return value("binary", {string(operation), left, expression(right)});
    auto *condition = truth(left);
    auto *start = builder.GetInsertBlock();
    auto *rhs = block("rhs");
    auto *done = block("logic");
    if (operation == "and")
      builder.CreateCondBr(condition, rhs, done);
    else
      builder.CreateCondBr(condition, done, rhs);
    builder.SetInsertPoint(rhs);
    auto *other = expression(right);
    truth(other);
    auto *end = builder.GetInsertBlock();
    builder.CreateBr(done);
    builder.SetInsertPoint(done);
    auto *result = builder.CreatePHI(builder.getPtrTy(), 2);
    result->addIncoming(left, start);
    result->addIncoming(other, end);
    return result;
  }

  IrValue *postfix(const Syntax &node, const Children &children) {
    const auto &base = unbox(*children.front());
    std::size_t start = 1;
    IrValue *result = nullptr;
    if (children.size() > 1 && kind(*children[1]) == "trailing_block_part" &&
        (kind(base) == "reference" || kind(base) == "named_call")) {
      result = invoke_stage(base, nullptr, &children[1]->children.back());
      start = 2;
    } else {
      result = expression(*children.front());
    }
    for (std::size_t i = start; i < children.size(); ++i) {
      const auto &part = *children[i];
      const auto part_kind = kind(part);
      const auto operands = terms(part);
      if (part_kind == "member_part" || part_kind == "target_member_part") {
        auto *hint = i == 1 && kind(base) == "reference"
                         ? string(base.children.back().text)
                         : null();
        result = value("get", {result, string(operands.front()->text), hint});
      } else if (part_kind == "index_expression") {
        result = value("index", {result, expression(*operands.front())});
      } else if (part_kind == "slice_expression") {
        IrValue *bounds[3] = {null(), null(), null()};
        for (std::size_t bound = 0; bound < operands.size(); ++bound) {
          const auto expression_parts = terms(*operands[bound]);
          if (!expression_parts.empty())
            bounds[bound] = expression(*expression_parts.front());
        }
        result = value("slice", {result, bounds[0], bounds[1], bounds[2]});
      } else if (part_kind == "call_suffix") {
        const Syntax *callback = nullptr;
        if (i + 1 < children.size() &&
            kind(*children[i + 1]) == "trailing_block_part")
          callback = &children[++i]->children.back();
        result = invocation({}, result,
                            operands.empty() ? nullptr : operands.front(),
                            nullptr, callback);
      } else if (part_kind == "trailing_block_part") {
        result =
            invocation({}, result, nullptr, nullptr, &part.children.back());
      } else {
        fail(part,
             llvm::Twine("native lowering is unavailable for CTK access ") +
                 part.name);
      }
    }
    return result;
  }

  std::size_t template_end(llvm::StringRef content, std::size_t begin,
                           bool nested) {
    unsigned depth = 1;
    char quote = 0;
    for (auto position = begin; position < content.size(); ++position) {
      const auto character = content[position];
      if (quote) {
        if (character == '\\')
          ++position;
        else if (character == quote)
          quote = 0;
      } else if (character == '\'' || character == '"') {
        quote = character;
      } else if (nested && character == '{') {
        ++depth;
      } else if (character == '}' && --depth == 0) {
        return position;
      }
    }
    return llvm::StringRef::npos;
  }

  IrValue *template_value(const Syntax &literal_node, llvm::StringRef text,
                          bool reference_only) {
    auto parsed = parse_ctk(text);
    if (!parsed)
      fail(literal_node, llvm::toString(parsed.takeError()));
    const auto &program = parsed->children.front().children.front();
    const auto items = terms(program);
    if (items.size() != 1)
      fail(literal_node, "interpolation requires one value expression");
    const auto &item = unbox(*items.front());
    const auto name = kind(item);
    if (name == "let_stmt" || name == "assign_stmt" ||
        name == "runnable_definition" || name == "print_stmt" ||
        name == "host_statement" ||
        (reference_only && name != "reference" && name != "postfix"))
      fail(literal_node, "interpolation requires one value expression");
    auto previous = std::exchange(source, text);
    auto *result = expression(item);
    source = previous;
    return value("render", {result});
  }

  IrValue *string_literal(const Syntax &node) {
    const auto raw = llvm::StringRef(node.text);
    if (raw.front() == '\'')
      return literal(4, decode_ctk_string(node.text));
    constexpr auto escaped = "\xee\x80\x80";
    std::string masked;
    for (std::size_t index = 0; index < raw.size(); ++index) {
      if (raw[index] == '\\' && index + 1 < raw.size()) {
        if (raw[index + 1] == '$') {
          masked += escaped;
          ++index;
          continue;
        }
        masked += raw[index++];
      }
      masked += raw[index];
    }
    const auto decoded = decode_ctk_string(masked);
    const llvm::StringRef content(decoded);
    const bool braces =
        !ctk::compat::contains(raw, '$') && raw.find_first_of("{}") != llvm::StringRef::npos;
    if (!braces && !ctk::compat::contains(content, '$') && !ctk::compat::contains(content, escaped))
      return literal(4, content);
    IrValue *result = nullptr;
    std::string pending;
    const auto append = [&](IrValue *item) {
      result = result ? value("binary", {string("+"), result, item}) : item;
    };
    const auto flush = [&] {
      if (!pending.empty()) {
        append(literal(4, pending));
        pending.clear();
      }
    };
    const auto is_letter = [](char character) {
      return (character >= 'a' && character <= 'z') ||
             (character >= 'A' && character <= 'Z') || character == '_';
    };
    for (std::size_t index = 0; index < content.size();) {
      const auto character = content[index];
      if (ctk::compat::starts_with(content.drop_front(index), escaped)) {
        pending += '$';
        index += 3;
      } else if (braces && (content.substr(index, 2) == "{{" ||
                            content.substr(index, 2) == "}}")) {
        pending += character;
        index += 2;
      } else if ((braces && character == '{') ||
                 (!braces && content.substr(index, 2) == "${")) {
        const auto start = index + (braces ? 1 : 2);
        const auto end = template_end(content, start, braces);
        if (end == llvm::StringRef::npos)
          fail(node, "unclosed interpolation placeholder: expected `}`");
        const auto part = content.slice(start, end).trim();
        if (part.empty())
          fail(node, "empty interpolation expression");
        flush();
        if (braces) {
          append(template_value(node, part, false));
        } else {
          const auto reference = "$" + part.str();
          append(template_value(node, reference, true));
        }
        index = end + 1;
      } else if (!braces && character == '$' && index + 1 < content.size() &&
                 is_letter(content[index + 1])) {
        const auto start = index++;
        while (index < content.size() &&
               (is_letter(content[index]) ||
                (content[index] >= '0' && content[index] <= '9')))
          ++index;
        flush();
        append(template_value(node, content.slice(start, index), true));
      } else {
        if (braces && character == '}')
          fail(node,
               "unexpected `}` in interpolation; use `}}` for a literal brace");
        pending += character;
        ++index;
      }
    }
    flush();
    return result ? result : literal(4);
  }

  IrValue *expression(const Syntax &raw, bool collect = true) {
    const auto &node = unbox(raw);
    const auto name = kind(node);
    const auto children = terms(node);
    if (!node.text.empty()) {
      if (node.name == "PROTO_PREDICATE_STRING")
        return literal(4, decode_ctk_string(node.text));
      if (ctk::compat::ends_with(node.name, "STRING"))
        return string_literal(node);
      if (ctk::compat::ends_with(node.name, "NUMBER") || node.name == "PROTO_INT" ||
          node.name == "PROTO_FLOAT") {
        const bool floating = node.text.find_first_of(".eE") != Kind::npos;
        if (!floating) {
          std::int64_t number = 0;
          const auto end = node.text.data() + node.text.size();
          const auto parsed = std::from_chars(node.text.data(), end, number);
          if (parsed.ec != std::errc{} || parsed.ptr != end)
            fail(node, "integer literal out of range");
        }
        return literal(floating ? 3 : 2, node.text);
      }
      fail(node, llvm::Twine("unexpected CTK token ") + node.name);
    }
    if (name == "repl_start" || name == "start" || name == "single_body" ||
        name == "block_body" || name == "if_else" ||
        name == "single_else_body" || name == "statement_else_body" ||
        name == "block_else_body")
      return children.empty() ? literal(0)
                              : expression(*children.front(), collect);
    if (name == "program" || name == "block_contents")
      return statements(node, false, collect);
    if (name == "empty_program" || name == "null_literal")
      return literal(0);
    if (name == "integer_literal" || name == "float_literal" ||
        name == "string_literal")
      return expression(*children.front());
    if (name == "true_literal" || name == "false_literal" || name == "true" ||
        name == "false")
      return literal(1, ctk::compat::starts_with(name, "true") ? "true" : "false");
    if (name == "reference" && ctk::compat::starts_with(node.name, "proto_"))
      return value("lookup", {string(node.children.back().text)});
    if (name == "postfix" || name == "natural_postfix" ||
        name == "natural_reference_postfix" || name == "target")
      return postfix(node, children);
    if (name == "list_literal" || name == "dict_literal" ||
        name == "tuple_items" || name == "tuple_singleton" ||
        name == "empty_tuple")
      return make_collection(node, children);
    if (name == "print_stmt")
      return value("print", {expression(*children.front())}, 2);
    if (name == "let_stmt") {
      const auto &pattern = *children.front();
      const auto &definition = unbox(*children[1]);
      auto *result =
          kind(definition) == "clause_runnable" &&
                  kind(pattern) == "name_pattern"
              ? clause_runnable(definition, pattern.children.front().text)
              : consumed(*children[1]);
      bind(pattern, result);
      return result;
    }
    if (name == "assign_stmt") {
      auto target = terms(*children[0]);
      const auto op = children[1]->text;
      const bool simple = target.size() == 1;
      IrValue *base = nullptr;
      IrValue *key = nullptr;
      IrValue *old = nullptr;
      if (simple) {
        key = string(target.front()->children.back().text);
        if (op != "=")
          old = value("lookup", {key});
      } else {
        const auto &access = *target.pop_back_val();
        base = postfix(*children[0], target);
        if (kind(access) == "target_member_part")
          key = literal(4, access.children.back().text);
        else if (kind(access) == "index_expression")
          key = expression(*terms(access).front());
        else
          fail(access, "invalid assignment target");
        if (op != "=")
          old = value("index", {base, key});
      }
      auto *right = consumed(*children[2]);
      if (old)
        right =
            value("binary", {string(op.substr(0, op.size() - 1)), old, right});
      return simple ? value("assign", {key, right})
                    : value("store", {base, key, right});
    }
    if (name == "runnable_definition" || name == "inline_runnable")
      return runnable(node, children);
    if (name == "clause_runnable")
      return clause_runnable(node);
    if (name == "named_call")
      return invoke_stage(node);
    if (name == "unary_expr" || name == "not_expr") {
      if (children.front()->text == "-" &&
          kind(*children.back()) == "integer_literal" &&
          children.back()->children.front().text == "9223372036854775808")
        return literal(2, "-9223372036854775808");
      return value("unary", {string(children.front()->text),
                             expression(*children.back())});
    }
    if (name == "additive" || name == "multiplicative" || name == "or_expr" ||
        name == "and_expr") {
      auto *result = expression(*children.front());
      for (std::size_t index = 1; index < children.size(); index += 2)
        result = binary(children[index]->text, result, *children[index + 1]);
      return result;
    }
    if (name == "comparison")
      return comparison(children);
    if (name == "pipe_expr" || name == "recovery_expr") {
      if (kind(*children.back()) != "recovery_tail")
        return pipe(children);
      auto pipeline = children;
      const auto &handler = *pipeline.pop_back_val();
      return with_recovery(
          [&] {
            push();
            auto *result = pipe(pipeline);
            pop();
            return result;
          },
          &handler.children.back());
    }
    if (name == "bare_key")
      return literal(4, children.front()->text);
    if (name == "predicate_string_literal")
      return expression(*children.front());
    if (name == "natural_call" || name == "natural_stage")
      return invoke_stage(node);
    if (name == "if_expr" || name == "unless_expr" || name == "conditional")
      return conditional(node, children);
    if (name == "foreach_expr")
      return for_each(children);
    if (name == "while_expr" || name == "repeat_expr")
      return condition_loop(children, name == "repeat_expr", collect);
    if (name == "break_stmt" || name == "continue_stmt")
      return flow(node, name == "break_stmt");
    if (name == "block") {
      push();
      auto *result = children.empty() ? literal(0)
                                      : expression(*children.front(), collect);
      pop();
      return result;
    }
    if (name == "host_expression" || name == "host_statement") {
      const auto &root = *children.front();
      if (kind(root) == "reference" && children.size() > 1) {
        auto reference = root;
        for (const auto *child : llvm::ArrayRef(children).drop_front())
          reference.children.push_back(*child);
        return host_reference(reference);
      }
      return host(root, name == "host_statement");
    }
    if (name == "matcher" || name == "display" || name == "glob_call" ||
        name == "list_value" || name == "dict_value" ||
        name == "nested_qualified_name" || name == "reference")
      return host(node, false);
    fail(node, llvm::Twine("native lowering is unavailable for CTK syntax ") +
                   node.name);
  }

  llvm::StringRef source;
  llvm::LLVMContext context;
  llvm::Module module;
  llvm::IRBuilder<> builder;
  llvm::Function *function = nullptr;
  llvm::BasicBlock *error = nullptr;
  IrValue *runtime = nullptr;
  IrValue *values = nullptr;
  llvm::StringMap<IrValue *> strings;
  llvm::SmallVector<Loop, 4> loops;
  llvm::SmallVector<Cleanup, 4> cleanups;
  std::int64_t scope_depth = 0;
  std::int64_t consume_depth = 0;
};

} // namespace

llvm::Expected<std::string> lower_ctk(llvm::StringRef source, bool display,
                                      llvm::StringRef path, bool library) {
  auto parsed = parse_ctk(source);
  if (!parsed)
    return parsed.takeError();
  const Syntax *program = &*parsed;
  while (kind(*program) == "repl_start" || kind(*program) == "start") {
    if (program->children.empty())
      break;
    program = &program->children.front();
  }
  try {
    return Lowering(source).lower(*program, display, path, library);
  } catch (const std::exception &error) {
    return llvm::createStringError(llvm::inconvertibleErrorCode(), "%s",
                                   error.what());
  }
}

} // namespace ctk::jit
