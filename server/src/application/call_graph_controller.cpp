#include "ctk/application/call_graph_controller.hpp"
#include "file_target_validation.hpp"
#include "query_executor.hpp"
#include "resource_scope_guard.hpp"
#include <future>

namespace ctk::application {
using ctk::clang_layer::CallGraphResult;
using ctk::clang_layer::CallGraphStreamResult;
using ctk::clang_layer::MatchCode;
struct CallGraphController::Impl {
  std::shared_ptr<ctk::clang_layer::ICallGraphBackend> backend;
  ctk::clang_layer::CallGraphLimits limits;
  std::shared_ptr<OperationExecutor> executor;
  std::shared_ptr<ResourceManager> resources;
  MatchController *matches;
  Impl(CursorSettings settings,
       std::shared_ptr<ctk::clang_layer::ICallGraphBackend> native,
       std::shared_ptr<OperationExecutor> work)
      : backend(std::move(native)), resources(settings.resources),
        matches(nullptr),
        limits{100000, 1000000, settings.results.max_bytes},
        executor(work ? std::move(work)
                      : make_operation_executor(settings.workers,
                                                settings.pending_requests)) {}
};
CallGraphController::CallGraphController(
    CursorSettings settings,
    std::shared_ptr<ctk::clang_layer::ICallGraphBackend> backend,
    std::shared_ptr<OperationExecutor> executor, MatchController *matches) {
  if (settings.results.max_bytes == 0)
    throw std::invalid_argument("call graph byte limit must be positive");
#ifdef CTK_WITH_CLANG
  if (!backend)
    backend = ctk::clang_layer::make_call_graph_backend();
#endif
  impl_ =
      std::make_unique<Impl>(settings, std::move(backend), std::move(executor));
  impl_->matches = matches;
  if (!impl_->resources && matches)
    impl_->resources = matches->resource_manager();
}
CallGraphController::~CallGraphController() = default;
CallGraphResult CallGraphController::build(
    const ctk::analysis::v1::CallGraphRequest &request,
    const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint,
    const std::string &owner) {
  const auto invalid = request.has_file()
                           ? detail::invalid_file_target(request.file())
                           : std::string{};
  if (request.target_case() ==
          ctk::analysis::v1::CallGraphRequest::TARGET_NOT_SET ||
      !invalid.empty())
    return {MatchCode::InvalidArgument,
            invalid.empty() ? "call graph target is required" : invalid,
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
  if (request.has_binding() && !request.function().empty())
    return {MatchCode::InvalidArgument,
            "function cannot be combined with a binding target", {}};
  if (!ctk::analysis::v1::CallGraphDirection_IsValid(request.direction()))
    return {MatchCode::InvalidArgument, "unknown call graph direction", {}};
  if ((request.has_unlimited_depth() && request.unlimited_depth() &&
       request.has_max_depth()) ||
      (request.has_max_depth() && request.max_depth() > 32) ||
      (request.has_max_call_sites() &&
       (request.max_call_sites() == 0 || request.max_call_sites() > 1000000)))
    return {MatchCode::InvalidArgument,
            "call graph depth or call-site limit exceeds server bounds", {}};
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
          std::shared_ptr<const ctk::clang_layer::NativeBindingState> state;
          if (!request.has_file()) {
            if (!impl_->matches) {
              promise->set_value({MatchCode::FailedPrecondition,
                                  "retained call graph targets are unavailable",
                                  {}});
              return;
            }
            ctk::match::v1::MatchRequest target;
            target.set_query("unused");
            target.set_resource_scope_id(request.resource_scope_id());
            if (request.has_session())
              target.mutable_session()->CopyFrom(request.session());
            else if (request.has_binding())
              target.mutable_binding()->CopyFrom(request.binding());
            else
              target.mutable_file_handle()->CopyFrom(request.file_handle());
            const auto resolved = impl_->matches->native_state(
                owner, target, state, work->token());
            if (resolved.code != MatchCode::Ok) {
              promise->set_value({resolved.code, resolved.message, {}});
              return;
            }
          }
          auto result = impl_->backend->build_selected(
              request, std::move(state), scoped_checkpoint, impl_->limits);
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
CallGraphStreamResult CallGraphController::build_stream(
    const ctk::analysis::v1::CallGraphRequest &request,
    const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint,
    const ctk::clang_layer::ICallGraphBackend::EventSink &sink,
    const std::string &owner) {
  const auto invalid = request.has_file()
                           ? detail::invalid_file_target(request.file())
                           : std::string{};
  if (!sink || request.target_case() ==
                   ctk::analysis::v1::CallGraphRequest::TARGET_NOT_SET ||
      !invalid.empty())
    return {MatchCode::InvalidArgument,
            invalid.empty() ? "call graph target and event sink are required"
                            : invalid,
            {}};
  if ((request.has_max_nodes() &&
       (!request.max_nodes() || request.max_nodes() > impl_->limits.max_nodes)) ||
      (request.has_max_edges() &&
       (!request.max_edges() || request.max_edges() > impl_->limits.max_edges)))
    return {MatchCode::InvalidArgument,
            "call graph limits must be positive and within server bounds", {}};
  if (request.has_binding() && !request.function().empty())
    return {MatchCode::InvalidArgument,
            "function cannot be combined with a binding target", {}};
  if (!ctk::analysis::v1::CallGraphDirection_IsValid(request.direction()))
    return {MatchCode::InvalidArgument, "unknown call graph direction", {}};
  if ((request.has_unlimited_depth() && request.unlimited_depth() &&
       request.has_max_depth()) ||
      (request.has_max_depth() && request.max_depth() > 32) ||
      (request.has_max_call_sites() &&
       (!request.max_call_sites() || request.max_call_sites() > 1000000)))
    return {MatchCode::InvalidArgument,
            "call graph depth or call-site limit exceeds server bounds", {}};
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
  const auto check = [checkpoint, work] {
    return (!checkpoint || checkpoint()) && work->checkpoint();
  };
  auto promise = std::make_shared<std::promise<CallGraphStreamResult>>();
  auto future = promise->get_future();
  if (!impl_->executor->enqueue([this, promise, request, check, owner, work,
                                 sink] {
        try {
          auto scope = detail::make_snapshot_scope(impl_->resources, owner,
                                                   request.resource_scope_id(),
                                                   work->token());
          std::shared_ptr<const ctk::clang_layer::NativeBindingState> state;
          if (!request.has_file()) {
            if (!impl_->matches) {
              promise->set_value({MatchCode::FailedPrecondition,
                                  "retained call graph targets are unavailable", {}});
              return;
            }
            ctk::match::v1::MatchRequest target;
            target.set_query("unused");
            target.set_resource_scope_id(request.resource_scope_id());
            if (request.has_session())
              target.mutable_session()->CopyFrom(request.session());
            else if (request.has_binding())
              target.mutable_binding()->CopyFrom(request.binding());
            else
              target.mutable_file_handle()->CopyFrom(request.file_handle());
            const auto resolved = impl_->matches->native_state(
                owner, target, state, work->token());
            if (resolved.code != MatchCode::Ok) {
              promise->set_value({resolved.code, resolved.message, {}});
              return;
            }
          }
          auto result = impl_->backend->build_stream(
              request, std::move(state), check, impl_->limits,
              [&](const ctk::analysis::v1::CallGraphStreamEvent &event,
                  std::string &message) {
                if (!check()) {
                  message = "call graph analysis cancelled";
                  return MatchCode::Cancelled;
                }
                if (event.ByteSizeLong() > impl_->limits.max_bytes) {
                  message = "call graph stream event byte limit exceeded";
                  return MatchCode::ResourceExhausted;
                }
                return sink(event, message);
              });
          ctk::analysis::v1::CallGraphStreamEvent completion_event;
          completion_event.mutable_completed()->CopyFrom(result.completed);
          if (result.code == MatchCode::Ok &&
              completion_event.ByteSizeLong() > impl_->limits.max_bytes) {
            result.code = MatchCode::ResourceExhausted;
            result.message = "call graph completion exceeds response byte limit";
          }
          if (result.code == MatchCode::Ok && !check())
            result = {MatchCode::Cancelled,
                      "call graph analysis cancelled before completion", {}};
          promise->set_value(std::move(result));
        } catch (const std::exception &error) {
          promise->set_value({MatchCode::Internal, error.what(), {}});
        } catch (...) {
          promise->set_value(
              {MatchCode::Internal, "call graph analysis failed", {}});
        }
      }))
    return {MatchCode::ResourceExhausted,
            "call graph executor queue is full or stopped", {}};
  return future.get();
}
void CallGraphController::stop_admission() {
  impl_->executor->stop_admission();
}
} // namespace ctk::application
