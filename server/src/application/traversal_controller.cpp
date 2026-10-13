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
  MatchController *matches;
  Impl(CursorSettings settings,
       std::shared_ptr<ctk::clang_layer::ITraversalBackend> native,
       std::shared_ptr<OperationExecutor> work, MatchController *source)
      : backend(std::move(native)),
        resources(settings.resources ? settings.resources
                  : source           ? source->resource_manager()
                                     : nullptr),
        matches(source), limits{100000, settings.results.max_bytes},
        executor(work ? std::move(work)
                      : make_operation_executor(settings.workers,
                                                settings.pending_requests)) {}
};
TraversalController::TraversalController(
    CursorSettings settings,
    std::shared_ptr<ctk::clang_layer::ITraversalBackend> backend,
    std::shared_ptr<OperationExecutor> executor, MatchController *matches) {
  if (settings.results.max_bytes == 0)
    throw std::invalid_argument("traversal byte limit must be positive");
#ifdef CTK_WITH_CLANG
  if (!backend)
    backend = ctk::clang_layer::make_traversal_backend();
#endif
  impl_ = std::make_unique<Impl>(settings, std::move(backend),
                                 std::move(executor), matches);
}
TraversalController::~TraversalController() = default;
TraversalResult TraversalController::traverse(
    const ctk::analysis::v1::TraverseRequest &request,
    const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint,
    const std::string &owner) {
  ctk::analysis::v1::TraverseResponse collected;
  std::size_t collected_bytes = 0;
  auto result = traverse_stream(
      request, checkpoint,
      [&](const ctk::analysis::v1::TraversalNode &node, std::string &message) {
        if (node.ByteSizeLong() + 16 >
            impl_->limits.max_bytes - collected_bytes) {
          message = "AST traversal response limit exceeded";
          return MatchCode::ResourceExhausted;
        }
        collected_bytes += node.ByteSizeLong() + 16;
        collected.add_nodes()->CopyFrom(node);
        return MatchCode::Ok;
      },
      owner);
  if (result.code == MatchCode::Ok) {
    collected.set_depth_limited(result.response.depth_limited());
    result.response.Swap(&collected);
  }
  return result;
}
TraversalResult TraversalController::traverse_stream(
    const ctk::analysis::v1::TraverseRequest &request,
    const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint,
    const ctk::clang_layer::ITraversalBackend::NodeSink &sink,
    const std::string &owner) {
  if (!sink)
    return {MatchCode::InvalidArgument, "traversal node sink is required", {}};
  const auto invalid = request.has_file()
                           ? detail::invalid_file_target(request.file())
                           : std::string{};
  if (request.target_case() ==
          ctk::analysis::v1::TraverseRequest::TARGET_NOT_SET ||
      !invalid.empty())
    return {MatchCode::InvalidArgument,
            invalid.empty() ? "traversal target is required" : invalid,
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
                                 owner, work, sink] {
        try {
          auto resource_scope = detail::make_snapshot_scope(
              impl_->resources, owner, request.resource_scope_id(),
              work->token());
          std::shared_ptr<const ctk::clang_layer::NativeBindingState> state;
          if (!request.has_file()) {
            if (!impl_->matches) {
              promise->set_value({MatchCode::FailedPrecondition,
                                  "retained traversal is unavailable",
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
          auto result = impl_->backend->traverse_stream(
              request, state, scoped_checkpoint, impl_->limits, sink);
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
