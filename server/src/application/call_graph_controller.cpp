#include "ctk/application/call_graph_controller.hpp"
#include "file_target_validation.hpp"
#include "query_executor.hpp"
#include "resource_scope_guard.hpp"
#include <future>

namespace ctk::application {
using ctk::clang_layer::CallGraphResult;
using ctk::clang_layer::MatchCode;
struct CallGraphController::Impl {
  std::shared_ptr<ctk::clang_layer::ICallGraphBackend> backend;
  ctk::clang_layer::CallGraphLimits limits;
  std::shared_ptr<OperationExecutor> executor;
  std::shared_ptr<ResourceManager> resources;
  Impl(CursorSettings settings,
       std::shared_ptr<ctk::clang_layer::ICallGraphBackend> native,
       std::shared_ptr<OperationExecutor> work)
      : backend(std::move(native)), resources(settings.resources),
        limits{100000, 1000000, settings.results.max_bytes},
        executor(work ? std::move(work)
                      : make_operation_executor(settings.workers,
                                                settings.pending_requests)) {}
};
CallGraphController::CallGraphController(
    CursorSettings settings,
    std::shared_ptr<ctk::clang_layer::ICallGraphBackend> backend,
    std::shared_ptr<OperationExecutor> executor) {
  if (settings.results.max_bytes == 0)
    throw std::invalid_argument("call graph byte limit must be positive");
#ifdef CTK_WITH_CLANG
  if (!backend)
    backend = ctk::clang_layer::make_call_graph_backend();
#endif
  impl_ =
      std::make_unique<Impl>(settings, std::move(backend), std::move(executor));
}
CallGraphController::~CallGraphController() = default;
CallGraphResult CallGraphController::build(
    const ctk::analysis::v1::CallGraphRequest &request,
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
      (request.has_max_edges() &&
       (request.max_edges() == 0 ||
        request.max_edges() > impl_->limits.max_edges)))
    return {MatchCode::InvalidArgument,
            "call graph limits must be positive and within server bounds",
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
  auto promise = std::make_shared<std::promise<CallGraphResult>>();
  auto future = promise->get_future();
  if (!impl_->executor->enqueue([this, promise, request, scoped_checkpoint,
                                 owner, work] {
        try {
          auto resource_scope = detail::make_snapshot_scope(
              impl_->resources, owner, request.resource_scope_id(),
              work->token());
          auto result =
              impl_->backend->build(request, scoped_checkpoint, impl_->limits);
          if (result.code == MatchCode::Ok && !scoped_checkpoint())
            result = {MatchCode::Cancelled,
                      "call graph analysis cancelled before publication",
                      {}};
          promise->set_value(std::move(result));
        } catch (const std::exception &error) {
          promise->set_value({MatchCode::Internal, error.what(), {}});
        } catch (...) {
          promise->set_value(
              {MatchCode::Internal, "call graph analysis failed", {}});
        }
      }))
    return {MatchCode::ResourceExhausted,
            "call graph executor queue is full or stopped",
            {}};
  return future.get();
}
void CallGraphController::stop_admission() {
  impl_->executor->stop_admission();
}
} // namespace ctk::application
