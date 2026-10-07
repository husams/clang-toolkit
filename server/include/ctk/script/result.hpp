#pragma once
#include "analysis/v1/script_response.pb.h"
#include "ctk/clang/matching.hpp"
namespace ctk::script {
struct Result {
  ctk::clang_layer::MatchCode code = ctk::clang_layer::MatchCode::Ok;
  std::string message;
  ctk::analysis::v1::ScriptResponse response;
};
} // namespace ctk::script
