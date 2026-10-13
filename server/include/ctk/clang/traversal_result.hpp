#pragma once
#include "analysis/v1/traverse_response.pb.h"
#include "ctk/clang/matching.hpp"

namespace ctk::clang_layer {
struct TraversalResult {
  MatchCode code{MatchCode::Ok};
  std::string message;
  ctk::analysis::v1::TraverseResponse response;
  std::uint64_t node_count{};
};
} // namespace ctk::clang_layer
