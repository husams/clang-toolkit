#pragma once
#include "ctk/clang/cfg_limits.hpp"
#include "ctk/clang/matching.hpp"
#include <stdexcept>
namespace ctk::clang_layer::control_flow {
struct BuildFailure : std::runtime_error {
  MatchCode code;
  BuildFailure(MatchCode c, const char *m) : std::runtime_error(m), code(c) {}
};
struct CfgBudget {
  IMatchBackend::Checkpoint checkpoint;
  CfgLimits limits;
  std::size_t blocks = 0, elements = 0, bytes = 0;
  void check() const {
    if (!checkpoint())
      throw BuildFailure(MatchCode::Cancelled, "CFG analysis cancelled");
  }
  void add_bytes(std::size_t amount) {
    check();
    if (amount > limits.max_bytes - bytes)
      throw BuildFailure(MatchCode::ResourceExhausted,
                         "CFG response byte limit exceeded");
    bytes += amount;
  }
};
} // namespace ctk::clang_layer::control_flow
