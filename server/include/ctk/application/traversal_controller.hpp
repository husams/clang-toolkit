#pragma once
#include "ctk/application/match_controller.hpp"
#include "ctk/clang/traversal_backend.hpp"

namespace ctk::application {
class TraversalController final {
public:
  explicit TraversalController(
      CursorSettings settings = {},
      std::shared_ptr<ctk::clang_layer::ITraversalBackend> backend = {},
      std::shared_ptr<OperationExecutor> executor = {});
  ~TraversalController();
  ctk::clang_layer::TraversalResult
  traverse(const ctk::analysis::v1::TraverseRequest &,
           const ctk::clang_layer::IMatchBackend::Checkpoint &);
  void stop_admission();

private:
  struct Impl;
  std::unique_ptr<Impl> impl_;
};
} // namespace ctk::application
