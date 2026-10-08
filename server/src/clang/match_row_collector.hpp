#pragma once

#include "captured_binding_state.hpp"
#include <clang/ASTMatchers/ASTMatchFinder.h>
#include <optional>

namespace ctk::clang_layer {
using clang::ast_matchers::MatchFinder;
using ctk::match::v1::MatchResult;
class RowCollector final : public MatchFinder::MatchCallback {
public:
  RowCollector(MatchExecution &result, CapturedBindingState &state,
               const IMatchBackend::Checkpoint &checkpoint,
               const MatchLimits &limits,
               const IMatchBackend::RowSink *sink = nullptr);
  std::optional<std::uint64_t> source_row;
  void run(const MatchFinder::MatchResult &found) override;

private:
  MatchExecution &result_;
  CapturedBindingState &state_;
  const IMatchBackend::Checkpoint &checkpoint_;
  const MatchLimits &limits_;
  const IMatchBackend::RowSink *sink_;
  std::size_t bytes_{};
};

} // namespace ctk::clang_layer
