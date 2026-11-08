#pragma once

#include <cstdint>
#include <deque>
#include <memory>
#include <optional>
#include <string>
#include <variant>
#include <vector>

#include <llvm/ADT/StringMap.h>

namespace clang {
class ASTContext;
class DynTypedNode;
} // namespace clang

namespace llvm {
class Error;
class Twine;
} // namespace llvm

namespace llvm::orc {
class LLJIT;
}

namespace ctk::jit {

struct Sequence;
struct Record;
struct Runnable;
struct SemanticValue;

struct SemanticEnum {
  std::string name;
  std::int64_t number;
};
using AstHandle = std::shared_ptr<clang::ASTContext>;

struct NativeNode {
  AstHandle ast;
  std::shared_ptr<clang::DynTypedNode> node;
  mutable std::shared_ptr<SemanticValue> semantic;
  std::shared_ptr<clang::DynTypedNode> parent;
  std::string binding_name;
};

struct BuiltinFunction {
  std::string name;
};

struct MatcherValue {
  std::string text;
  std::string name;
  std::shared_ptr<const Sequence> arguments;
  std::optional<std::string> binding;
};

MatcherValue matcher_value(llvm::StringRef name, const Sequence& arguments,
                           std::optional<std::string> binding);

struct Value {
  using Data = std::variant<std::monostate, bool, std::int64_t, double, std::string,
                            std::shared_ptr<Sequence>, std::shared_ptr<Record>, AstHandle,
                            std::shared_ptr<NativeNode>, MatcherValue, std::shared_ptr<Runnable>,
                            BuiltinFunction, std::shared_ptr<SemanticValue>, SemanticEnum>;

  Data data;
};

struct Sequence {
  std::vector<Value> items;
  bool tuple = false;
};

struct Record {
  // CTK records iterate in insertion order.
  std::vector<std::string> keys;
  llvm::StringMap<Value> fields;
  void set(llvm::StringRef key, Value value);
};

using Bindings = llvm::StringMap<Value>;

struct Scope {
  Bindings bindings;
  llvm::StringMap<std::int64_t> ordinals;
};

struct Values;
using RunnableEntry = const Value* (*)(void*, Values*, const Value*, const Value*);

struct Runnable {
  std::string name;
  RunnableEntry entry;
  std::size_t minimum;
  std::size_t maximum;
  std::string source_path;
  std::vector<Scope> captured;
  std::shared_ptr<void> code;
};

struct LocalState {
  std::string output_path;
  std::string default_database;
  std::string compilation_database;
  std::vector<std::string> compilation_arguments;
  Value default_targets;
  bool spelled_only = false;
  std::optional<std::size_t> batch_output_bytes;
  std::size_t successful_exports = 0;
};

struct Values {
  Values(void* context, Bindings& globals, LocalState& state, std::string& output,
         std::string& error)
      : context(context)
      , globals(globals)
      , state(state)
      , output(output)
      , error(error) {}

  const Value* hold(Value value);
  const Value* fail(const llvm::Twine& message);
  Value* lookup(llvm::StringRef name);
  Bindings& local();
  void push();
  void pop();
  bool tick();

  void* context;
  Bindings& globals;
  LocalState& state;
  std::string& output;
  std::string& error;
  std::deque<Value> temporaries;
  std::vector<Scope> scopes;
  std::shared_ptr<void> code;
  std::size_t steps = 0;
  std::size_t consume_depth = 0;
  std::size_t emissions = 0;
  const Value* last_printed = nullptr;
  const Value* result = nullptr;
  std::string source_path;
  std::size_t call_depth = 0;
  std::size_t frame_depth = 0;
  bool fatal = false;
  bool exit_requested = false;
};

llvm::Error expose_values(llvm::orc::LLJIT& jit);

} // namespace ctk::jit
