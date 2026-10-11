#include "ctk/application/script_controller.hpp"
#include "ctk/clang/file_discovery.hpp"
#include "ctk/clang/tooling.hpp"
#include "ctk/script/error.hpp"
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
    const std::string &owner, ctk::script::ExportSink export_sink) {
  if (request.has_file()) {
    auto file = request.file();
    if (request.has_profile()) {
      file.set_working_directory(request.profile().working_directory());
      file.set_compilation_database(request.profile().compilation_database());
      file.clear_compile_arguments();
      *file.mutable_compile_arguments() = request.profile().compile_arguments();
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
  bool has_native_batch = false;
  try {
    has_native_batch = ctk::script::Engine{}.contains_batch(request.source());
  } catch (const ctk::script::Error &error) {
    return {error.code, error.what(), {}};
  }
  auto work = std::make_shared<ResourceManager::WorkLease>();
  if (settings_.resources &&
      (!request.resource_scope_id().empty() || !has_native_batch)) {
    std::string message;
    const auto code = settings_.resources->begin_work(
        owner, request.resource_scope_id(), *work, message);
    if (code != Code::Ok)
      return {code, std::move(message), {}};
  }
  const auto scoped_checkpoint = [checkpoint, work] {
    return (!checkpoint || checkpoint()) && (!*work || work->checkpoint());
  };
  auto promise = std::make_shared<std::promise<ctk::script::Result>>();
  auto future = promise->get_future();
  if (!executor_->enqueue([this, promise, request, scoped_checkpoint, owner,
                           work, export_sink = std::move(export_sink)] {
        try {
          auto resource_scope = detail::make_snapshot_scope(
              settings_.resources, owner, request.resource_scope_id(),
              work->token());
          detail::NativeScriptEnvironment environment(
              request, settings_, engine_, scoped_checkpoint, owner);
          ctk::script::Limits limits;
          limits.max_steps =
              request.has_max_steps() ? request.max_steps() : 100;
          limits.max_response_bytes = settings_.results.max_bytes;
          promise->set_value(ctk::script::Engine{}.run(
              request.source(), &environment, limits, scoped_checkpoint,
              {request.initial_values().begin(),
               request.initial_values().end()},
              std::move(export_sink), request.collect_final()));
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
std::vector<std::vector<ScriptSourceRevision>>
ScriptController::capture_source_revisions(
    const std::vector<ctk::match::v1::InputDescriptor> &inputs,
    const std::string &owner, const std::string &resource_scope_id) {
  if (!engine_)
    throw std::runtime_error("native source revision capture is unavailable");
  std::vector<std::vector<ScriptSourceRevision>> result;
  result.reserve(inputs.size());
  auto work = std::make_shared<ResourceManager::WorkLease>();
  if (settings_.resources) {
    std::string message;
    const auto code = settings_.resources->begin_work(owner, resource_scope_id,
                                                      *work, message);
    if (code != Code::Ok)
      throw std::runtime_error(message);
  }
  auto snapshot_scope = detail::make_snapshot_scope(
      settings_.resources, owner, resource_scope_id, work->token(), inputs);
  for (const auto &input : inputs) {
    auto resolved = ctk::clang_layer::resolve_file_descriptor(input);
    auto snapshot = engine_->acquire_snapshot(resolved.file);
    if (!snapshot)
      throw std::runtime_error("source revision snapshot was not acquired");
    std::vector<ScriptSourceRevision> closure;
    closure.reserve(snapshot->inputs.size());
    for (const auto &observation : snapshot->inputs) {
      const char *kind = "file";
      if (observation.kind == ctk::cache::InputKind::Absent)
        kind = "absent";
      else if (observation.kind == ctk::cache::InputKind::Directory)
        kind = "directory";
      closure.push_back({observation.path, kind, observation.content_digest,
                         observation.validation_context});
    }
    result.push_back(std::move(closure));
  }
  return result;
}
} // namespace ctk::application
