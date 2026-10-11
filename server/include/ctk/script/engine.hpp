#pragma once
#include "ctk/script/environment.hpp"
#include "ctk/script/limits.hpp"
#include "ctk/script/result.hpp"
#include <functional>
#include <map>
#include <utility>
namespace ctk::script {
using ExportSink =
    std::function<std::pair<ctk::clang_layer::MatchCode, std::string>(
        const std::string &, const ctk::analysis::v1::ScriptValue &,
        const std::string &)>;
class Engine {
public:
  bool contains_batch(const std::string &source) const;
  Result run(
      const std::string &source, Environment *environment = nullptr,
      Limits limits = {},
      const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint =
          [] { return true; },
      const std::map<std::string, ctk::analysis::v1::ScriptValue>
          &initial_values = {},
      ExportSink export_sink = {}, bool collect_final = false);
  std::string eval(const std::string &source);
};
} // namespace ctk::script
