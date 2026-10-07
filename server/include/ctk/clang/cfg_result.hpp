#pragma once
#include "analysis/v1/cfg_response.pb.h"
#include "ctk/clang/matching.hpp"
namespace ctk::clang_layer {
struct CfgResult {
  MatchCode code{MatchCode::Ok};
  std::string message;
  ctk::analysis::v1::CfgResponse response;
};
} // namespace ctk::clang_layer
