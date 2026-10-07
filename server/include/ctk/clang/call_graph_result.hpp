#pragma once
#include "analysis/v1/call_graph_response.pb.h"
#include "ctk/clang/matching.hpp"
namespace ctk::clang_layer {
struct CallGraphResult {
  MatchCode code{MatchCode::Ok};
  std::string message;
  ctk::analysis::v1::CallGraphResponse response;
};
} // namespace ctk::clang_layer
