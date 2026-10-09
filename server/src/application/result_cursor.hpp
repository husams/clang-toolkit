#pragma once

#include "ctk/application/match_controller.hpp"
#include <mutex>

namespace ctk::application::detail {
struct ResultCursor {
  std::mutex operation;
  std::string owner, id, file_path;
  bool closed{false};
  std::chrono::steady_clock::time_point deadline;
  std::shared_ptr<const ctk::clang_layer::NativeBindingState> state;
  ctk::match::v1::MatchResponse response;
};
} // namespace ctk::application::detail
