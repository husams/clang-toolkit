#include "ctk/application/call_graph_controller.hpp"
#include "file_target_validation.hpp"
#include "query_executor.hpp"
#include <future>

namespace ctk::application {
using ctk::clang_layer::CallGraphResult;
using ctk::clang_layer::MatchCode;
struct CallGraphController::Impl {
  std::shared_ptr<ctk::clang_layer::ICallGraphBackend> backend;
  ctk::clang_layer::CallGraphLimits limits;
  std::shared_ptr<OperationExecutor> executor;
  Impl(CursorSettings settings,
       std::shared_ptr<ctk::clang_layer::ICallGraphBackend> native,
       std::shared_ptr<OperationExecutor> work)
      : backend(std::move(native)),
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
    const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint) {
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
  auto promise = std::make_shared<std::promise<CallGraphResult>>();
  auto future = promise->get_future();
  if (!impl_->executor->enqueue([this, promise, request, checkpoint] {
        try {
          auto result =
              impl_->backend->build(request, checkpoint, impl_->limits);
          if (result.code == MatchCode::Ok && !checkpoint())
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
