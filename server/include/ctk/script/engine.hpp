#pragma once
#include "ctk/script/environment.hpp"
#include "ctk/script/limits.hpp"
#include "ctk/script/result.hpp"
namespace ctk::script {
class Engine {
public:
  Result run(
      const std::string &source, Environment *environment = nullptr,
      Limits limits = {},
      const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint = [] {
        return true;
      });
  std::string eval(const std::string &source);
};
} // namespace ctk::script
