#pragma once
#include "ctk/clang/matching.hpp"
#include <stdexcept>
namespace ctk::script {
class Error final : public std::runtime_error {
public:
  Error(ctk::clang_layer::MatchCode status, const std::string &message)
      : std::runtime_error(message), code(status) {}
  const ctk::clang_layer::MatchCode code;
};
} // namespace ctk::script
