#include "ctk/application/script_controller.hpp"
#include "ctk/clang/tooling.hpp"
#include "file_target_validation.hpp"
#include "native_script_environment.hpp"
#include "resource_scope_guard.hpp"
#include <future>
namespace ctk::application {
using Code = ctk::clang_layer::MatchCode;
ScriptController::ScriptController(
    CursorSettings settings,
    std::shared_ptr<ctk::clang_layer::IQueryEngine> engine,
    std::shared_ptr<OperationExecutor> executor)
    : settings_(settings), engine_(std::move(engine)),
      executor_(executor ? std::move(executor)
                         : make_operation_executor(settings.workers,
                                                   settings.pending_requests)) {
  if (!settings.results.max_bytes || !settings.max_memory_bytes)
    throw std::invalid_argument("script resource limits must be positive");
#ifdef CTK_WITH_CLANG
  if (!engine_)
    engine_ = ctk::clang_layer::make_query_engine();
#endif
}
ctk::script::Result ScriptController::run(
    const ctk::analysis::v1::ScriptRequest &request,
    const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint,
    const std::string &owner) {
  if (request.has_file()) {
    auto file = request.file();
    if (request.has_profile()) {
      file.set_working_directory(request.profile().working_directory());
      file.set_compilation_database(request.profile().compilation_database());
      file.clear_compile_arguments();
      *file.mutable_compile_arguments() =
          request.profile().compile_arguments();
    }
    auto invalid = detail::invalid_file_target(file);
    if (!invalid.empty())
      return {Code::InvalidArgument, invalid, {}};
  }
  if (request.has_profile()) {
    auto invalid = detail::invalid_script_profile(request.profile());
    if (!invalid.empty())
      return {Code::InvalidArgument, invalid, {}};
  }
  if (request.has_max_steps() &&
      (request.max_steps() == 0 || request.max_steps() > 10000))
    return {Code::InvalidArgument, "script max_steps must be 1..10000", {}};
  if (request.source().size() > 1024 * 1024)
    return {Code::ResourceExhausted, "script source byte limit exceeded", {}};
  auto work = std::make_shared<ResourceManager::WorkLease>();
  if (settings_.resources) {
    std::string message;
    const auto code = settings_.resources->begin_work(
        owner, request.resource_scope_id(), *work, message);
    if (code != Code::Ok)
      return {code, std::move(message), {}};
  }
  const auto scoped_checkpoint = [checkpoint, work] {
    return (!checkpoint || checkpoint()) && work->checkpoint();
  };
  auto promise = std::make_shared<std::promise<ctk::script::Result>>();
  auto future = promise->get_future();
  if (!executor_->enqueue([this, promise, request, scoped_checkpoint, owner,
                           work] {
        try {
          auto resource_scope = detail::make_snapshot_scope(
              settings_.resources, owner, request.resource_scope_id(),
              work->token());
          detail::NativeScriptEnvironment environment(request, settings_,
                                                      engine_, scoped_checkpoint);
          ctk::script::Limits limits;
          limits.max_steps =
              request.has_max_steps() ? request.max_steps() : 100;
          limits.max_response_bytes = settings_.results.max_bytes;
          promise->set_value(ctk::script::Engine{}.run(
              request.source(), &environment, limits, scoped_checkpoint));
        } catch (const std::exception &error) {
          promise->set_value({Code::Internal, error.what(), {}});
        } catch (...) {
          promise->set_value({Code::Internal, "script execution failed", {}});
        }
      }))
    return {Code::ResourceExhausted,
            "script executor queue is full or stopped",
            {}};
  return future.get();
}
} // namespace ctk::application
