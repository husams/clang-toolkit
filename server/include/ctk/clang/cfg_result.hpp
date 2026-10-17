#pragma once
#include "analysis/v1/cfg_response.pb.h"
#include "ctk/clang/matching.hpp"
#include <cstdint>
namespace ctk::clang_layer {
struct CfgResult {
  MatchCode code{MatchCode::Ok};
  std::string message;
  ctk::analysis::v1::CfgResponse response;
  std::uint64_t graph_count{}, block_count{}, element_count{};
};
} // namespace ctk::clang_layer
