#pragma once
#include "ctk/application/match_controller.hpp"
#include "ctk/clang/call_graph_backend.hpp"

namespace ctk::application {
class CallGraphController final {
public:
  explicit CallGraphController(
      CursorSettings settings = {},
      std::shared_ptr<ctk::clang_layer::ICallGraphBackend> backend = {},
      std::shared_ptr<OperationExecutor> executor = {});
  ~CallGraphController();
  ctk::clang_layer::CallGraphResult
  build(const ctk::analysis::v1::CallGraphRequest &,
        const ctk::clang_layer::IMatchBackend::Checkpoint &);
  void stop_admission();

private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};
} // namespace ctk::application
