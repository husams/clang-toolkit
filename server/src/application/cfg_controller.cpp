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
  MatchController *matches;
  Impl(CursorSettings settings,
       std::shared_ptr<ctk::clang_layer::ICfgBackend> native,
       std::shared_ptr<OperationExecutor> work, MatchController *source)
      : backend(std::move(native)),
        resources(settings.resources ? settings.resources
                  : source           ? source->resource_manager()
                                     : nullptr),
        matches(source),
        limits{1000, 100000, 1000000, settings.results.max_bytes},
        executor(work ? std::move(work)
                      : make_operation_executor(settings.workers,
                                                settings.pending_requests)) {}
};
CfgController::CfgController(
    CursorSettings settings,
    std::shared_ptr<ctk::clang_layer::ICfgBackend> backend,
    std::shared_ptr<OperationExecutor> executor, MatchController *matches) {
  if (settings.results.max_bytes == 0)
    throw std::invalid_argument("CFG byte limit must be positive");
#ifdef CTK_WITH_CLANG
  if (!backend)
    backend = ctk::clang_layer::make_cfg_backend();
#endif
  impl_ = std::make_unique<Impl>(settings, std::move(backend),
                                 std::move(executor), matches);
}
CfgController::~CfgController() = default;
CfgResult CfgController::build(
    const ctk::analysis::v1::CfgRequest &request,
    const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint,
    const std::string &owner) {
  ctk::analysis::v1::CfgResponse collected;
  std::size_t bytes = 0;
  auto result = build_stream(
      request, checkpoint,
      [&](const ctk::analysis::v1::CfgStreamEvent &event,
          std::string &message) {
        if (event.ByteSizeLong() + 16 > impl_->limits.max_bytes - bytes) {
          message = "CFG response byte limit exceeded";
          return MatchCode::ResourceExhausted;
        }
        bytes += event.ByteSizeLong() + 16;
        if (event.has_graph_started())
          collected.add_graphs()->CopyFrom(event.graph_started().graph());
        else if (event.has_block()) {
          auto *graph = collected.mutable_graphs(event.block().graph_index());
          graph->add_blocks()->CopyFrom(event.block().block());
          for (const auto &field : event.block().block().availability())
            graph->add_availability()->CopyFrom(field);
        } else if (event.has_graph_completed())
          collected.mutable_graphs(event.graph_completed().graph_index())
              ->set_is_complete(event.graph_completed().is_complete());
        return MatchCode::Ok;
      },
      owner);
  if (result.code == MatchCode::Ok)
    result.response.Swap(&collected);
  return result;
}
CfgResult CfgController::build_stream(
    const ctk::analysis::v1::CfgRequest &request,
    const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint,
    const ctk::clang_layer::ICfgBackend::EventSink &sink,
    const std::string &owner) {
  const auto invalid = request.has_file()
                           ? detail::invalid_file_target(request.file())
                           : std::string{};
  if (!sink ||
      request.target_case() == ctk::analysis::v1::CfgRequest::TARGET_NOT_SET ||
      !invalid.empty())
    return {MatchCode::InvalidArgument,
            invalid.empty() ? "CFG target and event sink are required"
                            : invalid,
            {}};
  if (request.has_binding() ? !request.function().empty()
                            : request.function().empty())
    return {MatchCode::InvalidArgument,
            "function name is required except for an exact binding",
            {}};
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
                                 owner, work, sink] {
        try {
          auto resource_scope = detail::make_snapshot_scope(
              impl_->resources, owner, request.resource_scope_id(),
              work->token());
          std::shared_ptr<const ctk::clang_layer::NativeBindingState> state;
          if (!request.has_file()) {
            if (!impl_->matches) {
              promise->set_value({MatchCode::FailedPrecondition,
                                  "retained CFG is unavailable",
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
          auto result = impl_->backend->build_stream(
              request, state, scoped_checkpoint, impl_->limits,
              [&](const ctk::analysis::v1::CfgStreamEvent &event,
                  std::string &message) {
                if (!scoped_checkpoint()) {
                  message = "CFG analysis cancelled";
                  return MatchCode::Cancelled;
                }
                if (event.ByteSizeLong() > impl_->limits.max_bytes) {
                  message = "CFG stream event byte limit exceeded";
                  return MatchCode::ResourceExhausted;
                }
                return sink(event, message);
              });
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
CfgResult CfgController::variable_flow(
    const ctk::analysis::v1::VariableFlowRequest &request,
    const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint,
    const ctk::clang_layer::ICfgBackend::VariableSink &sink,
    const std::string &owner) {
  if (!sink || !request.has_variable() || !request.has_function())
    return {MatchCode::InvalidArgument,
            "variable and function bindings are required",
            {}};
  if ((request.has_max_blocks() &&
       (!request.max_blocks() || request.max_blocks() > 100000)) ||
      (request.has_max_events() &&
       (!request.max_events() || request.max_events() > 100000)) ||
      (request.has_max_iterations() &&
       (!request.max_iterations() || request.max_iterations() > 1000000)))
    return {MatchCode::InvalidArgument,
            "variable flow limits exceed server bounds",
            {}};
  if (!impl_->backend || !impl_->matches)
    return {MatchCode::FailedPrecondition,
            "retained variable flow is unavailable",
            {}};
  auto work = std::make_shared<ResourceManager::WorkLease>();
  if (impl_->resources) {
    std::string message;
    auto code = impl_->resources->begin_work(owner, request.resource_scope_id(),
                                             *work, message);
    if (code != MatchCode::Ok)
      return {code, std::move(message), {}};
  }
  const auto check = [checkpoint, work] {
    return (!checkpoint || checkpoint()) && work->checkpoint();
  };
  auto promise = std::make_shared<std::promise<CfgResult>>();
  auto future = promise->get_future();
  if (!impl_->executor->enqueue([this, promise, request, check, owner, work,
                                 sink] {
        try {
          auto scope = detail::make_snapshot_scope(impl_->resources, owner,
                                                   request.resource_scope_id(),
                                                   work->token());
          std::shared_ptr<const ctk::clang_layer::NativeBindingState> variable,
              function;
          auto resolve = [&](const auto &binding, auto &state) {
            ctk::match::v1::MatchRequest target;
            target.mutable_binding()->CopyFrom(binding);
            target.set_query("unused");
            target.set_resource_scope_id(request.resource_scope_id());
            return impl_->matches->native_state(owner, target, state,
                                                work->token());
          };
          auto resolved = resolve(request.variable(), variable);
          if (resolved.code != MatchCode::Ok) {
            promise->set_value({resolved.code, resolved.message, {}});
            return;
          }
          resolved = resolve(request.function(), function);
          if (resolved.code != MatchCode::Ok) {
            promise->set_value({resolved.code, resolved.message, {}});
            return;
          }
          promise->set_value(impl_->backend->variable_flow(
              request, variable, function, check, impl_->limits,
              [&](const auto &event, std::string &message) {
                if (!check()) {
                  message = "variable flow cancelled";
                  return MatchCode::Cancelled;
                }
                if (event.ByteSizeLong() > impl_->limits.max_bytes) {
                  message = "variable flow event byte limit exceeded";
                  return MatchCode::ResourceExhausted;
                }
                return sink(event, message);
              }));
        } catch (const std::exception &error) {
          promise->set_value({MatchCode::Internal, error.what(), {}});
        } catch (...) {
          promise->set_value({MatchCode::Internal, "variable flow failed", {}});
        }
      }))
    return {MatchCode::ResourceExhausted,
            "CFG executor queue is full or stopped",
            {}};
  return future.get();
}
} // namespace ctk::application
