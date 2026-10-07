#pragma once
#include "ctk/clang/call_graph_limits.hpp"
#include "ctk/clang/matching.hpp"
#include <stdexcept>
namespace ctk::clang_layer::calls {
struct CallGraphFailure : std::runtime_error {
  MatchCode code;
  CallGraphFailure(MatchCode c, const char *message)
      : std::runtime_error(message), code(c) {}
};
struct CallGraphBudget {
  IMatchBackend::Checkpoint checkpoint;
  CallGraphLimits limits;
  std::size_t edges = 0, bytes = 0;
  void check() const {
    if (!checkpoint())
      throw CallGraphFailure(MatchCode::Cancelled, "call graph cancelled");
  }
  void add_bytes(std::size_t amount) {
    check();
    if (amount > limits.max_bytes - bytes)
      throw CallGraphFailure(MatchCode::ResourceExhausted,
                             "call graph byte limit exceeded");
    bytes += amount;
  }
};
} // namespace ctk::clang_layer::calls
