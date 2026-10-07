#pragma once
#include "ctk/application/match_controller.hpp"
#include "ctk/clang/cfg_backend.hpp"

namespace ctk::application {
class CfgController final {
public:
  explicit CfgController(
      CursorSettings settings = {},
      std::shared_ptr<ctk::clang_layer::ICfgBackend> backend = {},
      std::shared_ptr<OperationExecutor> executor = {});
  ~CfgController();
  ctk::clang_layer::CfgResult
  build(const ctk::analysis::v1::CfgRequest &,
        const ctk::clang_layer::IMatchBackend::Checkpoint &);
  void stop_admission();

private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};
} // namespace ctk::application
