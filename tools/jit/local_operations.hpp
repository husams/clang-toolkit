#pragma once

#include "values.hpp"

#include <llvm/Support/Error.h>

namespace ctk::application {
class MatchController;
class ScriptController;
} // namespace ctk::application

namespace ctk::clang_layer {
class IQueryEngine;
}

namespace ctk::jit {

class LocalOperations {
public:
  explicit LocalOperations(llvm::StringRef database);
  ~LocalOperations();

  const Value* execute(Values& runtime, llvm::StringRef command, const Sequence& arguments,
                       llvm::StringRef options, bool display);
  bool is_target(const Value& value) const;
  llvm::Expected<AstHandle> target(const Value& value);

private:
  application::MatchController& controller();

  std::string database_;
  std::shared_ptr<clang_layer::IQueryEngine> engine_;
  std::unique_ptr<application::MatchController> controller_;
  std::unique_ptr<application::ScriptController> script_;
};

} // namespace ctk::jit
