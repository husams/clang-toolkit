#include "ctk/application/traversal_controller.hpp"
#include "file_target_validation.hpp"
#include "query_executor.hpp"
#include "resource_scope_guard.hpp"
#include <future>

namespace ctk::application {
using ctk::clang_layer::MatchCode;
using ctk::clang_layer::TraversalResult;
struct TraversalController::Impl {
  std::shared_ptr<ctk::clang_layer::ITraversalBackend> backend;
  ctk::clang_layer::TraversalLimits limits;
  std::shared_ptr<OperationExecutor> executor;
  std::shared_ptr<ResourceManager> resources;
  Impl(CursorSettings settings,
       std::shared_ptr<ctk::clang_layer::ITraversalBackend> native,
       std::shared_ptr<OperationExecutor> work)
      : backend(std::move(native)), resources(settings.resources),
        limits{100000, settings.results.max_bytes},
        executor(work ? std::move(work)
                      : make_operation_executor(settings.workers,
                                                settings.pending_requests)) {}
};
TraversalController::TraversalController(
    CursorSettings settings,
    std::shared_ptr<ctk::clang_layer::ITraversalBackend> backend,
    std::shared_ptr<OperationExecutor> executor) {
  if (settings.results.max_bytes == 0)
    throw std::invalid_argument("traversal byte limit must be positive");
#ifdef CTK_WITH_CLANG
  if (!backend)
    backend = ctk::clang_layer::make_traversal_backend();
#endif
  impl_ =
      std::make_unique<Impl>(settings, std::move(backend), std::move(executor));
}
TraversalController::~TraversalController() = default;
TraversalResult TraversalController::traverse(
    const ctk::analysis::v1::TraverseRequest &request,
    const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint,
    const std::string &owner) {
  const auto invalid = detail::invalid_file_target(request.file());
  if (!request.has_file() || !invalid.empty())
    return {MatchCode::InvalidArgument,
            invalid.empty() ? "file target is required" : invalid,
            {}};
  if ((request.has_max_nodes() &&
       (request.max_nodes() == 0 ||
        request.max_nodes() > impl_->limits.max_nodes)) ||
      (request.has_max_depth() && request.max_depth() > 256))
    return {MatchCode::InvalidArgument,
            "max_nodes must be 1..100000; max_depth must be 0..256",
            {}};
  if (!impl_->backend)
    return {MatchCode::FailedPrecondition, "Clang analysis is disabled", {}};
  auto work = std::make_shared<ResourceManager::WorkLease>();
  if (impl_->resources) {
    std::string message;
    const auto code = impl_->resources->begin_work(
        owner, request.resource_scope_id(), *work, message);
    if (code != MatchCode::Ok)
      return {code, std::move(message), {}};
  }
  const auto scoped_checkpoint = [checkpoint, work] {
    return (!checkpoint || checkpoint()) && work->checkpoint();
  };
  auto promise = std::make_shared<std::promise<TraversalResult>>();
  auto future = promise->get_future();
  if (!impl_->executor->enqueue([this, promise, request, scoped_checkpoint,
                                 owner, work] {
        try {
          auto resource_scope = detail::make_snapshot_scope(
              impl_->resources, owner, request.resource_scope_id(),
              work->token());
          auto result =
              impl_->backend->traverse(request, scoped_checkpoint, impl_->limits);
          if (result.code == MatchCode::Ok && !scoped_checkpoint())
            result = {MatchCode::Cancelled,
                      "AST traversal cancelled before publication",
                      {}};
          promise->set_value(std::move(result));
        } catch (const std::exception &error) {
          promise->set_value({MatchCode::Internal, error.what(), {}});
        } catch (...) {
          promise->set_value({MatchCode::Internal, "AST traversal failed", {}});
        }
      }))
    return {MatchCode::ResourceExhausted,
            "traversal executor queue is full or stopped",
            {}};
  return future.get();
}
void TraversalController::stop_admission() {
  impl_->executor->stop_admission();
}
} // namespace ctk::application
