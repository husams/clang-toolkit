#pragma once
#include "analysis/v1/script_request.pb.h"
#include "ctk/application/match_controller.hpp"
#include "ctk/script/engine.hpp"
namespace ctk::application {
class ScriptController final {
public:
  explicit ScriptController(
      CursorSettings settings = {},
      std::shared_ptr<ctk::clang_layer::IQueryEngine> engine = {},
      std::shared_ptr<OperationExecutor> executor = {});
  ctk::script::Result run(const ctk::analysis::v1::ScriptRequest &,
                          const ctk::clang_layer::IMatchBackend::Checkpoint &);

private:
  CursorSettings settings_;
  std::shared_ptr<ctk::clang_layer::IQueryEngine> engine_;
  std::shared_ptr<OperationExecutor> executor_;
};
} // namespace ctk::application
