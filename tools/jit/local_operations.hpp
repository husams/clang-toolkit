#pragma once

#include "values.hpp"

#include <functional>

#include <llvm/Support/Error.h>

namespace ctk::application {
class MatchController;
} // namespace ctk::application

namespace ctk::clang_layer {
class IQueryEngine;
}

namespace ctk::jit {

class EmbeddedServices;
struct TargetRequest;

class LocalOperations {
public:
  explicit LocalOperations(const LocalState& settings);
  ~LocalOperations();
  void set_events(std::function<void(std::string)> events);
  void finish();
  bool scoped() const { return static_cast<bool>(scope_); }
  bool accepts(const AstHandle& ast) const;
  Value scoped_inputs() const;
  llvm::Expected<AstHandle> target_path(llvm::StringRef path);
  llvm::Expected<AstHandle> parse_snippet(const TargetRequest& target, llvm::StringRef source,
                                          const std::vector<std::string>& includes,
                                          bool translation_unit);

  const Value* execute(Values& runtime, llvm::StringRef command, const Sequence& arguments,
                       llvm::StringRef options, bool display);
  bool is_target(const Value& value) const;
  llvm::Expected<AstHandle> target(const Value& value);

private:
  application::MatchController& controller();
  EmbeddedServices& embedded();
  struct BatchScope;
  const Value* foreground_batch(Values& runtime, const Sequence& args, llvm::StringRef options,
                                bool display);

  const LocalState& settings_;
  std::shared_ptr<clang_layer::IQueryEngine> engine_;
  std::unique_ptr<application::MatchController> controller_;
  std::function<void(std::string)> events_;
  std::unique_ptr<EmbeddedServices> embedded_;
  std::unique_ptr<BatchScope> scope_;
};

} // namespace ctk::jit
