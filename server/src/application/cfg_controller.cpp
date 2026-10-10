#include "ctk/application/cfg_controller.hpp"
#include "file_target_validation.hpp"
#include "query_executor.hpp"
#include "resource_scope_guard.hpp"
#include <future>

namespace ctk::application {
using ctk::clang_layer::CfgResult;
using ctk::clang_layer::MatchCode;
struct CfgController::Impl {
  std::shared_ptr<ctk::clang_layer::ICfgBackend> backend;
  ctk::clang_layer::CfgLimits limits;
  std::shared_ptr<OperationExecutor> executor;
  std::shared_ptr<ResourceManager> resources;
  Impl(CursorSettings settings,
       std::shared_ptr<ctk::clang_layer::ICfgBackend> native,
       std::shared_ptr<OperationExecutor> work)
      : backend(std::move(native)), resources(settings.resources),
        limits{1000, 100000, 1000000, settings.results.max_bytes},
        executor(work ? std::move(work)
                      : make_operation_executor(settings.workers,
                                                settings.pending_requests)) {}
};
CfgController::CfgController(
    CursorSettings settings,
    std::shared_ptr<ctk::clang_layer::ICfgBackend> backend,
    std::shared_ptr<OperationExecutor> executor) {
  if (settings.results.max_bytes == 0)
    throw std::invalid_argument("CFG byte limit must be positive");
#ifdef CTK_WITH_CLANG
  if (!backend)
    backend = ctk::clang_layer::make_cfg_backend();
#endif
  impl_ =
      std::make_unique<Impl>(settings, std::move(backend), std::move(executor));
}
CfgController::~CfgController() = default;
CfgResult CfgController::build(
    const ctk::analysis::v1::CfgRequest &request,
    const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint,
    const std::string &owner) {
  const auto invalid = detail::invalid_file_target(request.file());
  if (!request.has_file() || !invalid.empty())
    return {MatchCode::InvalidArgument,
            invalid.empty() ? "file target is required" : invalid,
            {}};
  if (request.function().empty())
    return {MatchCode::InvalidArgument, "function name is required", {}};
  if ((request.has_max_functions() &&
       (request.max_functions() == 0 ||
        request.max_functions() > impl_->limits.max_functions)) ||
      (request.has_max_blocks() &&
       (request.max_blocks() == 0 ||
        request.max_blocks() > impl_->limits.max_blocks)) ||
      (request.has_max_elements() &&
       (request.max_elements() == 0 ||
        request.max_elements() > impl_->limits.max_elements)))
    return {MatchCode::InvalidArgument,
            "CFG limits must be positive and within server bounds",
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
  auto promise = std::make_shared<std::promise<CfgResult>>();
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
                      "CFG analysis cancelled before publication",
                      {}};
          promise->set_value(std::move(result));
        } catch (const std::exception &error) {
          promise->set_value({MatchCode::Internal, error.what(), {}});
        } catch (...) {
          promise->set_value({MatchCode::Internal, "CFG analysis failed", {}});
        }
      }))
    return {MatchCode::ResourceExhausted,
            "CFG executor queue is full or stopped",
            {}};
  return future.get();
}
void CfgController::stop_admission() { impl_->executor->stop_admission(); }
} // namespace ctk::application
