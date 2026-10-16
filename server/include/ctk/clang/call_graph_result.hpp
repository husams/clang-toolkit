#pragma once
#include "analysis/v1/call_graph_response.pb.h"
#include "analysis/v1/call_graph_stream.pb.h"
#include "ctk/clang/matching.hpp"
namespace ctk::clang_layer {
struct CallGraphResult {
  MatchCode code{MatchCode::Ok};
  std::string message;
  ctk::analysis::v1::CallGraphResponse response;
};
struct CallGraphStreamResult {
  MatchCode code{MatchCode::Ok};
  std::string message;
  ctk::analysis::v1::CallGraphCompleted completed;
};
} // namespace ctk::clang_layer
