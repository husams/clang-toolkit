#pragma once
#include "ctk/script/engine.hpp"
#include "program.hpp"
namespace ctk::script::detail {
class Interpreter final {
public:
  Interpreter(Environment *environment, Limits limits,
              const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint);
  ctk::analysis::v1::ScriptResponse run(const Program &program);

private:
  void tick();
  Value evaluate(const Expression &expression);
  void statements(const std::vector<Statement> &body);
  void retain(const Value &value);
  Value row(const Value &value, std::size_t index);
  Value scoped(const ScopedBlock &block);
  Environment *environment_;
  Limits limits_;
  ctk::clang_layer::IMatchBackend::Checkpoint checkpoint_;
  ctk::analysis::v1::ScriptResponse response_;
  std::vector<std::map<std::string, Value>> scopes_;
  std::vector<Value> default_trees_;
  std::vector<std::weak_ptr<const ctk::analysis::v1::ScriptValue>> values_;
  std::vector<std::weak_ptr<const ctk::clang_layer::NativeBindingState>>
      bindings_;
  std::vector<std::weak_ptr<const std::vector<std::size_t>>> rows_;
};
} // namespace ctk::script::detail
