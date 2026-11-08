#pragma once

#include <cstdint>
#include <deque>
#include <memory>
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
using AstHandle = std::shared_ptr<clang::ASTContext>;

struct NativeNode {
  AstHandle ast;
  std::shared_ptr<clang::DynTypedNode> node;
};

struct MatcherValue {
  std::string text;
};

struct Value {
  using Data = std::variant<std::monostate, bool, std::int64_t, double, std::string,
                            std::shared_ptr<Sequence>, std::shared_ptr<Record>, AstHandle,
                            std::shared_ptr<NativeNode>, MatcherValue, std::shared_ptr<Runnable>>;

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
  std::vector<Scope> captured;
  std::shared_ptr<void> code;
};

struct Values {
  Values(void* context, Bindings& globals, std::string& output, std::string& error)
      : context(context)
      , globals(globals)
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
  std::string& output;
  std::string& error;
  std::deque<Value> temporaries;
  std::vector<Scope> scopes;
  std::shared_ptr<void> code;
  std::size_t steps = 0;
  std::size_t call_depth = 0;
  std::size_t frame_depth = 0;
  bool fatal = false;
};

llvm::Error expose_values(llvm::orc::LLJIT& jit);

} // namespace ctk::jit
