#include "ctk/application/match_controller.hpp"
#include "cursor_registry.hpp"
#include "file_target_validation.hpp"
#include "query_executor.hpp"
#include "ctk/platform/process_memory.hpp"
#include <algorithm>
#include <future>
#include <limits>
#include <filesystem>

namespace ctk::application {
using ctk::clang_layer::MatchCode;
using namespace ctk::match::v1;
namespace {
MatchReply failure(MatchCode code, std::string message) {
  return {code, std::move(message), {}};
}
std::string invalid_request(const ParseRequest &request) {
  FileMatchTarget file;
  file.set_file_path(request.file_path());
  file.set_working_directory(request.working_directory());
  file.set_compilation_database(request.compilation_database());
  file.mutable_compile_arguments()->CopyFrom(request.compile_arguments());
  return detail::invalid_file_target(file);
}
std::string invalid_request(const MatchRequest &request) {
  if (request.query().empty())
    return "query must not be empty";
  if (!MatchTraversalMode_IsValid(request.traversal_mode()))
    return "invalid traversal mode";
  if (request.target_case() == MatchRequest::TARGET_NOT_SET)
    return "one target is required";
  if (request.has_file()) {
    return detail::invalid_file_target(request.file());
  } else {
    const auto &id = request.has_session() ? request.session().session_id()
                                           : request.binding().session_id();
    if (!detail::CursorRegistry::valid_id(id))
      return "session_id must be a canonical UUIDv4";
    if (request.has_session() &&
        request.session().has_expected_result_revision() &&
        request.session().expected_result_revision() == 0)
      return "revision must be positive";
    if (request.has_binding()) {
      const auto &binding = request.binding();
      if (binding.bind().empty())
        return "bind must not be empty";
      if (!BindingMatchScope_IsValid(binding.scope()))
        return "invalid binding scope";
      if (binding.has_expected_result_revision() &&
          binding.expected_result_revision() == 0)
        return "revision must be positive";
    }
  }
  return {};
}
} // namespace

struct MatchController::Impl {
  CursorSettings settings;
  std::shared_ptr<ctk::clang_layer::IMatchBackend> backend;
  detail::CursorRegistry registry;
  std::shared_ptr<OperationExecutor> executor;
  const std::chrono::steady_clock::time_point started = std::chrono::steady_clock::now();
  Impl(CursorSettings config,
       std::shared_ptr<ctk::clang_layer::IMatchBackend> native,
       std::shared_ptr<OperationExecutor> work)
      : settings(config), backend(std::move(native)), registry(config),
        executor(work ? std::move(work)
                      : make_operation_executor(config.workers,
                                                config.pending_requests)) {}
  MatchReply
  run_parse(const std::string &owner, const ParseRequest &request,
            const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint) {
    if (!backend)
      return failure(MatchCode::FailedPrecondition,
                     "Clang analysis is disabled");
    registry.find(owner, "");
    auto cursor = std::make_shared<detail::ResultCursor>();
    cursor->owner = owner;
    cursor->file_path = (std::filesystem::path(request.working_directory()) /
                         request.file_path()).lexically_normal().string();
    std::lock_guard operation(cursor->operation);
    auto result = backend->parse(request, checkpoint, settings.results);
    if (result.code != MatchCode::Ok)
      return failure(result.code, result.message);
    if (!result.rows.empty())
      return failure(MatchCode::Internal, "parse returned match rows");
    return registry.commit(cursor, std::move(result), checkpoint, true);
  }
  MatchReply run(const std::string &owner, const MatchRequest &request,
                 const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint,
                 const StreamSink *stream_sink = nullptr) {
    if (!backend)
      return failure(MatchCode::FailedPrecondition,
                     "Clang analysis is disabled");
    std::shared_ptr<detail::ResultCursor> cursor;
    if (request.has_file()) {
      // Prune expired cursors before a fresh publication.
      registry.find(owner, "");
      cursor = std::make_shared<detail::ResultCursor>();
      cursor->owner = owner;
      cursor->file_path = (std::filesystem::path(request.file().working_directory()) /
                           request.file().file_path()).lexically_normal().string();
    } else {
      cursor = registry.find(owner, request.has_session()
                                        ? request.session().session_id()
                                        : request.binding().session_id());
      if (!cursor)
        return failure(MatchCode::NotFound, "cursor unavailable");
    }
    std::lock_guard operation(cursor->operation);
    if (!request.has_file()) {
      if (cursor->closed ||
          cursor->deadline <= std::chrono::steady_clock::now())
        return failure(MatchCode::NotFound, "cursor expired or closed");
      const bool guard = request.has_session()
                             ? request.session().has_expected_result_revision()
                             : request.binding().has_expected_result_revision();
      const auto revision = request.has_session()
                                ? request.session().expected_result_revision()
                                : request.binding().expected_result_revision();
      if (guard && revision != cursor->response.result_revision())
        return failure(MatchCode::Aborted, "cursor result revision changed");
      if (request.has_binding()) {
        const auto &target = request.binding();
        bool selected = false;
        const auto scope = target.scope() == BINDING_MATCH_SCOPE_UNSPECIFIED
                               ? BINDING_MATCH_SCOPE_SUBTREE
                               : target.scope();
        for (int i = 0; i < cursor->response.results_size(); ++i) {
          if (target.has_match_index() &&
              target.match_index() != static_cast<std::uint64_t>(i))
            continue;
          const auto &bindings = cursor->response.results(i).bindings();
          const auto found = bindings.find(target.bind());
          if (found == bindings.end())
            continue;
          selected = true;
          const auto &scopes = found->second.supported_scopes();
          if (std::find(scopes.begin(), scopes.end(), scope) == scopes.end())
            return failure(MatchCode::FailedPrecondition,
                           "binding does not support requested scope");
        }
        if (!selected &&
            !(request.preserve_source() && cursor->response.results().empty() &&
              !target.has_match_index()))
          return failure(MatchCode::NotFound, "binding or row unavailable");
      }
    }
    ctk::clang_layer::MatchExecution result;
    if (stream_sink) {
      const ctk::clang_layer::IMatchBackend::RowSink row_sink =
          [this, stream_sink](const MatchResult &row, std::string &message) {
            MatchStreamEvent event;
            *event.mutable_row() = row;
            if (event.ByteSizeLong() > settings.results.max_bytes) {
              message = "match stream event exceeds byte limit (limit " +
                        std::to_string(settings.results.max_bytes) +
                        " bytes); no cursor state committed";
              return MatchCode::ResourceExhausted;
            }
            return (*stream_sink)(event, message);
          };
      result = backend->execute_stream(request, cursor->state, checkpoint,
                                       settings.results, row_sink);
    } else {
      result = backend->execute(request, cursor->state, checkpoint,
                                settings.results);
    }
    if (result.code != MatchCode::Ok)
      return failure(result.code, result.message);
    if (!request.has_file() && request.preserve_source()) {
      auto fork = std::make_shared<detail::ResultCursor>();
      fork->owner = owner;
      fork->file_path = cursor->file_path;
      std::lock_guard fork_operation(fork->operation);
      auto reply = registry.commit(fork, std::move(result), checkpoint, true,
                                   stream_sink != nullptr);
      if (reply.code == MatchCode::Ok && stream_sink) {
        MatchStreamEvent event;
        auto *completed = event.mutable_completed();
        completed->set_session_id(reply.response.session_id());
        completed->set_result_revision(reply.response.result_revision());
        completed->mutable_expires_at()->CopyFrom(reply.response.expires_at());
        completed->set_row_count(reply.response.results_size());
        std::string message;
        const auto code = (*stream_sink)(event, message);
        if (code != MatchCode::Ok)
          return failure(code, std::move(message));
      }
      return reply;
    }
    auto reply = registry.commit(cursor, std::move(result), checkpoint,
                                 request.has_file(), stream_sink != nullptr);
    if (reply.code == MatchCode::Ok && stream_sink) {
      MatchStreamEvent event;
      auto *completed = event.mutable_completed();
      completed->set_session_id(reply.response.session_id());
      completed->set_result_revision(reply.response.result_revision());
      completed->mutable_expires_at()->CopyFrom(reply.response.expires_at());
      completed->set_row_count(reply.response.results_size());
      std::string message;
      const auto code = (*stream_sink)(event, message);
      if (code != MatchCode::Ok)
        return failure(code, std::move(message));
    }
    return reply;
  }
};

MatchController::MatchController(
    CursorSettings settings,
    std::shared_ptr<ctk::clang_layer::IMatchBackend> backend,
    std::shared_ptr<OperationExecutor> executor) {
  if (settings.max_cursors == 0 || settings.max_memory_bytes == 0 ||
      settings.idle_ttl.count() <= 0 || settings.results.max_rows == 0 ||
      settings.results.max_bytes == 0)
    throw std::invalid_argument("cursor limits and TTL must be positive");
#ifdef CTK_WITH_CLANG
  if (!backend)
    backend = ctk::clang_layer::make_match_backend();
#endif
  impl_ =
      std::make_unique<Impl>(settings, std::move(backend), std::move(executor));
}
MatchController::~MatchController() = default;
ParseReply MatchController::parse(
    const std::string &owner, const ParseRequest &request,
    const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint) {
  const auto invalid = invalid_request(request);
  if (owner.empty() || !invalid.empty())
    return {MatchCode::InvalidArgument,
            owner.empty() ? "caller owner is required" : invalid,
            {}};
  auto promise = std::make_shared<std::promise<MatchReply>>();
  auto future = promise->get_future();
  if (!impl_->executor->enqueue([this, promise, owner, request, checkpoint] {
        try {
          promise->set_value(impl_->run_parse(owner, request, checkpoint));
        } catch (const std::exception &error) {
          promise->set_value(failure(MatchCode::Internal, error.what()));
        } catch (...) {
          promise->set_value(
              failure(MatchCode::Internal, "native parsing failed"));
        }
      }))
    return {MatchCode::ResourceExhausted,
            "match executor queue is full or stopped",
            {}};
  auto result = future.get();
  ParseReply reply{result.code, std::move(result.message), {}};
  if (result.code == MatchCode::Ok) {
    reply.response.set_session_id(result.response.session_id());
    reply.response.set_result_revision(result.response.result_revision());
    reply.response.mutable_expires_at()->Swap(
        result.response.mutable_expires_at());
  }
  return reply;
}
MatchReply MatchController::match(
    const std::string &owner, const MatchRequest &request,
    const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint) {
  const auto invalid = invalid_request(request);
  if (owner.empty() || !invalid.empty())
    return failure(MatchCode::InvalidArgument,
                   owner.empty() ? "caller owner is required" : invalid);
  auto promise = std::make_shared<std::promise<MatchReply>>();
  auto future = promise->get_future();
  if (!impl_->executor->enqueue([this, promise, owner, request, checkpoint] {
        try {
          promise->set_value(impl_->run(owner, request, checkpoint));
        } catch (const std::exception &error) {
          promise->set_value(failure(MatchCode::Internal, error.what()));
        } catch (...) {
          promise->set_value(
              failure(MatchCode::Internal, "native matching failed"));
        }
      }))
    return failure(MatchCode::ResourceExhausted,
                   "match executor queue is full or stopped");
  return future.get();
}
MatchReply MatchController::stream_match(
    const std::string &owner, const MatchRequest &request,
    const ctk::clang_layer::IMatchBackend::Checkpoint &checkpoint,
    const StreamSink &sink) {
  const auto invalid = invalid_request(request);
  if (owner.empty() || !invalid.empty())
    return failure(MatchCode::InvalidArgument,
                   owner.empty() ? "caller owner is required" : invalid);
  // Reject an event cap too small for any valid completion before work can
  // commit. Maximal field widths make this a conservative wire-size bound.
  MatchStreamEvent maximum_completion;
  auto *completed = maximum_completion.mutable_completed();
  completed->set_session_id("00000000-0000-4000-8000-000000000000");
  completed->set_result_revision(std::numeric_limits<std::uint64_t>::max());
  completed->mutable_expires_at()->set_seconds(253402300799LL);
  completed->mutable_expires_at()->set_nanos(999999999);
  completed->set_row_count(std::numeric_limits<std::uint64_t>::max());
  if (maximum_completion.ByteSizeLong() > impl_->settings.results.max_bytes)
    return failure(MatchCode::ResourceExhausted,
                   "match completion event exceeds byte limit; no cursor "
                   "state committed");
  auto promise = std::make_shared<std::promise<MatchReply>>();
  auto future = promise->get_future();
  if (!impl_->executor->enqueue(
          [this, promise, owner, request, checkpoint, sink] {
            try {
              promise->set_value(impl_->run(owner, request, checkpoint, &sink));
            } catch (const std::exception &error) {
              promise->set_value(failure(MatchCode::Internal, error.what()));
            } catch (...) {
              promise->set_value(
                  failure(MatchCode::Internal, "native matching failed"));
            }
          }))
    return failure(MatchCode::ResourceExhausted,
                   "match executor queue is full or stopped");
  return future.get();
}
MatchReply MatchController::close(const std::string &owner,
                                  const std::string &id) {
  return impl_->registry.close(owner, id);
}
void MatchController::stop_admission() { impl_->executor->stop_admission(); }

ListSessionsResponse MatchController::list_sessions(const std::string &owner) {
  return impl_->registry.list(owner);
}
MatchReply MatchController::attach_session(const std::string &owner,
                                           const std::string &id,
                                           SessionInfo &response) {
  if (owner.empty())
    return failure(MatchCode::InvalidArgument, "caller owner is required");
  return impl_->registry.attach(owner, id, response);
}
ServerStatusResponse MatchController::server_status() {
  ServerStatusResponse response;
  response.set_uptime_ms(std::chrono::duration_cast<std::chrono::milliseconds>(
      std::chrono::steady_clock::now() - impl_->started).count());
  if (const auto rss = ctk::platform::resident_memory_bytes())
    response.set_resident_memory_bytes(*rss);
  const auto [count, bytes] = impl_->registry.usage();
  response.set_active_sessions(count);
  response.set_retained_memory_bytes(bytes);
  response.set_max_sessions(impl_->settings.max_cursors);
  response.set_max_retained_memory_bytes(impl_->settings.max_memory_bytes);
  if (impl_->backend)
    response.mutable_cache()->CopyFrom(impl_->backend->resources());
  return response;
}
MatchReply MatchController::prune_caches(const PruneCachesRequest &request,
                                        PruneCachesResponse &response) {
  if (!request.memory() && !request.disk())
    return failure(MatchCode::InvalidArgument, "select memory and/or disk caches");
  if (!impl_->backend)
    return failure(MatchCode::FailedPrecondition, "Clang analysis is disabled");
  try {
    response.mutable_before()->CopyFrom(impl_->backend->resources());
    if ((request.memory() && !response.before().memory_available()) ||
        (request.disk() && !response.before().storage_available()))
      return failure(MatchCode::FailedPrecondition, "selected cache is unavailable");
    impl_->backend->prune_caches(request.memory(), request.disk());
    response.mutable_after()->CopyFrom(impl_->backend->resources());
    return {};
  } catch (const std::exception &error) {
    return failure(MatchCode::Internal, error.what());
  }
}
} // namespace ctk::application
